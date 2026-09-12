from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
from typing import Any, cast

import pytest

from phatch.core.user_paths import (
    HostPlatform,
    PathResolution,
    UserPathError,
    initialize_user_paths,
    current_platform,
    platform_directory_provider,
    resolve_user_paths,
)


class FakeProvider:
    def __init__(self, root: Path) -> None:
        self.config_path = root / "config"
        self.data_path = root / "data"
        self.cache_path = root / "cache"
        self.log_path = root / "logs"
        self.home_path = root / "home"


class RecordingFactory:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[tuple[HostPlatform, bool]] = []

    def __call__(self, platform: HostPlatform, roaming: bool) -> FakeProvider:
        self.calls.append((platform, roaming))
        location = "roaming" if roaming else "local"
        return FakeProvider(self.root / location)


def request(
    platform: HostPlatform,
    environment: dict[str, str] | None = None,
    portable_root: Path | None = None,
) -> PathResolution:
    return PathResolution(environment or {}, platform, portable_root)


def test_windows_uses_roaming_config_data_and_local_rebuildable_state(
    tmp_path: Path,
) -> None:
    # Given
    factory = RecordingFactory(tmp_path)

    # When
    paths = resolve_user_paths(request(HostPlatform.WINDOWS), factory)

    # Then
    assert paths.config == tmp_path / "roaming/config"
    assert paths.data == tmp_path / "roaming/data"
    assert paths.cache == tmp_path / "local/cache"
    assert paths.logs == tmp_path / "local/logs"
    assert paths.previews == tmp_path / "local/cache/previews"
    assert paths.font_index == tmp_path / "local/cache/fonts.index"
    assert factory.calls == [
        (HostPlatform.WINDOWS, True),
        (HostPlatform.WINDOWS, False),
    ]


@pytest.mark.parametrize("platform", [HostPlatform.MACOS, HostPlatform.LINUX])
def test_non_windows_uses_platformdirs_defaults(
    platform: HostPlatform, tmp_path: Path
) -> None:
    # Given
    factory = RecordingFactory(tmp_path)

    # When
    paths = resolve_user_paths(request(platform), factory)

    # Then
    assert paths.config == tmp_path / "local/config"
    assert paths.data == tmp_path / "local/data"
    assert paths.cache == tmp_path / "local/cache"
    assert factory.calls == [(platform, False)]


