from __future__ import annotations

import os
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypeAlias, assert_never

from phatch.core.execution_types import DiscoveredFile


@dataclass(frozen=True, slots=True)
class DirectoryListing:
    folder: Path
    files: tuple[str, ...]


class DiscoveryFileSystem(Protocol):
    def absolute(self, path: Path) -> Path: ...

    def is_file(self, path: Path) -> bool: ...

    def is_dir(self, path: Path) -> bool: ...

    def list_files(self, folder: Path) -> DirectoryListing: ...

    def walk_files(self, folder: Path) -> Iterable[DirectoryListing]: ...


class LocalDiscoveryFileSystem:
    __slots__ = ()

    def absolute(self, path: Path) -> Path:
        return Path(os.path.abspath(path))

    def is_file(self, path: Path) -> bool:
        return os.path.isfile(path)

    def is_dir(self, path: Path) -> bool:
        return os.path.isdir(path)

    def list_files(self, folder: Path) -> DirectoryListing:
        return DirectoryListing(folder, tuple(os.listdir(folder)))

    def walk_files(self, folder: Path) -> Iterator[DirectoryListing]:
        for current, _directories, files in os.walk(folder):
            yield DirectoryListing(Path(current), tuple(files))


@dataclass(frozen=True, slots=True)
class ResolvedFile:
    path: Path


@dataclass(frozen=True, slots=True)
class ResolvedFolder:
    path: Path


ResolvedInput: TypeAlias = ResolvedFile | ResolvedFolder


@dataclass(slots=True)
class InvalidDiscoveryPathError(ValueError):
    path: Path

    def __str__(self) -> str:
        return f'"{self.path}" is not a valid path.'


class FileDiscovery:
    __slots__ = ("_filesystem",)

    def __init__(self, filesystem: DiscoveryFileSystem) -> None:
        self._filesystem = filesystem

    def resolve(self, raw_path: str) -> ResolvedInput:
        path = self._filesystem.absolute(Path(raw_path.strip()))
        if self._filesystem.is_file(path):
            return ResolvedFile(path)
        if self._filesystem.is_dir(path):
            return ResolvedFolder(path)
        raise InvalidDiscoveryPathError(path)

    def listings(self, folder: Path, *, recursive: bool) -> Iterable[DirectoryListing]:
        if recursive:
            return self._filesystem.walk_files(folder)
        return (self._filesystem.list_files(folder),)

    def candidates(
        self,
        listing: DirectoryListing,
        source_root: Path,
    ) -> tuple[DiscoveredFile, ...]:
        return tuple(
            DiscoveredFile(listing.folder / name, source_root=source_root)
            for name in sorted(listing.files, key=str.lower)
        )

    def is_file(self, path: Path) -> bool:
        return self._filesystem.is_file(path)

    def discover_folder(
        self,
        folder: Path,
        extensions: Sequence[str],
        *,
        recursive: bool,
    ) -> tuple[DiscoveredFile, ...]:
        normalized_extensions = frozenset(extension.lower() for extension in extensions)
        discovered: list[DiscoveredFile] = []
        for listing in self.listings(folder, recursive=recursive):
            folder_index = 0
            for candidate in self.candidates(listing, folder):
                extension = candidate.path.suffix.lstrip(".").lower()
                if self.is_file(candidate.path) and extension in normalized_extensions:
                    discovered.append(
                        DiscoveredFile(candidate.path, folder, folder_index)
                    )
                    folder_index += 1
        return tuple(discovered)

    def discover(
        self,
        paths: Sequence[str],
        extensions: Sequence[str],
        *,
        recursive: bool,
    ) -> tuple[DiscoveredFile, ...]:
        discovered: list[DiscoveredFile] = []
        normalized_extensions = frozenset(extension.lower() for extension in extensions)
        for raw_path in paths:
            match self.resolve(raw_path):
                case ResolvedFile(path):
                    if path.suffix.lstrip(".").lower() in normalized_extensions:
                        discovered.append(DiscoveredFile(path))
                case ResolvedFolder(path):
                    discovered.extend(
                        self.discover_folder(path, extensions, recursive=recursive)
                    )
                case unreachable:
                    assert_never(unreachable)
        return tuple(sorted(discovered, key=lambda source: str(source.path)))
