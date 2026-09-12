from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

RegistryLookup = Callable[[str], os.PathLike[str] | str | None]


@dataclass(frozen=True, slots=True)
class ExecutableLookup:
    search_directories: tuple[Path, ...] = ()
    path: str | None = None
    registry_lookup: RegistryLookup | None = None
    platform: str = sys.platform

    def find(self, name: str) -> Path | None:
        if not name or "\0" in name:
            return None
        if self.platform.startswith("win") and Path(name).suffix.lower() in {
            ".bat",
            ".cmd",
        }:
            return None

        explicit = Path(name)
        if explicit.is_absolute() or explicit.parent != Path("."):
            return self._usable_path(shutil.which(name, path=""))

        candidate_name = name
        if self.platform.startswith("win") and not Path(name).suffix:
            candidate_name = f"{name}.exe"
        configured_path = os.pathsep.join(
            os.fspath(directory) for directory in self.search_directories
        )
        if configured_path:
            configured = shutil.which(candidate_name, path=configured_path)
            found = self._usable_path(configured)
            if found is not None:
                return found
        if self.path:
            found = self._usable_path(shutil.which(candidate_name, path=self.path))
            if found is not None:
                return found
        if self.platform.startswith("win") and self.registry_lookup is not None:
            return self._usable_path(self.registry_lookup(name))
        return None

    def _usable_path(self, value: os.PathLike[str] | str | None) -> Path | None:
        if value is None:
            return None
        candidate = Path(value)
        if self.platform.startswith("win") and candidate.suffix.lower() in {
            ".bat",
            ".cmd",
        }:
            return None
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            return None
        return candidate.resolve()
