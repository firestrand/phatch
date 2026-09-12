from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from operator import attrgetter
from pathlib import Path
from typing import Protocol

from phatch.resources.provider import ResourceProvider


class GuiModule(Protocol):
    Frame: type


@contextmanager
def plugin_help_path(provider: ResourceProvider) -> Iterator[Path]:
    provider.read_bytes("docs/html/index.html")
    with provider.tree_as_path("docs/html") as documentation_root:
        yield documentation_root / "index.html"


@contextmanager
def packaged_gui_help(
    gui_module: GuiModule,
    provider: ResourceProvider,
) -> Iterator[None]:
    legacy_frame = gui_module.Frame
    legacy_get_setting = attrgetter("get_setting")(legacy_frame)
    with plugin_help_path(provider) as help_path:

        def get_setting(frame, name: str) -> str:
            if name == "PHATCH_DOCS_PATH":
                return str(help_path.parent)
            return legacy_get_setting(frame, name)

        gui_module.Frame = type(
            "PackagedHelpFrame",
            (legacy_frame,),
            {"get_setting": get_setting},
        )
        try:
            yield
        finally:
            gui_module.Frame = legacy_frame
