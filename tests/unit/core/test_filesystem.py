from __future__ import annotations

import os
from pathlib import Path

import pytest

from phatch.core.filesystem import atomic_write_bytes, ensure_directory


def test_ensure_directory_accepts_pathlike_and_is_idempotent(tmp_path: Path) -> None:
    destination = tmp_path / "one/two"
    assert ensure_directory(destination) == destination
    assert ensure_directory(os.fspath(destination)) == destination
    assert destination.is_dir()


def test_atomic_write_replaces_destination_and_leaves_no_temp(tmp_path: Path) -> None:
    destination = tmp_path / "settings.json"
    destination.write_bytes(b"old")

    atomic_write_bytes(destination, b"new")

    assert destination.read_bytes() == b"new"
    assert tuple(tmp_path.iterdir()) == (destination,)


def test_replace_failure_preserves_destination_and_cleans_temp(tmp_path: Path) -> None:
    destination = tmp_path / "settings.json"
    destination.write_bytes(b"old")

    def fail_replace(source: Path, target: Path) -> None:
        raise PermissionError(source, target)

    with pytest.raises(PermissionError):
        atomic_write_bytes(destination, b"new", fail_replace)

    assert destination.read_bytes() == b"old"
    assert tuple(tmp_path.iterdir()) == (destination,)


def test_write_interruption_preserves_destination_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "settings.json"
    destination.write_bytes(b"old")

    def interrupt(_file_descriptor: int, _data: bytes) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "write", interrupt)
    with pytest.raises(KeyboardInterrupt):
        atomic_write_bytes(destination, b"new")

    assert destination.read_bytes() == b"old"
    assert tuple(tmp_path.iterdir()) == (destination,)


def test_zero_progress_write_preserves_destination_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "settings.json"
    destination.write_bytes(b"old")
    monkeypatch.setattr(os, "write", lambda descriptor, data: 0)

    with pytest.raises(OSError, match="made no progress"):
        atomic_write_bytes(destination, b"new")

    assert destination.read_bytes() == b"old"
    assert tuple(tmp_path.iterdir()) == (destination,)


def test_fsync_failure_preserves_destination_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "settings.json"
    destination.write_bytes(b"old")

    def fail_fsync(_file_descriptor: int) -> None:
        raise OSError("injected fsync failure")

    monkeypatch.setattr(os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="injected fsync failure"):
        atomic_write_bytes(destination, b"new")

    assert destination.read_bytes() == b"old"
    assert tuple(tmp_path.iterdir()) == (destination,)


def test_replace_interruption_preserves_destination_and_cleans_temp(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "settings.json"
    destination.write_bytes(b"old")

    def interrupt_replace(_source: Path, _target: Path) -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        atomic_write_bytes(destination, b"new", interrupt_replace)

    assert destination.read_bytes() == b"old"
    assert tuple(tmp_path.iterdir()) == (destination,)


def test_primary_close_failure_still_unlinks_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "settings.json"
    destination.write_bytes(b"old")
    real_close = os.close
    descriptors: list[int] = []

    def fail_close(descriptor: int) -> None:
        descriptors.append(descriptor)
        raise OSError("injected close failure")

    monkeypatch.setattr(os, "close", fail_close)
    with pytest.raises(OSError, match="injected close failure"):
        atomic_write_bytes(destination, b"new")
    monkeypatch.setattr(os, "close", real_close)
    real_close(descriptors[0])

    assert destination.read_bytes() == b"old"
    assert tuple(tmp_path.iterdir()) == (destination,)


def test_cleanup_close_failure_does_not_replace_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "settings.json"
    destination.write_bytes(b"old")
    real_close = os.close
    descriptors: list[int] = []

    def fail_write(descriptor: int, data: bytes) -> int:
        raise PermissionError("primary write failure")

    def fail_close(descriptor: int) -> None:
        descriptors.append(descriptor)
        raise OSError("cleanup close failure")

    monkeypatch.setattr(os, "write", fail_write)
    monkeypatch.setattr(os, "close", fail_close)
    with pytest.raises(PermissionError, match="primary write failure"):
        atomic_write_bytes(destination, b"new")
    monkeypatch.setattr(os, "close", real_close)
    real_close(descriptors[0])

    assert destination.read_bytes() == b"old"
    assert tuple(tmp_path.iterdir()) == (destination,)


def test_path_unlink_failure_uses_os_fallback(tmp_path: Path, monkeypatch) -> None:
    destination = tmp_path / "settings.json"
    destination.write_bytes(b"old")
    real_unlink = Path.unlink
    unlink_calls = 0

    def fail_once(path: Path, *, missing_ok: bool = False) -> None:
        nonlocal unlink_calls
        unlink_calls += 1
        if unlink_calls == 1:
            raise PermissionError("transient unlink failure")
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_once)

    atomic_write_bytes(destination, b"new", lambda source, target: None)

    assert unlink_calls == 1
    assert destination.read_bytes() == b"old"
    assert tuple(tmp_path.iterdir()) == (destination,)


def test_write_error_survives_close_and_path_unlink_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "settings.json"
    destination.write_bytes(b"old")
    real_close = os.close
    real_unlink = Path.unlink
    descriptors: list[int] = []
    unlink_calls = 0

    def fail_write(descriptor: int, data: bytes) -> int:
        raise KeyboardInterrupt("primary interrupt")

    def fail_close(descriptor: int) -> None:
        descriptors.append(descriptor)
        raise OSError("cleanup close failure")

    def fail_unlink_once(path: Path, *, missing_ok: bool = False) -> None:
        nonlocal unlink_calls
        unlink_calls += 1
        if unlink_calls == 1:
            raise PermissionError("cleanup unlink failure")
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(os, "write", fail_write)
    monkeypatch.setattr(os, "close", fail_close)
    monkeypatch.setattr(Path, "unlink", fail_unlink_once)
    with pytest.raises(KeyboardInterrupt, match="primary interrupt"):
        atomic_write_bytes(destination, b"new")
    monkeypatch.setattr(os, "close", real_close)
    real_close(descriptors[0])

    assert unlink_calls == 1
    assert destination.read_bytes() == b"old"
    assert tuple(tmp_path.iterdir()) == (destination,)
