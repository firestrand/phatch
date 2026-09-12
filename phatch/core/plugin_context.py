from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Protocol

from phatch.external_tools import ExternalTools, default_external_tools
from phatch.lib import system


class MetadataTarget(Protocol):
    def save(self, filename: str) -> str | None: ...


class FileOperations(Protocol):
    def exists(self, path: str) -> bool: ...

    def ensure_path(self, path: str) -> None: ...

    def copy2(self, source: str, destination: str) -> None: ...

    def rename(self, source: str, destination: str) -> None: ...

    def utime(self, path: str, times: tuple[float, float]) -> None: ...


class MetadataOperations(Protocol):
    def save(self, target: MetadataTarget, filename: str) -> str | None: ...


@dataclass(frozen=True, slots=True)
class StdlibFileOperations:
    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def ensure_path(self, path: str) -> None:
        system.ensure_path(path)

    def copy2(self, source: str, destination: str) -> None:
        shutil.copy2(source, destination)

    def rename(self, source: str, destination: str) -> None:
        os.rename(source, destination)

    def utime(self, path: str, times: tuple[float, float]) -> None:
        os.utime(path, times)


@dataclass(frozen=True, slots=True)
class DefaultMetadataOperations:
    def save(self, target: MetadataTarget, filename: str) -> str | None:
        return target.save(filename)


@dataclass(frozen=True, slots=True)
class PluginContext:
    files: FileOperations
    metadata: MetadataOperations
    external_tools: ExternalTools


def default_plugin_context() -> PluginContext:
    return PluginContext(
        files=StdlibFileOperations(),
        metadata=DefaultMetadataOperations(),
        external_tools=default_external_tools(),
    )
