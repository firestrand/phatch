from __future__ import annotations

import os
import signal
import time
from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image

from phatch.services import preview_process
from phatch.services.preview import run_preview, start_preview
from phatch.services.preview_types import (
    PreviewErrorCode,
    PreviewExecutionSpec,
    PreviewImagePayload,
    PreviewLimits,
    PreviewReadContext,
    PreviewSize,
    PreviewSource,
    PreviewWorkerFailure,
    PreviewWorkerSuccess,
)


def _spec(
    path: Path, *, max_live_bytes: int = 64 * 1024 * 1024
) -> PreviewExecutionSpec:
    source = PreviewSource(
        path,
        sha256(path.read_bytes()).hexdigest(),
        PreviewSize(8, 6),
        "RGB",
        "PNG",
    )
    return PreviewExecutionSpec(
        (),
        source,
        (),
        (
            "dpi",
            "filename",
            "format",
            "height",
            "orientation",
            "path",
            "size",
            "type",
            "width",
        ),
        PreviewLimits(max_live_bytes=max_live_bytes),
        PreviewReadContext(source, ()),
        False,
    )


def _source(path: Path) -> None:
    with Image.new("RGB", (8, 6), "navy") as image:
        image.save(path)


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _ignore_terminate(request, connection) -> None:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    connection.send_bytes(b"ready")
    while True:
        time.sleep(1)


def _oversized_result(request, connection) -> None:
    payload = PreviewImagePayload(b"x" * 2048, 1, 1, "RGB", "PNG")
    connection.send(PreviewWorkerSuccess(request.request_id, payload, os.getpid()))
    connection.close()


def _corrupt_result(request, connection) -> None:
    connection.send_bytes(b"not-a-pickle")
    connection.close()


def _wrong_request_result(request, connection) -> None:
    payload = PreviewImagePayload(b"png", 1, 1, "RGB", "PNG")
    connection.send(PreviewWorkerSuccess("another-request", payload, os.getpid()))
    connection.close()


def _invalid_image_result(request, connection) -> None:
    payload = PreviewImagePayload(b"not-an-image", 1, 1, "RGB", "PNG")
    connection.send(PreviewWorkerSuccess(request.request_id, payload, os.getpid()))
    connection.close()


def _unknown_result(request, connection) -> None:
    connection.send({"request_id": request.request_id})
    connection.close()


@pytest.mark.skipif(os.name == "nt", reason="SIGTERM ignore probe is POSIX-only")
def test_cancel_force_kills_terminate_resistant_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.png"
    _source(source)
    monkeypatch.setattr(preview_process, "_worker_entry", _ignore_terminate)
    monkeypatch.setattr(preview_process, "_TERMINATE_GRACE_SECONDS", 0.05)
    handle = start_preview(_spec(source), "force-kill")
    pid = handle.worker_pid
    time.sleep(0.1)

    result = handle.cancel()

    assert result.code is PreviewErrorCode.WORKER_CANCELLED
    assert not _pid_exists(pid)


@pytest.mark.parametrize(
    ("worker", "expected"),
    [
        (_oversized_result, PreviewErrorCode.MEMORY_LIMIT),
        (_corrupt_result, PreviewErrorCode.WORKER_FAILED),
        (_wrong_request_result, PreviewErrorCode.STALE_REQUEST),
        (_invalid_image_result, PreviewErrorCode.WORKER_FAILED),
        (_unknown_result, PreviewErrorCode.WORKER_FAILED),
    ],
)
def test_invalid_transfers_return_no_image_and_reap_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    worker,
    expected: PreviewErrorCode,
) -> None:
    source = tmp_path / "source.png"
    _source(source)
    monkeypatch.setattr(preview_process, "_worker_entry", worker)

    result = run_preview(_spec(source, max_live_bytes=1024), "transfer")

    assert isinstance(result, PreviewWorkerFailure)
    assert result.code is expected
    assert not _pid_exists(result.worker_pid)


def test_finished_handle_poll_is_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _source(source)
    handle = start_preview(_spec(source), "finished")
    result = None
    while result is None:
        result = handle.poll("finished")

    assert isinstance(result, PreviewWorkerSuccess)
    assert handle.poll("finished") is None
    assert not _pid_exists(result.worker_pid)