def test_platformdirs_layout_is_unversioned_without_duplicated_author(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg-cache"))

    # When
    provider = platform_directory_provider(HostPlatform.LINUX, False)

    # Then
    assert provider.config_path == tmp_path / "xdg-config/phatch"
    assert provider.data_path == tmp_path / "xdg-data/phatch"
    assert provider.cache_path == tmp_path / "xdg-cache/phatch"


@pytest.mark.parametrize(
    ("system_platform", "expected"),
    [
        ("win32", HostPlatform.WINDOWS),
        ("darwin", HostPlatform.MACOS),
        ("linux", HostPlatform.LINUX),
    ],
)
def test_current_platform_maps_supported_hosts(
    system_platform: str,
    expected: HostPlatform,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", system_platform)

    assert current_platform() is expected


def test_macos_platformdirs_provider_exposes_all_locations() -> None:
    provider = platform_directory_provider(HostPlatform.MACOS, False)

    assert provider.config_path.is_absolute()
    assert provider.data_path.is_absolute()
    assert provider.cache_path.is_absolute()
    assert provider.log_path.is_absolute()
    assert provider.home_path.is_absolute()


def test_windows_platformdirs_uses_documented_roaming_and_local_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    roaming = tmp_path / "Roaming Profile"
    local = tmp_path / "Local Profile"
    monkeypatch.setenv("WIN_PD_OVERRIDE_APPDATA", str(roaming))
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(local))

    # When
    paths = resolve_user_paths(request(HostPlatform.WINDOWS))

    # Then
    assert paths.config == roaming / "phatch"
    assert paths.data == roaming / "phatch"
    assert paths.cache == local / "phatch/Cache"
    assert paths.logs == local / "phatch/Logs"
    assert paths.previews.is_relative_to(local)
    assert paths.font_index.is_relative_to(local)


def test_precedence_is_portable_then_phatch_overrides_then_provider(
    tmp_path: Path,
) -> None:
    # Given
    factory = RecordingFactory(tmp_path / "provider")
    overrides = {
        "PHATCH_USER_CONFIG_DIR": str(tmp_path / "override/config"),
        "PHATCH_USER_DATA_DIR": str(tmp_path / "override/data"),
        "PHATCH_USER_CACHE_DIR": str(tmp_path / "override/cache"),
    }

    # When
    overridden = resolve_user_paths(request(HostPlatform.LINUX, overrides), factory)
    portable = resolve_user_paths(
        request(HostPlatform.LINUX, overrides, tmp_path / "portable"), factory
    )

    # Then
    assert overridden.config == tmp_path / "override/config"
    assert overridden.data == tmp_path / "override/data"
    assert overridden.cache == tmp_path / "override/cache"
    assert portable.config == tmp_path / "portable/config"
    assert portable.data == tmp_path / "portable/data"
    assert portable.cache == tmp_path / "portable/cache"


@pytest.mark.parametrize(
    "value", ["", "   ", "relative/root", "bad\x00root", "bad\nroot"]
)
def test_invalid_portable_or_override_paths_are_rejected(
    value: str, tmp_path: Path
) -> None:
    # Given
    factory = RecordingFactory(tmp_path)
    resolution = request(
        HostPlatform.LINUX,
        {"PHATCH_USER_DATA_DIR": value},
    )

    # When / Then
    with pytest.raises(UserPathError):
        resolve_user_paths(resolution, factory)


def test_relative_portable_root_is_rejected(tmp_path: Path) -> None:
    # Given
    factory = RecordingFactory(tmp_path)

    # When / Then
    with pytest.raises(UserPathError):
        resolve_user_paths(
            request(HostPlatform.LINUX, portable_root=Path("relative")), factory
        )


def test_user_path_error_has_actionable_message() -> None:
    assert str(UserPathError("PHATCH_USER_DATA_DIR", "relative")) == (
        "PHATCH_USER_DATA_DIR must be a non-empty absolute path without controls"
    )


def test_resolution_is_immutable_and_does_not_create_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    factory = RecordingFactory(tmp_path / "missing")

    # When
    paths = resolve_user_paths(request(HostPlatform.LINUX), factory)

    # Then
    with pytest.raises(FrozenInstanceError):
        monkeypatch.setattr(paths, "cache", tmp_path)
    assert not (tmp_path / "missing").exists()


def test_resolution_snapshots_caller_environment(tmp_path: Path) -> None:
    environment = {"PHATCH_USER_DATA_DIR": str(tmp_path / "original")}
    resolution = PathResolution(environment, HostPlatform.LINUX)
    environment["PHATCH_USER_DATA_DIR"] = str(tmp_path / "mutated")

    paths = resolve_user_paths(resolution, RecordingFactory(tmp_path / "provider"))

    assert paths.data == tmp_path / "original"
    environment_view = cast(Any, resolution.environment)
    with pytest.raises(TypeError):
        environment_view["PHATCH_USER_DATA_DIR"] = str(tmp_path / "blocked")


def test_explicit_initialization_creates_only_user_directories(tmp_path: Path) -> None:
    # Given
    root = tmp_path / "portable unicode space"
    paths = resolve_user_paths(
        request(HostPlatform.LINUX, portable_root=root), RecordingFactory(tmp_path)
    )

    # When
    initialize_user_paths(paths)

    # Then
    expected = (
        paths.config,
        paths.data,
        paths.cache,
        paths.logs,
        paths.previews,
        paths.actions,
        paths.actionlists,
        paths.fonts,
    )
    assert all(path.is_dir() for path in expected)
    assert all(path.is_relative_to(root) for path in expected)
