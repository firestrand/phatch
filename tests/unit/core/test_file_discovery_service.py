from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from phatch.core.execution_types import DiscoveredFile
from phatch.services.file_discovery import (
    DirectoryListing,
    FileDiscovery,
    InvalidDiscoveryPathError,
    LocalDiscoveryFileSystem,
)


def test_service_import_does_not_load_legacy_api() -> None:
    # Given
    command = (
        sys.executable,
        "-c",
        "import sys; import phatch.services.file_discovery; "
        "sys.exit(int('phatch.core.api' in sys.modules))",
    )

    # When
    completed = subprocess.run(command, check=False)

    # Then
    assert completed.returncode == 0


def test_service_package_preserves_lazy_action_list_exports() -> None:
    # Given
    import phatch.services as services

    # When
    exported = services.ActionListService

    # Then
    assert exported.__name__ == "ActionListService"


def test_service_package_rejects_unknown_export() -> None:
    # Given
    import phatch.services as services

    # When / Then
    with pytest.raises(AttributeError):
        services.__getattr__("missing_export")


class FakeFileSystem:
    __slots__ = ("calls", "directories", "files", "listings", "walks")

    def __init__(
        self,
        *,
        files: frozenset[Path],
        directories: frozenset[Path] = frozenset(),
        listings: tuple[DirectoryListing, ...] = (),
        walks: tuple[DirectoryListing, ...] = (),
    ) -> None:
        self.files = files
        self.directories = directories
        self.listings = listings
        self.walks = walks
        self.calls: list[tuple[str, Path]] = []

    def absolute(self, path: Path) -> Path:
        self.calls.append(("absolute", path))
        return path if path.is_absolute() else Path("/virtual") / path

    def is_file(self, path: Path) -> bool:
        self.calls.append(("is_file", path))
        return path in self.files

    def is_dir(self, path: Path) -> bool:
        self.calls.append(("is_dir", path))
        return path in self.directories

    def list_files(self, folder: Path) -> DirectoryListing:
        self.calls.append(("list_files", folder))
        return self.listings[0]

    def walk_files(self, folder: Path) -> tuple[DirectoryListing, ...]:
        self.calls.append(("walk_files", folder))
        return self.walks


def forbid_real_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(
        filesystem: LocalDiscoveryFileSystem,
        path: Path,
    ) -> Path:
        del filesystem, path
        pytest.fail("real filesystem access escaped the injected fake")

    monkeypatch.setattr(LocalDiscoveryFileSystem, "absolute", fail)
    monkeypatch.setattr(LocalDiscoveryFileSystem, "is_file", fail)
    monkeypatch.setattr(LocalDiscoveryFileSystem, "is_dir", fail)
    monkeypatch.setattr(LocalDiscoveryFileSystem, "list_files", fail)
    monkeypatch.setattr(LocalDiscoveryFileSystem, "walk_files", fail)


def test_explicit_files_apply_extensions_consistently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    forbid_real_filesystem(monkeypatch)
    explicit = Path("/virtual/사진 space/notes.unsupported")
    filesystem = FakeFileSystem(files=frozenset((explicit,)))

    # When
    discovered = FileDiscovery(filesystem).discover(
        ("  사진 space/notes.unsupported  ", "사진 space/notes.unsupported"),
        ("jpg",),
        recursive=False,
    )

    # Then
    assert discovered == ()


def test_nonrecursive_folder_sorts_case_insensitively_and_filters_extensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    forbid_real_filesystem(monkeypatch)
    root = Path("/virtual/Album")
    first = root / "alpha.JPG"
    second = root / "Beta.png"
    ignored = root / "zero.txt"
    filesystem = FakeFileSystem(
        files=frozenset((first, second, ignored)),
        directories=frozenset((root,)),
        listings=(DirectoryListing(root, ("zero.txt", "Beta.png", "alpha.JPG")),),
    )
    extensions = ("PnG", "JPG")

    # When
    discovered = FileDiscovery(filesystem).discover(
        ("Album",), extensions, recursive=False
    )

    # Then
    assert discovered == (
        DiscoveredFile(second, source_root=root, folder_index=1),
        DiscoveredFile(first, source_root=root, folder_index=0),
    )
    assert extensions == ("PnG", "JPG")
    assert ("walk_files", root) not in filesystem.calls


def test_recursive_discovery_preserves_walk_batches_then_sorts_full_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    forbid_real_filesystem(monkeypatch)
    root = Path("/virtual/root")
    later = root / "z" / "A.jpg"
    earlier = root / "a" / "b.JPG"
    filesystem = FakeFileSystem(
        files=frozenset((later, earlier)),
        directories=frozenset((root,)),
        walks=(
            DirectoryListing(later.parent, (later.name,)),
            DirectoryListing(earlier.parent, (earlier.name,)),
        ),
    )

    # When
    discovered = FileDiscovery(filesystem).discover(("root",), ("jpg",), recursive=True)

    # Then
    assert discovered == (
        DiscoveredFile(earlier, source_root=root, folder_index=0),
        DiscoveredFile(later, source_root=root, folder_index=0),
    )
    assert ("list_files", root) not in filesystem.calls


def test_invalid_path_after_valid_raises_without_partial_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    forbid_real_filesystem(monkeypatch)
    valid = Path("/virtual/valid.jpg")
    missing = Path("/virtual/missing.jpg")
    filesystem = FakeFileSystem(files=frozenset((valid,)))

    # When
    with pytest.raises(InvalidDiscoveryPathError) as error:
        FileDiscovery(filesystem).discover(
            ("valid.jpg", "missing.jpg"), ("jpg",), recursive=False
        )

    # Then
    assert error.value.path == missing
    assert str(error.value) == f'"{missing}" is not a valid path.'


def test_local_filesystem_adapter_exposes_required_operations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    nested = tmp_path / "nested"
    image = nested / "photo.jpg"
    nested.mkdir()
    image.write_text("photo", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    filesystem = LocalDiscoveryFileSystem()

    # When
    absolute = filesystem.absolute(Path("nested/photo.jpg"))
    listed = filesystem.list_files(nested)
    walked = tuple(filesystem.walk_files(tmp_path))

    # Then
    assert absolute == image
    assert filesystem.is_file(image)
    assert filesystem.is_dir(nested)
    assert listed == DirectoryListing(nested, ("photo.jpg",))
    assert walked == (
        DirectoryListing(tmp_path, ()),
        DirectoryListing(nested, ("photo.jpg",)),
    )
