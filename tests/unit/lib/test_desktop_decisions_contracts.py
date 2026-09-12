from __future__ import annotations

import importlib.util
import os
import stat
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

from phatch.lib.linux import desktop as linux_desktop


class ShellModule(ModuleType):
    SHGetFolderPath: Callable[..., str]


class ShellConstantsModule(ModuleType):
    CSIDL_DESKTOP: int


class Win32ShellModule(ModuleType):
    shell: ShellModule
    shellcon: ShellConstantsModule


class Win32Module(ModuleType):
    shell: Win32ShellModule


def load_desktop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, platform: str
) -> ModuleType:
    module_path = Path(__file__).parents[3] / "phatch" / "lib" / "desktop.py"
    module_name = f"phatch.lib._desktop_{platform}_contract_test"
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setenv("HOME", str(tmp_path))
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_linux_desktop_parses_xdg_path_and_environment_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    desktop = tmp_path / "Workspace Desktop"
    desktop.mkdir()
    config = tmp_path / ".config"
    config.mkdir()
    (config / "user-dirs.dirs").write_text(
        'XDG_DESKTOP_DIR="$HOME/Workspace Desktop"\n', encoding="utf-8"
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "custom-config"))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)

    module = load_desktop(monkeypatch, tmp_path, "linux")

    assert str(desktop) == module.DESKTOP_FOLDER
    assert str(tmp_path / ".local" / "share") == module.USER_DATA_FOLDER
    assert str(tmp_path / "custom-config") == module.USER_CONFIG_FOLDER
    assert str(tmp_path / ".cache") == module.USER_CACHE_FOLDER
    assert module.USER_THUMBNAILS_NORMAL_FOLDER is None


def test_linux_desktop_falls_back_to_home_for_invalid_or_missing_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = tmp_path / ".config"
    config.mkdir()
    (config / "user-dirs.dirs").write_text("malformed=true\n", encoding="utf-8")

    module = load_desktop(monkeypatch, tmp_path, "linux-invalid")

    assert str(tmp_path) == module.DESKTOP_FOLDER


def test_linux_desktop_handles_absent_xdg_config_and_existing_thumbnail_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    desktop = tmp_path / "Desktop"
    thumbnails = tmp_path / ".thumbnails" / "normal"
    desktop.mkdir()
    thumbnails.mkdir(parents=True)

    module = load_desktop(monkeypatch, tmp_path, "linux-no-config")

    assert str(desktop) == module.DESKTOP_FOLDER
    assert str(thumbnails) == module.USER_THUMBNAILS_NORMAL_FOLDER


@pytest.mark.parametrize("platform", ["darwin", "win32"])
def test_non_linux_desktop_uses_home_without_native_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, platform: str
) -> None:
    (tmp_path / "Desktop").mkdir()
    monkeypatch.delitem(sys.modules, "win32com", raising=False)
    monkeypatch.delitem(sys.modules, "win32com.shell", raising=False)

    module = load_desktop(monkeypatch, tmp_path, platform)

    assert str(tmp_path / "Desktop") == module.DESKTOP_FOLDER
    assert str(tmp_path) == module.USER_DATA_FOLDER
    assert str(tmp_path) == module.USER_CONFIG_FOLDER
    assert str(tmp_path) == module.USER_CACHE_FOLDER


def test_windows_desktop_uses_injected_native_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    native_desktop = tmp_path / "Native Desktop"
    native_desktop.mkdir()
    shell_module = Win32ShellModule("win32com.shell")
    shell = ShellModule("shell")
    shellcon = ShellConstantsModule("shellcon")
    shell.SHGetFolderPath = lambda *args: str(native_desktop)
    shellcon.CSIDL_DESKTOP = 16
    shell_module.shell = shell
    shell_module.shellcon = shellcon
    package = Win32Module("win32com")
    package.shell = shell_module
    monkeypatch.setitem(sys.modules, "win32com", package)
    monkeypatch.setitem(sys.modules, "win32com.shell", shell_module)

    module = load_desktop(monkeypatch, tmp_path, "win32")

    assert str(native_desktop) == module.DESKTOP_FOLDER


def test_linux_desktop_file_writer_preserves_command_quoting_and_mode(
    tmp_path: Path,
) -> None:
    linux_desktop.create_droplet(
        "Batch Photos",
        'phatch -d "/tmp/action list.phatch" %F',
        folder=str(tmp_path),
        icon="phatch",
    )

    output = tmp_path / "Batch Photos.desktop"
    assert output.read_text(encoding="utf-8") == (
        "#!/usr/bin/env xdg-open\n"
        "[Desktop Entry]\nVersion=1.0\nType=Application\n"
        "Name=Batch Photos\nTerminal=false\n"
        'Exec=phatch -d "/tmp/action list.phatch" %F\nIcon=phatch'
    )
    assert stat.S_IMODE(output.stat().st_mode) == 0o755
    assert os.listdir(tmp_path) == ["Batch Photos.desktop"]
