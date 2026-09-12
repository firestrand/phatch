from __future__ import annotations

import os
import tempfile
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import BinaryIO, Final

RESOURCE_PACKAGE: Final = "phatch_assets"


@dataclass(frozen=True, slots=True)
class LogicalResource:
    value: str

    @classmethod
    def parse(cls, value: str) -> LogicalResource:
        if not isinstance(value, str):
            raise InvalidResourceIdentifierError(value=repr(value))
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise InvalidResourceIdentifierError(value=value) from error
        parts = value.split("/")
        is_drive = len(value) >= 2 and value[1] == ":"
        has_control = any(
            unicodedata.category(character) == "Cc" for character in value
        )
        if (
            not value
            or not unicodedata.is_normalized("NFC", value)
            or has_control
            or value.startswith("/")
            or "\\" in value
            or is_drive
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise InvalidResourceIdentifierError(value=value)
        return cls(value=value)

    @property
    def name(self) -> str:
        return self.value.rsplit("/", 1)[-1]

    def child(self, name: str) -> LogicalResource:
        return LogicalResource.parse(f"{self.value}/{name}")


@dataclass(frozen=True, slots=True)
class InvalidResourceIdentifierError(ValueError):
    value: str

    def __str__(self) -> str:
        return "resource identifier must be a normalized package-relative path"


@dataclass(frozen=True, slots=True)
class ResourceNotFoundError(FileNotFoundError):
    resource: LogicalResource

    def __str__(self) -> str:
        return f"required packaged resource is missing: {self.resource.value}"


ResourceInput = str | LogicalResource


@dataclass(frozen=True, slots=True)
class ResourceProvider:
    package: str = RESOURCE_PACKAGE
    _injected_root: Traversable | None = None
    _root_identity: tuple[int, int] | None = None

    @classmethod
    def from_root(cls, root: Traversable) -> ResourceProvider:
        if isinstance(root, Path):
            status = root.stat(follow_symlinks=False)
            return cls(
                _injected_root=root,
                _root_identity=(status.st_dev, status.st_ino),
            )
        return cls(_injected_root=root)

    def _root(self) -> Traversable:
        if self._injected_root is not None:
            return self._injected_root
        return resources.files(self.package)

    @staticmethod
    def _parse(resource: ResourceInput) -> LogicalResource:
        if isinstance(resource, LogicalResource):
            return resource
        return LogicalResource.parse(resource)

    def traversable(self, resource: ResourceInput) -> Traversable:
        logical = self._parse(resource)
        root = self._root()
        if isinstance(root, Path):
            target = self._confined_path(root, logical)
        else:
            target = root
            for segment in logical.value.split("/"):
                target = target.joinpath(segment)
        if not target.is_file() and not target.is_dir():
            raise ResourceNotFoundError(resource=logical)
        return target

    def _confined_path(self, root: Path, logical: LogicalResource) -> Path:
        if root.is_symlink():
            raise ResourceNotFoundError(resource=logical)
        try:
            status = root.stat(follow_symlinks=False)
            if self._root_identity not in {None, (status.st_dev, status.st_ino)}:
                raise ResourceNotFoundError(resource=logical)
            resolved_root = root.resolve(strict=True)
        except (FileNotFoundError, OSError) as error:
            raise ResourceNotFoundError(resource=logical) from error
        target = root
        for part in logical.value.split("/"):
            target = target / part
            if target.is_symlink():
                raise ResourceNotFoundError(resource=logical)
            try:
                resolved_target = target.resolve(strict=False)
            except OSError as error:
                raise ResourceNotFoundError(resource=logical) from error
            if not resolved_target.is_relative_to(resolved_root):
                raise ResourceNotFoundError(resource=logical)
        return target

    def _read_filesystem_bytes(self, root: Path, logical: LogicalResource) -> bytes:
        target = self._confined_path(root, logical)
        if not target.is_file():
            raise ResourceNotFoundError(resource=logical)
        try:
            with target.open("rb") as source:
                self._verify_open_file(root, target, source, logical)
                return source.read()
        except (FileNotFoundError, OSError) as error:
            raise ResourceNotFoundError(resource=logical) from error

    def _verify_open_file(
        self,
        root: Path,
        target: Path,
        source: BinaryIO,
        logical: LogicalResource,
    ) -> None:
        self._confined_path(root, logical)
        path_status = target.stat(follow_symlinks=False)
        source_status = os.fstat(source.fileno())
        if (path_status.st_dev, path_status.st_ino) != (
            source_status.st_dev,
            source_status.st_ino,
        ):
            raise ResourceNotFoundError(resource=logical)

    def read_bytes(self, resource: ResourceInput) -> bytes:
        logical = self._parse(resource)
        root = self._root()
        if isinstance(root, Path):
            return self._read_filesystem_bytes(root, logical)
        target = self.traversable(logical)
        if not target.is_file():
            raise ResourceNotFoundError(resource=logical)
        return target.read_bytes()

    def read_text(self, resource: ResourceInput, encoding: str = "utf-8") -> str:
        return self.read_bytes(resource).decode(encoding)

    def iterdir(self, resource: ResourceInput) -> tuple[LogicalResource, ...]:
        logical = self._parse(resource)
        target = self.traversable(logical)
        if not target.is_dir():
            raise ResourceNotFoundError(resource=logical)
        root = self._root()
        before = None
        if isinstance(target, Path) and isinstance(root, Path):
            before = target.stat(follow_symlinks=False)
        entries = tuple(sorted(target.iterdir(), key=lambda item: item.name))
        if isinstance(target, Path) and isinstance(root, Path):
            self._confined_path(root, logical)
            after = target.stat(follow_symlinks=False)
            assert before is not None
            if (before.st_dev, before.st_ino) != (
                after.st_dev,
                after.st_ino,
            ):
                raise ResourceNotFoundError(resource=logical)
        children: list[LogicalResource] = []
        for child in entries:
            if child.name == "__pycache__" or child.name.endswith(".pyc"):
                continue
            child_logical = logical.child(child.name)
            self.traversable(child_logical)
            children.append(child_logical)
        return tuple(children)

    def walk_files(self, resource: ResourceInput) -> tuple[LogicalResource, ...]:
        logical = self._parse(resource)
        result: list[LogicalResource] = []
        self._walk(logical, result)
        return tuple(result)

    def _walk(self, logical: LogicalResource, result: list[LogicalResource]) -> None:
        target = self.traversable(logical)
        if target.is_file():
            result.append(logical)
            return
        for child in self.iterdir(logical):
            self._walk(child, result)

    @contextmanager
    def as_path(self, resource: ResourceInput) -> Iterator[Path]:
        logical = self._parse(resource)
        with tempfile.TemporaryDirectory(prefix="phatch-resource-") as directory:
            destination = Path(directory) / logical.name
            destination.write_bytes(self.read_bytes(logical))
            yield destination

    @contextmanager
    def tree_as_path(self, resource: ResourceInput) -> Iterator[Path]:
        logical = self._parse(resource)
        with tempfile.TemporaryDirectory(prefix="phatch-resource-") as directory:
            destination = Path(directory) / logical.name
            self._copy_tree(logical, destination)
            yield destination

    def _copy_tree(self, logical: LogicalResource, destination: Path) -> None:
        target = self.traversable(logical)
        if target.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(self.read_bytes(logical))
            return
        destination.mkdir(parents=True, exist_ok=True)
        for child in self.iterdir(logical):
            self._copy_tree(child, destination / child.name)
