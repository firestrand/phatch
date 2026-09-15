from __future__ import annotations

import io
import os
import time
from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image, ImageOps

from phatch.services import preview_process, preview_worker
from phatch.services.preview import run_preview, start_preview
from phatch.services.preview_types import (
    PreviewActionSpec,
    PreviewErrorCode,
    PreviewExecutionSpec,
    PreviewImagePayload,
    PreviewLimits,
    PreviewReadContext,
    PreviewSize,
    PreviewSource,
    PreviewWorkerCancelled,
    PreviewWorkerFailure,
    PreviewWorkerRequest,
    PreviewWorkerSuccess,
)
from phatch.services.preview_worker import _execute, execute_preview_worker


def _spec(source: Path, actions: tuple[PreviewActionSpec, ...]) -> PreviewExecutionSpec:
    with Image.open(source) as image:
        size = PreviewSize(*image.size)
        mode = image.mode
        format_name = image.format
    identity = PreviewSource(
        source.resolve(),
        sha256(source.read_bytes()).hexdigest(),
        size,
        mode,
        format_name,
    )
    return PreviewExecutionSpec(
        actions,
        identity,
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
        PreviewLimits(),
        PreviewReadContext(identity, ()),
        False,
    )


def _spawn_source(path: Path) -> None:
    with Image.new("RGB", (31, 23)) as image:
        for y in range(image.height):
            for x in range(image.width):
                image.putpixel((x, y), ((x * 17) % 256, (y * 29) % 256, (x + y) % 256))
        image.save(path)


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _hang_worker(request, connection) -> None:
    time.sleep(30)


def _crash_worker(request, connection) -> None:
    os._exit(17)


def _result_then_hang_worker(request, connection) -> None:
    payload = PreviewImagePayload(b"png", 1, 1, "RGB", "PNG")
    connection.send(PreviewWorkerSuccess(request.request_id, payload, os.getpid()))
    connection.close()
    time.sleep(30)


def _large_result_worker(request, connection) -> None:
    image = Image.effect_noise((512, 512), 100).convert("RGB")
    output = io.BytesIO()
    image.save(output, format="PNG")
    image.close()
    data = output.getvalue()
    payload = PreviewImagePayload(data, 512, 512, "RGB", "PNG")
    connection.send(PreviewWorkerSuccess(request.request_id, payload, os.getpid()))
    connection.close()


class CapturingConnection:
    def __init__(self) -> None:
        self.result = None
        self.closed = False

    def send(self, result) -> None:
        self.result = result

    def close(self) -> None:
        self.closed = True


def test_spawned_crop_matches_production_pixels_and_uses_new_pid(
    tmp_path: Path,
) -> None:
    # Given
    source = tmp_path / "source.png"
    _spawn_source(source)
    spec = _spec(
        source,
        (PreviewActionSpec("crop", (("mode", "All"), ("all", "7px"))),),
    )

    # When
    result = run_preview(spec, "crop-parity")

    # Then
    assert isinstance(result, PreviewWorkerSuccess)
    assert result.worker_pid != os.getpid()
    with (
        Image.open(io.BytesIO(result.image.data)) as actual,
        Image.open(source) as original,
    ):
        expected = ImageOps.crop(original, 7)
        assert actual.size == expected.size
        assert actual.tobytes() == expected.tobytes()


