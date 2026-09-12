from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, assert_never

import pytest

from phatch.core.filesystem import atomic_write_bytes

FailureStage = Literal["write", "first-close", "second-close", "fsync", "replace"]


def _inject_primary_failure(
    stage: FailureStage,
    primary: BaseException,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_close = os.close

    def fail_write(_descriptor: int, _data: bytes) -> int:
        raise primary

    def fail_close_after_closing(descriptor: int) -> None:
        real_close(descriptor)
        raise primary

    def fail_cleanup_close_after_closing(descriptor: int) -> None:
        real_close(descriptor)
        raise OSError("secondary cleanup close failure")

    def fail_fsync(_descriptor: int) -> None:
        raise primary

    match stage:
        case "write":
            monkeypatch.setattr(os, "write", fail_write)
        case "first-close":
            monkeypatch.setattr(os, "close", fail_close_after_closing)
        case "second-close":
            monkeypatch.setattr(os, "write", fail_write)
            monkeypatch.setattr(os, "close", fail_cleanup_close_after_closing)
        case "fsync":
            monkeypatch.setattr(os, "fsync", fail_fsync)
        case "replace":
            return
        case unreachable:
            assert_never(unreachable)


@pytest.mark.parametrize(
    "stage", ["write", "first-close", "second-close", "fsync", "replace"]
)
@pytest.mark.parametrize("primary_type", [OSError, KeyboardInterrupt])
def test_primary_failure_survives_injected_path_unlink_failure_without_residue(
    stage: FailureStage,
    primary_type: type[BaseException],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "target.bin"
    destination.write_bytes(b"old")
    primary = primary_type(f"primary {stage} failure")
    _inject_primary_failure(stage, primary, monkeypatch)

    def fail_path_unlink(_path: Path, *, missing_ok: bool = False) -> None:
        raise PermissionError("persistent injected path unlink failure")

    def replace(source: Path, target: Path) -> None:
        if stage == "replace":
            raise primary

    monkeypatch.setattr(Path, "unlink", fail_path_unlink)

    with pytest.raises(primary_type) as raised:
        atomic_write_bytes(destination, b"new", replace)

    assert raised.value is primary
    assert tuple(tmp_path.iterdir()) == (destination,)


def test_os_wide_deletion_denial_preserves_primary_and_can_leave_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "target.bin"
    destination.write_bytes(b"old")
    primary = OSError("primary write failure")
    real_os_unlink = os.unlink

    def fail_write(_descriptor: int, _data: bytes) -> int:
        raise primary

    def deny_path_unlink(_path: Path, *, missing_ok: bool = False) -> None:
        raise PermissionError("path deletion denied")

    def deny_os_unlink(_path: os.PathLike[str] | str, *, dir_fd: int | None = None) -> None:
        raise PermissionError("operating system deletion denied")

    monkeypatch.setattr(os, "write", fail_write)
    monkeypatch.setattr(Path, "unlink", deny_path_unlink)
    monkeypatch.setattr(os, "unlink", deny_os_unlink)

    with pytest.raises(OSError) as raised:
        atomic_write_bytes(destination, b"new")

    assert raised.value is primary
    assert len(tuple(tmp_path.glob(".target.bin.*.tmp"))) == 1

    monkeypatch.setattr(os, "unlink", real_os_unlink)
    for temporary in tmp_path.glob(".target.bin.*.tmp"):
        real_os_unlink(temporary)


def test_os_wide_deletion_denial_raises_cleanup_error_without_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "target.bin"
    destination.write_bytes(b"old")
    real_os_unlink = os.unlink

    def deny_path_unlink(_path: Path, *, missing_ok: bool = False) -> None:
        raise PermissionError("path deletion denied")

    def deny_os_unlink(_path: os.PathLike[str] | str, *, dir_fd: int | None = None) -> None:
        raise PermissionError("operating system deletion denied")

    monkeypatch.setattr(Path, "unlink", deny_path_unlink)
    monkeypatch.setattr(os, "unlink", deny_os_unlink)

    with pytest.raises(PermissionError, match="operating system deletion denied"):
        atomic_write_bytes(destination, b"new", lambda source, target: None)

    assert len(tuple(tmp_path.glob(".target.bin.*.tmp"))) == 1

    monkeypatch.setattr(os, "unlink", real_os_unlink)
    for temporary in tmp_path.glob(".target.bin.*.tmp"):
        real_os_unlink(temporary)
