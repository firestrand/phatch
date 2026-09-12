from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path

import pytest

from phatch.resources.provider import (
    InvalidResourceIdentifierError,
    LogicalResource,
    ResourceNotFoundError,
    ResourceProvider,
)

EXTERNAL_PAYLOAD = "outside-root-secret"


class StorageMustNotBeTouchedProvider(ResourceProvider):
    def _root(self):
        raise AssertionError("storage accessed")


@pytest.mark.parametrize(
    "value",
    [
        None,
        b"data/file.txt",
        1,
        "data/\x00.txt",
        "data/\n.txt",
        "data/\r.txt",
        "data/\t.txt",
        "data/\x80.txt",
        "data/cafe\u0301.txt",
    ],
)
def test_malformed_identifier_is_rejected_before_storage_access(value) -> None:
    # Given: a provider whose storage seam fails if reached
    provider = StorageMustNotBeTouchedProvider()

    # When: an invalid identifier crosses the provider boundary
    # Then: parsing fails before storage access
    with pytest.raises(InvalidResourceIdentifierError):
        provider.read_bytes(value)


def test_valid_normalized_unicode_identifier_is_preserved() -> None:
    # Given: a valid NFC package-relative identifier
    value = "data/caf\u00e9/\u5199\u771f.txt"

    # When: it is parsed
    logical = LogicalResource.parse(value)

    # Then: its identity is preserved exactly
    assert logical.value == value


def _invoke_file_operation(provider: ResourceProvider, operation: str) -> None:
    if operation == "as_path":
        context = provider.as_path("data/link.txt")
        with context:
            return
    getattr(provider, operation)("data/link.txt")


@pytest.mark.parametrize(
    "operation",
    ["traversable", "read_bytes", "read_text", "as_path"],
)
def test_file_symlink_escape_is_rejected_for_every_file_surface(
    tmp_path: Path, operation: str
) -> None:
    # Given: a resource file symlink targeting an external payload
    root = tmp_path / "root"
    outside = tmp_path / "outside.txt"
    (root / "data").mkdir(parents=True)
    outside.write_text("outside-root-secret", encoding="utf-8")
    (root / "data/link.txt").symlink_to(outside)
    provider = ResourceProvider.from_root(root)

    # When: any file surface resolves the logical resource
    # Then: the provider rejects it before external data is accessed
    with pytest.raises(ResourceNotFoundError):
        _invoke_file_operation(provider, operation)


@pytest.mark.parametrize(
    "operation",
    ["traversable", "iterdir", "walk_files", "tree_as_path"],
)
def test_directory_symlink_escape_is_rejected_for_every_tree_surface(
    tmp_path: Path, operation: str
) -> None:
    # Given: a nested resource directory symlink targeting an external tree
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    (root / "data/nested").mkdir(parents=True)
    outside.mkdir()
    (outside / "secret.txt").write_text("outside-root-secret", encoding="utf-8")
    (root / "data/nested/link").symlink_to(outside, target_is_directory=True)
    provider = ResourceProvider.from_root(root)

    # When: any tree surface reaches the symlink
    # Then: the complete operation fails without exposing the external tree
    with pytest.raises(ResourceNotFoundError):
        result = getattr(provider, operation)("data/nested/link")
        if isinstance(result, AbstractContextManager):
            with result:
                return


def test_broken_symlink_is_rejected_during_iteration(tmp_path: Path) -> None:
    # Given: an injected resource directory containing a broken link
    root = tmp_path / "root"
    (root / "data").mkdir(parents=True)
    (root / "data/broken.txt").symlink_to(tmp_path / "missing.txt")
    provider = ResourceProvider.from_root(root)

    # When: callers list the directory
    # Then: iteration rejects the link rather than exposing its identity
    with pytest.raises(ResourceNotFoundError):
        provider.iterdir("data")


def test_normal_in_root_resources_remain_available(tmp_path: Path) -> None:
    # Given: ordinary files and directories entirely within the injected root
    root = tmp_path / "root"
    (root / "data/nested").mkdir(parents=True)
    (root / "data/nested/file.txt").write_text("payload", encoding="utf-8")
    provider = ResourceProvider.from_root(root)

    # When: callers use every resource shape
    files = provider.walk_files("data")
    text = provider.read_text("data/nested/file.txt")
    with provider.as_path("data/nested/file.txt") as file_path:
        materialized = file_path.read_text(encoding="utf-8")
    with provider.tree_as_path("data") as tree_path:
        tree_payload = (tree_path / "nested/file.txt").read_text(encoding="utf-8")

    # Then: normal resources remain available unchanged
    assert files == (LogicalResource("data/nested/file.txt"),)
    assert text == materialized == tree_payload == "payload"


@pytest.mark.parametrize("operation", ["read_bytes", "read_text", "as_path"])
def test_file_replacement_after_validation_cannot_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    # Given: a validated file replaced by an external symlink before consumption
    root = tmp_path / "root"
    target = root / "data/file.txt"
    outside = tmp_path / "outside.txt"
    target.parent.mkdir(parents=True)
    target.write_text("inside", encoding="utf-8")
    outside.write_text(EXTERNAL_PAYLOAD, encoding="utf-8")
    original = Path.is_file
    replaced = False

    def replace_after_validation(path: Path) -> bool:
        nonlocal replaced
        result = original(path)
        if not replaced and path == target and result:
            replaced = True
            target.unlink()
            target.symlink_to(outside)
        return result

    monkeypatch.setattr(Path, "is_file", replace_after_validation)
    provider = ResourceProvider.from_root(root)

    # When: a file consumer reaches the replacement window
    # Then: it fails closed without returning or materializing external bytes
    with pytest.raises(ResourceNotFoundError):
        result = getattr(provider, operation)("data/file.txt")
        if isinstance(result, AbstractContextManager):
            with result as path:
                assert path.read_text(encoding="utf-8") != EXTERNAL_PAYLOAD


