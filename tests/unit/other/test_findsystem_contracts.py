from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

from phatch.other import findsystem


class FakeRegistry(ModuleType):
    def __init__(self) -> None:
        super().__init__("winreg")
        self.HKEY_CURRENT_USER = "current-user"
        self.HKEY_LOCAL_MACHINE = "local-machine"
        self.opened: list[tuple[str, str]] = []
        self.closed: list[str] = []
        self.values: list[tuple[str, str, int]] = []
        self.fail_keys: set[str] = set()

    def OpenKey(self, hive: str, key: str) -> str:
        self.opened.append((hive, key))
        if key in self.fail_keys:
            raise OSError("missing key")
        return key

    def QueryValueEx(self, key: str, name: str) -> tuple[str, int]:
        assert name == "Fonts"
        return "/native/fonts", 1

    def QueryInfoKey(self, key: str) -> tuple[int, int, int]:
        return 0, len(self.values), 0

    def EnumValue(self, key: str, index: int) -> tuple[str, str, int]:
        return self.values[index]

    def CloseKey(self, key: str) -> None:
        self.closed.append(key)


def test_win32_font_directory_uses_registry_and_closes_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = FakeRegistry()
    monkeypatch.setitem(sys.modules, "winreg", registry)

    assert findsystem.win32FontDirectory() == "/native/fonts"
    assert registry.closed == [registry.opened[0][1]]


def test_win32_font_directory_falls_back_without_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "winreg", raising=False)
    monkeypatch.setenv("WINDIR", "/windows")
    real_import = __import__

    def import_without_registry(name: str, *args, **kwargs):
        if name == "winreg":
            raise ImportError("winreg unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", import_without_registry)
    assert findsystem.win32FontDirectory() == "/windows/Fonts"


def test_win32_installed_fonts_normalizes_filters_and_deduplicates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    registry = FakeRegistry()
    registry.fail_keys.add(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
    registry.values = [
        ("Relative", "Alpha.TTF", 1),
        ("Duplicate", "alpha.ttf", 1),
        ("Absolute", str(tmp_path / "Beta.ttf"), 1),
        ("Ignored", "readme.txt", 1),
    ]
    monkeypatch.setitem(sys.modules, "winreg", registry)

    fonts = findsystem.win32InstalledFonts(str(tmp_path))

    assert set(fonts) == {
        os.path.abspath(tmp_path / "Alpha.TTF").lower(),
        os.path.abspath(tmp_path / "Beta.ttf").lower(),
    }
    assert registry.closed == [registry.opened[-1][1]]


def test_win32_installed_fonts_globs_when_registry_keys_are_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    registry = FakeRegistry()
    registry.fail_keys.update(
        {
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Fonts",
        }
    )
    monkeypatch.setitem(sys.modules, "winreg", registry)
    font = tmp_path / "Fallback.ttf"
    font.write_bytes(b"font")

    assert findsystem.win32InstalledFonts(str(tmp_path)) == [str(font)]


def test_win32_installed_fonts_resolves_default_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    registry = FakeRegistry()
    registry.fail_keys.update(
        {
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Fonts",
        }
    )
    monkeypatch.setitem(sys.modules, "winreg", registry)
    monkeypatch.setattr(findsystem, "win32FontDirectory", lambda: str(tmp_path))

    assert findsystem.win32InstalledFonts() == []


def test_linux_font_directories_parse_fake_process_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePipe:
        def readlines(self) -> list[str]:
            return ["1: /fonts/one\n", "invalid\n", "20: /fonts/two\n"]

    monkeypatch.setattr(findsystem.os.path, "isfile", lambda path: True)
    monkeypatch.setattr(findsystem.os, "popen", lambda command: FakePipe())

    assert findsystem.linuxFontDirectories() == ["/fonts/one", "/fonts/two"]


def test_linux_font_directories_walk_existing_fallback_roots(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "fonts"
    nested = root / "nested"
    nested.mkdir(parents=True)
    monkeypatch.setattr(findsystem.os.path, "isfile", lambda path: False)
    monkeypatch.setattr(
        findsystem.os.path,
        "expandvars",
        lambda path: str(root) if path == "/usr/share/fonts" else path,
    )
    monkeypatch.setattr(
        findsystem.os.path,
        "expanduser",
        lambda path: str(root) if path == "/usr/share/fonts" else path,
    )
    real_isdir = os.path.isdir
    monkeypatch.setattr(
        findsystem.os.path, "isdir", lambda path: real_isdir(path) and path == str(root)
    )

    assert findsystem.linuxFontDirectories() == [str(root), str(nested)]


def test_linux_font_directories_ignores_unreadable_fallback_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(findsystem.os.path, "isfile", lambda path: False)
    monkeypatch.setattr(findsystem.os.path, "isdir", lambda path: True)

    def unreadable(path: str):
        raise OSError("permission denied")

    monkeypatch.setattr(findsystem.os, "walk", unreadable)
    assert findsystem.linuxFontDirectories() == []


def test_find_fonts_handles_paths_platform_dispatch_and_deduplication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first = tmp_path / "First.ttf"
    second = tmp_path / "Second.ttf"
    first.write_bytes(b"font")
    second.write_bytes(b"font")
    assert set(findsystem.findFonts(str(tmp_path))) == {str(first), str(second)}

    monkeypatch.setattr(findsystem.sys, "platform", "linux")
    monkeypatch.setattr(findsystem, "linuxFontDirectories", lambda: [str(tmp_path)])
    assert set(findsystem.findFonts()) == {str(first), str(second)}

    monkeypatch.setattr(findsystem.sys, "platform", "win32")
    monkeypatch.setattr(findsystem, "win32FontDirectory", lambda: str(tmp_path))
    monkeypatch.setattr(
        findsystem, "win32InstalledFonts", lambda directory: [str(first)]
    )
    assert set(findsystem.findFonts()) == {str(first), str(second)}
