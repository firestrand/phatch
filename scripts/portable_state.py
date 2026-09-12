from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Self


@dataclass(frozen=True, slots=True)
class PortableStateSnapshot:
    root: Path
    files: tuple[tuple[Path, bytes], ...]
    directories: frozenset[Path]

    @classmethod
    def capture(cls, root: Path) -> Self:
        return cls(
            root=root,
            files=tuple(
                (path.relative_to(root), path.read_bytes())
                for path in root.rglob("*")
                if path.is_file()
            ),
            directories=frozenset(
                path.relative_to(root) for path in root.rglob("*") if path.is_dir()
            ),
        )

    def is_unchanged(self) -> bool:
        return all(
            (self.root / relative).is_file()
            and (self.root / relative).read_bytes() == content
            for relative, content in self.files
        )

    def created_files(self) -> tuple[Path, ...]:
        initial_files = {relative for relative, _content in self.files}
        return tuple(
            path.relative_to(self.root)
            for path in self.root.rglob("*")
            if path.is_file() and path.relative_to(self.root) not in initial_files
        )

    def clean_created(self, created_files: tuple[Path, ...]) -> None:
        for relative in created_files:
            (self.root / relative).unlink()
        created_directories = sorted(
            (
                path
                for path in self.root.rglob("*")
                if path.is_dir() and path.relative_to(self.root) not in self.directories
            ),
            key=lambda path: len(path.parts),
            reverse=True,
        )
        for directory in created_directories:
            directory.rmdir()