def test_worker_execution_path_directly_uses_production_action(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _spawn_source(source)
    spec = _spec(
        source,
        (PreviewActionSpec("crop", (("mode", "All"), ("all", "7px"))),),
    )

    result = _execute(PreviewWorkerRequest("direct", spec, ()))

    assert result.image.width == 17
    assert result.image.height == 9


def test_worker_entry_sends_success_and_closes_connection(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _spawn_source(source)
    request = PreviewWorkerRequest("direct-entry", _spec(source, ()), ())
    connection = CapturingConnection()

    execute_preview_worker(request, connection)

    assert isinstance(connection.result, PreviewWorkerSuccess)
    assert connection.closed


def test_worker_entry_maps_admission_and_unexpected_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.png"
    _spawn_source(source)
    spec = _spec(source, ())
    source.write_bytes(b"changed")
    connection = CapturingConnection()

    execute_preview_worker(
        PreviewWorkerRequest("admission", spec, ()),
        connection,
    )

    assert isinstance(connection.result, PreviewWorkerFailure)
    assert connection.result.code is PreviewErrorCode.SOURCE_CHANGED

    def fail_unexpected(request):
        raise RuntimeError("boom")

    monkeypatch.setattr("phatch.services.preview_worker._execute", fail_unexpected)
    connection = CapturingConnection()
    execute_preview_worker(
        PreviewWorkerRequest("unexpected", spec, ()),
        connection,
    )
    assert isinstance(connection.result, PreviewWorkerFailure)
    assert connection.result.code is PreviewErrorCode.WORKER_FAILED


def test_recipe_reuses_production_settings_and_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.png"
    _spawn_source(source)
    observed: list[tuple[object, object]] = []

    class RecordingAction:
        def apply(self, photo, settings, cache):
            observed.append((settings, cache))
            return photo

    monkeypatch.setattr(
        preview_worker,
        "construct_preview_actions",
        lambda specs, fields: (RecordingAction(), RecordingAction()),
    )
    spec = _spec(
        source,
        (PreviewActionSpec("contrast", ()), PreviewActionSpec("brightness", ())),
    )

    _execute(PreviewWorkerRequest("shared-state", spec, ()))

    assert observed[0][0] is observed[1][0]
    assert observed[0][1] is observed[1][1]


@pytest.mark.parametrize(
    ("worker", "expected_code"),
    [
        (_hang_worker, PreviewErrorCode.WORKER_TIMEOUT),
        (_crash_worker, PreviewErrorCode.WORKER_FAILED),
        (_result_then_hang_worker, PreviewErrorCode.WORKER_TIMEOUT),
    ],
)
def test_worker_failure_paths_return_no_partial_image_and_reap_pid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    worker,
    expected_code: PreviewErrorCode,
) -> None:
    # Given
    source = tmp_path / "source.png"
    _spawn_source(source)
    monkeypatch.setattr(preview_process, "_worker_entry", worker)
    monkeypatch.setattr(preview_process, "_DEADLINE_SECONDS", 0.5)

    # When
    result = run_preview(_spec(source, ()), "failure")

    # Then
    assert isinstance(result, PreviewWorkerFailure)
    assert result.code is expected_code
    assert not _pid_exists(result.worker_pid)


def test_cancel_and_stale_request_reap_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    source = tmp_path / "source.png"
    _spawn_source(source)
    monkeypatch.setattr(preview_process, "_worker_entry", _hang_worker)
    handle = start_preview(_spec(source, ()), "current")
    pid = handle.worker_pid

    # When
    cancelled = handle.cancel()

    # Then
    assert isinstance(cancelled, PreviewWorkerCancelled)
    assert cancelled.code is PreviewErrorCode.WORKER_CANCELLED
    assert not _pid_exists(pid)

    stale = start_preview(_spec(source, ()), "old")
    stale_pid = stale.worker_pid
    stale_result = stale.poll("new")
    assert isinstance(stale_result, PreviewWorkerCancelled)
    assert stale_result.code is PreviewErrorCode.STALE_REQUEST
    assert not _pid_exists(stale_pid)


def test_worker_rechecks_source_fingerprint(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "source.png"
    _spawn_source(source)
    spec = _spec(source, ())
    source.write_bytes(b"changed after admission")

    # When
    result = run_preview(spec, "changed")

    # Then
    assert isinstance(result, PreviewWorkerFailure)
    assert result.code is PreviewErrorCode.SOURCE_CHANGED
    assert not _pid_exists(result.worker_pid)