@pytest.mark.parametrize("replacement", ["parent", "root"])
def test_directory_replacement_during_iteration_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    # Given: a validated directory replaced before its entries are consumed
    root = tmp_path / "root"
    data = root / "data"
    outside = tmp_path / "outside"
    data.mkdir(parents=True)
    (data / "inside.txt").write_text("inside", encoding="utf-8")
    outside.mkdir()
    (outside / "secret.txt").write_text(EXTERNAL_PAYLOAD, encoding="utf-8")
    original = Path.is_dir
    replaced = False

    def replace_after_validation(path: Path) -> bool:
        nonlocal replaced
        result = original(path)
        if not replaced and path == data and result:
            replaced = True
            if replacement == "root":
                root.rename(tmp_path / "original-root")
                outside.rename(root)
            else:
                data.rename(root / "original-data")
                (root / "data").symlink_to(outside, target_is_directory=True)
        return result

    monkeypatch.setattr(Path, "is_dir", replace_after_validation)
    provider = ResourceProvider.from_root(root)

    # When: directory iteration crosses the replacement window
    # Then: no external logical identity is returned
    with pytest.raises(ResourceNotFoundError):
        provider.iterdir("data")


def test_materialized_paths_are_owned_copies(tmp_path: Path) -> None:
    # Given: ordinary resources in a mutable injected filesystem root
    root = tmp_path / "root"
    file_path = root / "data/file.txt"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("inside", encoding="utf-8")
    provider = ResourceProvider.from_root(root)

    # When: file and tree paths are materialized
    with provider.as_path("data/file.txt") as copied_file:
        with provider.tree_as_path("data") as copied_tree:
            file_path.write_text(EXTERNAL_PAYLOAD, encoding="utf-8")
            file_value = copied_file.read_text(encoding="utf-8")
            tree_value = (copied_tree / "file.txt").read_text(encoding="utf-8")
        tree_exists = copied_tree.exists()
    file_exists = copied_file.exists()

    # Then: yielded paths are isolated copies and clean up after their contexts
    assert file_value == tree_value == "inside"
    assert copied_file != file_path
    assert not file_exists
    assert not tree_exists


@pytest.mark.parametrize("error_type", [RuntimeError, KeyboardInterrupt])
def test_materialized_file_cleans_up_on_exception(
    tmp_path: Path, error_type: type[BaseException]
) -> None:
    # Given: a filesystem resource provider
    resource = tmp_path / "data/file.txt"
    resource.parent.mkdir(parents=True)
    resource.write_text("inside", encoding="utf-8")
    provider = ResourceProvider.from_root(tmp_path)
    materialized_paths: list[Path] = []

    # When: materialized path use exits exceptionally
    with (
        pytest.raises(error_type),
        provider.as_path("data/file.txt") as materialized,
    ):
        materialized_paths.append(materialized)
        raise error_type

    # Then: provider-owned temporary state is cleaned up
    assert not materialized_paths[0].exists()


def test_replaced_root_identity_is_rejected(tmp_path: Path) -> None:
    # Given: a provider bound to a filesystem root identity
    root = tmp_path / "root"
    target = root / "data/file.txt"
    target.parent.mkdir(parents=True)
    target.write_text("inside", encoding="utf-8")
    provider = ResourceProvider.from_root(root)
    root.rename(tmp_path / "original-root")
    target.parent.mkdir(parents=True)
    target.write_text(EXTERNAL_PAYLOAD, encoding="utf-8")

    # When: the same root name resolves to a replacement directory
    # Then: the captured root identity causes access to fail closed
    with pytest.raises(ResourceNotFoundError):
        provider.read_bytes("data/file.txt")


def test_symlink_root_is_rejected(tmp_path: Path) -> None:
    # Given: an injected root that is itself an external symlink
    outside = tmp_path / "outside"
    (outside / "data").mkdir(parents=True)
    (outside / "data/file.txt").write_text(EXTERNAL_PAYLOAD, encoding="utf-8")
    root = tmp_path / "root"
    root.symlink_to(outside, target_is_directory=True)
    provider = ResourceProvider.from_root(root)

    # When: a resource read crosses the symlink root
    # Then: the provider rejects it without consuming external bytes
    with pytest.raises(ResourceNotFoundError):
        provider.read_bytes("data/file.txt")


def test_file_identity_change_after_open_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a file replaced after its handle is opened
    target = tmp_path / "data/file.txt"
    target.parent.mkdir(parents=True)
    target.write_text("inside", encoding="utf-8")
    provider = ResourceProvider.from_root(tmp_path)
    original_open = Path.open
    replaced = False

    def open_then_replace(path: Path, *args, **kwargs):
        nonlocal replaced
        source = original_open(path, *args, **kwargs)
        if path == target and not replaced:
            replaced = True
            path.rename(tmp_path / "original.txt")
            path.write_text(EXTERNAL_PAYLOAD, encoding="utf-8")
        return source

    monkeypatch.setattr(Path, "open", open_then_replace)

    # When: the provider verifies the opened handle against the current path
    # Then: differing identities fail closed
    with pytest.raises(ResourceNotFoundError):
        provider.read_bytes("data/file.txt")
