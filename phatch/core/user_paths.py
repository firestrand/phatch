from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Final, Protocol, assert_never

from platformdirs.api import PlatformDirsABC
from platformdirs.macos import MacOS
from platformdirs.unix import Unix
from platformdirs.windows import Windows

APP_NAME: Final = "phatch"
CONFIG_OVERRIDE: Final = "PHATCH_USER_CONFIG_DIR"
DATA_OVERRIDE: Final = "PHATCH_USER_DATA_DIR"
CACHE_OVERRIDE: Final = "PHATCH_USER_CACHE_DIR"


class HostPlatform(StrEnum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


class DirectoryProvider(Protocol):
    @property
    def config_path(self) -> Path: ...

    @property
    def data_path(self) -> Path: ...

    @property
    def cache_path(self) -> Path: ...

    @property
    def log_path(self) -> Path: ...

    @property
    def home_path(self) -> Path: ...


class DirectoryProviderFactory(Protocol):
    def __call__(self, platform: HostPlatform, roaming: bool) -> DirectoryProvider: ...


@dataclass(frozen=True, slots=True)
class PlatformDirectoryProvider:
    directories: PlatformDirsABC

    @property
    def config_path(self) -> Path:
        return self.directories.user_config_path

    @property
    def data_path(self) -> Path:
        return self.directories.user_data_path

    @property
    def cache_path(self) -> Path:
        return self.directories.user_cache_path

    @property
    def log_path(self) -> Path:
        return self.directories.user_log_path

    @property
    def home_path(self) -> Path:
        return Path.home()


@dataclass(frozen=True, slots=True)
class UserPaths:
    home: Path
    config: Path
    data: Path
    cache: Path
    logs: Path
    previews: Path
    font_index: Path
    settings: Path
    actions: Path
    actionlists: Path
    binaries: Path
    fonts: Path
    geek: Path
    masks: Path
    highlights: Path
    watermarks: Path


@dataclass(frozen=True, slots=True)
class PathResolution:
    environment: Mapping[str, str]
    platform: HostPlatform
    portable_root: os.PathLike[str] | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "environment", MappingProxyType(dict(self.environment))
        )


@dataclass(frozen=True, slots=True)
class UserPathError(ValueError):
    name: str
    value: str

    def __str__(self) -> str:
        return f"{self.name} must be a non-empty absolute path without controls"


def current_platform() -> HostPlatform:
    if sys.platform.startswith("win"):
        return HostPlatform.WINDOWS
    if sys.platform == "darwin":
        return HostPlatform.MACOS
    return HostPlatform.LINUX


def platform_directory_provider(
    platform: HostPlatform, roaming: bool
) -> PlatformDirectoryProvider:
    match platform:
        case HostPlatform.WINDOWS:
            directory_type = Windows
        case HostPlatform.MACOS:
            directory_type = MacOS
        case HostPlatform.LINUX:
            directory_type = Unix
        case unreachable:
            assert_never(unreachable)
    directories = directory_type(
        APP_NAME,
        appauthor=False,
        version=None,
        roaming=roaming,
        ensure_exists=False,
    )
    return PlatformDirectoryProvider(directories)


def _absolute_path(name: str, value: os.PathLike[str] | str) -> Path:
    raw = os.fspath(value)
    if not raw.strip() or any(ord(character) < 32 for character in raw):
        raise UserPathError(name, raw)
    path = Path(raw)
    if not path.is_absolute():
        raise UserPathError(name, raw)
    return path


def _roots(
    resolution: PathResolution, provider_factory: DirectoryProviderFactory
) -> tuple[Path, Path, Path, Path, Path]:
    if resolution.portable_root is not None:
        root = _absolute_path("portable_root", resolution.portable_root)
        return root, root / "config", root / "data", root / "cache", root / "cache/logs"

    roaming = resolution.platform is HostPlatform.WINDOWS
    persistent = provider_factory(resolution.platform, roaming)
    local = provider_factory(resolution.platform, False) if roaming else persistent
    environment = resolution.environment
    config = _override(environment, CONFIG_OVERRIDE, persistent.config_path)
    data = _override(environment, DATA_OVERRIDE, persistent.data_path)
    cache = _override(environment, CACHE_OVERRIDE, local.cache_path)
    logs = cache / "logs" if CACHE_OVERRIDE in environment else local.log_path
    return persistent.home_path, config, data, cache, logs


def _override(environment: Mapping[str, str], name: str, fallback: Path) -> Path:
    if name not in environment:
        return fallback
    return _absolute_path(name, environment[name])


def resolve_user_paths(
    resolution: PathResolution,
    provider_factory: DirectoryProviderFactory = platform_directory_provider,
) -> UserPaths:
    home, config, data, cache, logs = _roots(resolution, provider_factory)
    return UserPaths(
        home=home,
        config=config,
        data=data,
        cache=cache,
        logs=logs,
        previews=cache / "previews",
        font_index=cache / "fonts.index",
        settings=config / "settings.py",
        actions=data / "actions",
        actionlists=data / "actionlists",
        binaries=data / "bin",
        fonts=data / "fonts",
        geek=data / "geek.txt",
        masks=data / "masks",
        highlights=data / "highlights",
        watermarks=data / "watermarks",
    )


def initialize_user_paths(paths: UserPaths) -> None:
    directories = (
        paths.config,
        paths.data,
        paths.cache,
        paths.logs,
        paths.previews,
        paths.actions,
        paths.actionlists,
        paths.binaries,
        paths.fonts,
        paths.masks,
        paths.highlights,
        paths.watermarks,
    )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
