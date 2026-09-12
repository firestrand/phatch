from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from phatch.resources.provider import ResourceNotFoundError, ResourceProvider


def test_plugin_help_uses_only_injected_documentation_root(tmp_path: Path) -> None:
    # Given: an injected packaged documentation directory
    docs = tmp_path / "docs/html"
    docs.mkdir(parents=True)
    expected = docs / "index.html"
    expected.write_text("documentation", encoding="utf-8")
    module = importlib.import_module("phatch.pyWx.documentation")

    # When: the help adapter selects the plugin documentation
    provider = ResourceProvider.from_root(tmp_path)
    with module.plugin_help_path(provider) as result:
        value = result.read_text(encoding="utf-8")

    # Then: it uses the injected root directly
    assert value == "documentation"
    assert not result.exists()


def test_missing_plugin_documentation_raises_typed_error(tmp_path: Path) -> None:
    # Given: an injected package root without documentation
    module = importlib.import_module("phatch.pyWx.documentation")
    provider = ResourceProvider.from_root(tmp_path)

    # When: plugin help is materialized
    # Then: the provider reports the missing logical resource
    with (
        pytest.raises(ResourceNotFoundError, match=r"docs/html/index\.html"),
        module.plugin_help_path(provider),
    ):
        pass


def test_packaged_gui_help_substitutes_and_restores_frame(tmp_path: Path) -> None:
    # Given: a legacy GUI frame and packaged documentation
    module = importlib.import_module("phatch.pyWx.documentation")

    class LegacyFrame:
        def get_setting(self, name: str) -> str:
            return f"legacy/{name}"

    class TestGuiModule:
        Frame = LegacyFrame

    gui_module = TestGuiModule()
    docs = tmp_path / "docs/html"
    docs.mkdir(parents=True)
    (docs / "index.html").write_text("documentation", encoding="utf-8")
    provider = ResourceProvider.from_root(tmp_path)

    # When: the canonical composition context substitutes the GUI frame
    with module.packaged_gui_help(gui_module, provider):
        selected_frame = gui_module.Frame
        selected_docs = selected_frame().get_setting("PHATCH_DOCS_PATH")
        selected_content = Path(selected_docs, "index.html").read_text(encoding="utf-8")
        selected_other = selected_frame().get_setting("other")

    # Then: packaged docs are injected only for the context
    assert selected_content == "documentation"
    assert selected_other == "legacy/other"
    assert gui_module.Frame is LegacyFrame
