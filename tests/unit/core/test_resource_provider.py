from __future__ import annotations

import importlib
import zipfile
from pathlib import Path

import pytest


def resource_module():
    return importlib.import_module("phatch.resources.provider")


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "..",
        "/absolute",
        "//server/share",
        "C:/drive",
        "C:\\drive",
        "folder//file",
        "folder/./file",
        "folder/../file",
        "folder\\..\\file",
        "bad\ud800name",
    ],
)
def test_logical_identifier_rejects_unsafe_input_before_resource_access(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: an identifier that is not a normalized package-relative path
    module = resource_module()
    monkeypatch.setattr(
        module.resources,
        "files",
        lambda package: (_ for _ in ()).throw(AssertionError("filesystem accessed")),
    )

    # When: the provider parses the boundary input
    # Then: it rejects the identifier without touching package storage
    with pytest.raises(module.InvalidResourceIdentifierError) as caught:
        module.ResourceProvider().read_bytes(value)
    assert "package-relative" in str(caught.value)


def test_provider_streams_lists_and_materializes_packaged_resources() -> None:
    # Given: the source package resource provider
    module = resource_module()
    provider = module.ResourceProvider()

    # When: callers use each narrow resource operation
    children = provider.iterdir("data/fonts")
    font_bytes = provider.read_bytes("data/fonts/FreeSans.ttf")
    geek_text = provider.read_text("data/geek.txt")
    with provider.as_path("data/fonts/FreeSans.ttf") as font_path:
        materialized = Path(font_path)
        materialized_bytes = materialized.read_bytes()

    # Then: the same packaged objects are exposed without a checkout lookup
    assert {child.name for child in children} >= {"FreeSans.ttf", "Purisa.ttf"}
    assert font_bytes[:4] == materialized_bytes[:4]
    assert "convert" in geek_text.lower()


def test_materialized_resource_cleanup_survives_interruption() -> None:
    # Given: a provider and a materialized package file
    module = resource_module()
    provider = module.ResourceProvider()
    materialized: Path | None = None

    # When: the consumer is interrupted inside the context
    with (
        pytest.raises(KeyboardInterrupt),
        provider.as_path("data/geek.txt") as resource_path,
    ):
        materialized = Path(resource_path)
        assert materialized.is_file()
        raise KeyboardInterrupt

    # Then: the resource was usable and the context closed cleanly
    assert materialized is not None


def test_missing_required_resource_has_typed_logical_diagnostic(tmp_path: Path) -> None:
    # Given: an injected resource root with one required object absent
    module = resource_module()
    provider = module.ResourceProvider.from_root(tmp_path)

    # When: a required resource is requested
    with pytest.raises(module.ResourceNotFoundError) as caught:
        provider.read_bytes("data/geek.txt")

    # Then: the diagnostic names only its logical identity
    assert caught.value.resource.value == "data/geek.txt"
    assert str(tmp_path) not in str(caught.value)


@pytest.mark.parametrize("operation", ["read_bytes", "read_text"])
def test_file_stream_operations_reject_directories(operation: str) -> None:
    # Given: a package directory passed to a file-only operation
    module = resource_module()
    provider = module.ResourceProvider()

    # When: the operation is invoked
    method = getattr(provider, operation)

    # Then: the typed resource diagnostic is raised
    with pytest.raises(module.ResourceNotFoundError):
        method("data/fonts")


def test_directory_iteration_rejects_files() -> None:
    # Given: a package file passed to a directory-only operation
    module = resource_module()
    provider = module.ResourceProvider()

    # When: directory iteration is invoked
    # Then: the typed resource diagnostic is raised
    with pytest.raises(module.ResourceNotFoundError):
        provider.iterdir("data/geek.txt")


def test_inventory_ignores_interpreter_cache_files(tmp_path: Path) -> None:
    # Given: interpreter-generated cache files beside packaged data scripts
    module = resource_module()
    (tmp_path / "data/__pycache__").mkdir(parents=True)
    (tmp_path / "data/__pycache__/runner.pyc").write_bytes(b"cache")
    (tmp_path / "data/runner.py").write_text("pass\n")
    provider = module.ResourceProvider.from_root(tmp_path)

    # When: package files are inventoried
    resources = provider.walk_files("data")

    # Then: only authoritative resources are exposed
    assert resources == (module.LogicalResource("data/runner.py"),)


def test_compressed_tree_materialization_copies_and_cleans_up(tmp_path: Path) -> None:
    # Given: resources stored behind a non-filesystem Traversable
    module = resource_module()
    archive_path = tmp_path / "resources.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("data/nested/example.txt", "payload")

    # When: a directory is materialized for a filesystem-only consumer
    with zipfile.ZipFile(archive_path) as archive:
        provider = module.ResourceProvider.from_root(zipfile.Path(archive))
        with provider.tree_as_path("data") as data_path:
            materialized = data_path
            assert (data_path / "nested" / "example.txt").read_text() == "payload"

    # Then: the temporary tree is removed when the context closes
    assert not materialized.exists()


def test_direct_paths_reject_compressed_resources(tmp_path: Path) -> None:
    # Given: a compressed resource package
    module = resource_module()
    resource_config = importlib.import_module("phatch.core.resource_config")
    archive_path = tmp_path / "resources.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("data/example.txt", "payload")

    # When: legacy direct-path lookup is attempted
    with zipfile.ZipFile(archive_path) as archive:
        provider = module.ResourceProvider.from_root(zipfile.Path(archive))
        with pytest.raises(resource_config.CompressedResourceError):
            resource_config.direct_config_paths(provider)


def test_injected_packaged_config_materializes_all_runtime_roots(
    tmp_path: Path,
) -> None:
    # Given: a complete injected resource root
    module = resource_module()
    resource_config = importlib.import_module("phatch.core.resource_config")
    for directory in ("data", "images", "locale", "docs/html"):
        (tmp_path / directory).mkdir(parents=True)
    provider = module.ResourceProvider.from_root(tmp_path)

    # When: runtime paths are materialized through the provider
    with resource_config.packaged_config_paths(provider) as paths:
        result = dict(paths)
        assert Path(result["PHATCH_DATA_PATH"]).is_dir()
        assert Path(result["PHATCH_IMAGE_PATH"]).is_dir()
        assert Path(result["PHATCH_LOCALE_PATH"]).is_dir()
        assert Path(result["PHATCH_DOCS_PATH"]).is_dir()

    # Then: isolated runtime roots are removed with the provider context
    assert not Path(result["PHATCH_DATA_PATH"]).exists()
    assert not Path(result["PHATCH_IMAGE_PATH"]).exists()
    assert not Path(result["PHATCH_LOCALE_PATH"]).exists()
    assert not Path(result["PHATCH_DOCS_PATH"]).exists()
