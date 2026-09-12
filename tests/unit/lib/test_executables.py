from __future__ import annotations

import os
from pathlib import Path

from phatch.lib.executables import ExecutableLookup


def make_executable(path: Path) -> Path:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_lookup_prefers_injected_directories_and_returns_raw_absolute_path(
    tmp_path: Path,
) -> None:
    configured = tmp_path / "program files & tools"
    path_dir = tmp_path / "path"
    configured.mkdir()
    path_dir.mkdir()
    preferred = make_executable(configured / "render;tool")
    make_executable(path_dir / "render;tool")
    lookup = ExecutableLookup(
        search_directories=(configured,), path=os.fspath(path_dir)
    )

    assert lookup.find("render;tool") == preferred.resolve()


def test_lookup_does_not_cache_absence_or_stale_success(tmp_path: Path) -> None:
    lookup = ExecutableLookup(path=os.fspath(tmp_path))
    executable = tmp_path / "changing-tool"

    assert lookup.find("changing-tool") is None
    make_executable(executable)
    assert lookup.find("changing-tool") == executable.resolve()
    executable.unlink()
    assert lookup.find("changing-tool") is None


def test_lookup_does_not_search_cwd_for_missing_or_empty_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    make_executable(tmp_path / "local-tool")
    monkeypatch.chdir(tmp_path)

    assert ExecutableLookup(path=None).find("local-tool") is None
    assert ExecutableLookup(path="").find("local-tool") is None
    assert ExecutableLookup(path=os.fspath(tmp_path)).find("") is None
    assert ExecutableLookup(path=os.fspath(tmp_path)).find("bad\0name") is None


def test_lookup_validates_explicit_paths(tmp_path: Path) -> None:
    executable = make_executable(tmp_path / "tool")

    assert ExecutableLookup().find(os.fspath(executable)) == executable.resolve()
    executable.chmod(0o644)
    assert ExecutableLookup().find(os.fspath(executable)) is None


def test_windows_lookup_uses_registry_fallback_and_rejects_batch_files(
    tmp_path: Path,
) -> None:
    native = make_executable(tmp_path / "native.exe")
    batch = make_executable(tmp_path / "unsafe.cmd")

    assert (
        ExecutableLookup(
            registry_lookup=lambda name: native,
            platform="win32",
        ).find("native")
        == native.resolve()
    )
    assert (
        ExecutableLookup(path=os.fspath(tmp_path), platform="win32").find(batch.name)
        is None
    )
    assert (
        ExecutableLookup(
            registry_lookup=lambda name: batch,
            platform="win32",
        ).find("unsafe")
        is None
    )


def test_registry_fallback_rejects_a_non_executable_file(tmp_path: Path) -> None:
    file_path = tmp_path / "not-executable.exe"
    file_path.write_text("data", encoding="utf-8")

    assert (
        ExecutableLookup(
            registry_lookup=lambda name: file_path,
            platform="win32",
        ).find("tool")
        is None
    )
