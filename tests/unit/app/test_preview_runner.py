from __future__ import annotations

import threading
from concurrent.futures import Future
from pathlib import Path

import pytest

from phatch.core.user_paths import HostPlatform
from phatch.pyWx import preview_runner
from phatch.pyWx.preview_runner import PreviewRunner
from phatch.resources.provider import ResourceProvider
from phatch.services.action_schema_types import ActionDocument
from phatch.services.preview_types import (
    PreviewAdmissionError,
    PreviewDependencies,
    PreviewErrorCode,
    PreviewImagePayload,
    PreviewRequest,
    PreviewWorkerCancelled,
    PreviewWorkerSuccess,
)


class FixtureCatalog:
    def action_label(self, action_id: str) -> str | None:
        return action_id

    def field_label(self, action_id: str, field_id: str) -> str | None:
        return field_id

    def invalid_fields(self, spec) -> tuple[str, ...]:
        return ()


class CancellingHandle:
    request_id = "preview-1"

    def cancel(self) -> PreviewWorkerCancelled:
        return PreviewWorkerCancelled(
            self.request_id, PreviewErrorCode.WORKER_CANCELLED, 123
        )

    def poll(self, request_id: str):
        raise AssertionError("cancelled work must not be polled")


def _request(tmp_path: Path) -> PreviewRequest:
    return PreviewRequest(ActionDocument.from_values("", ()), tmp_path / "source.png")


def _dependencies(tmp_path: Path) -> PreviewDependencies:
    resources = tmp_path / "resources"
    resources.mkdir()
    return PreviewDependencies(
        lambda: FixtureCatalog(),
        ResourceProvider.from_root(resources),
        HostPlatform.MACOS,
    )


def test_run_returns_admission_error_without_starting_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    error = PreviewAdmissionError(PreviewErrorCode.BLOCKED_ACTION, "blocked", "geek")

    def reject(request, dependencies):
        raise error

    monkeypatch.setattr(preview_runner, "admit_preview", reject)
    monkeypatch.setattr(
        preview_runner,
        "start_preview",
        lambda specification, request_id: pytest.fail("worker was started"),
    )

    result = PreviewRunner._run(
        _request(tmp_path), _dependencies(tmp_path), 1, threading.Event()
    )

    assert result is error


def test_run_cancels_started_worker_before_poll(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cancel = threading.Event()
    cancel.set()
    monkeypatch.setattr(preview_runner, "admit_preview", lambda request, deps: request)
    monkeypatch.setattr(
        preview_runner,
        "start_preview",
        lambda specification, request_id: CancellingHandle(),
    )

    result = PreviewRunner._run(_request(tmp_path), _dependencies(tmp_path), 1, cancel)

    assert isinstance(result, PreviewWorkerCancelled)


def test_run_cancels_before_starting_worker_after_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cancel = threading.Event()
    cancel.set()
    monkeypatch.setattr(preview_runner, "admit_preview", lambda request, deps: request)
    monkeypatch.setattr(
        preview_runner,
        "start_preview",
        lambda specification, request_id: pytest.fail("worker was started"),
    )

    result = PreviewRunner._run(_request(tmp_path), _dependencies(tmp_path), 3, cancel)

    assert result == PreviewWorkerCancelled(
        "preview-3", PreviewErrorCode.WORKER_CANCELLED, 0
    )


def test_cancel_and_close_suppress_stale_scheduled_completion() -> None:
    scheduled = []
    runner = PreviewRunner(lambda callback, *args: scheduled.append((callback, args)))
    future = Future()
    future.set_result(PreviewAdmissionError(PreviewErrorCode.BLOCKED_ACTION, "blocked"))
    assert runner.generation == 0

    runner.cancel()
    runner._schedule(future, 0, lambda generation, result: None)
    runner.close()
    runner._schedule(future, runner.generation, lambda generation, result: None)

    assert scheduled == []


def test_cancelled_future_is_not_scheduled() -> None:
    scheduled = []
    runner = PreviewRunner(lambda callback, *args: scheduled.append((callback, args)))
    future = Future()
    future.cancel()

    runner._schedule(future, runner.generation, lambda generation, result: None)

    assert scheduled == []
    runner.close()


def test_cancel_schedules_joined_cancellation_for_owning_generation() -> None:
    scheduled = []
    delivered = []
    runner = PreviewRunner(lambda callback, *args: scheduled.append((callback, args)))
    runner._generation = 1
    runner._active_generation = 1
    future = Future()
    cancelled = PreviewWorkerCancelled(
        "preview-1", PreviewErrorCode.WORKER_CANCELLED, 123
    )
    future.set_result(cancelled)

    runner.cancel()
    runner._schedule(
        future, 1, lambda generation, result: delivered.append((generation, result))
    )
    callback, args = scheduled[0]
    callback(*args)

    assert len(scheduled) == 1
    assert delivered == [(1, cancelled)]
    runner.close()


def test_cancel_converts_queued_success_to_cancellation() -> None:
    scheduled = []
    delivered = []
    runner = PreviewRunner(lambda callback, *args: scheduled.append((callback, args)))
    runner._generation = 1
    runner._active_generation = 1
    future = Future()
    future.set_result(
        PreviewWorkerSuccess(
            "preview-1",
            PreviewImagePayload(b"image", 1, 1, "RGB", "PNG"),
            123,
        )
    )

    runner._schedule(
        future, 1, lambda generation, result: delivered.append((generation, result))
    )
    runner.cancel()
    callback, args = scheduled[0]
    callback(*args)

    assert len(scheduled) == 1
    assert delivered == [
        (
            1,
            PreviewWorkerCancelled("preview-1", PreviewErrorCode.WORKER_CANCELLED, 123),
        )
    ]
    runner.close()


def test_close_discards_completion_already_queued_for_main_thread() -> None:
    scheduled = []
    delivered = []
    runner = PreviewRunner(lambda callback, *args: scheduled.append((callback, args)))
    runner._generation = 1
    runner._active_generation = 1
    future = Future()
    future.set_result(PreviewAdmissionError(PreviewErrorCode.BLOCKED_ACTION, "blocked"))

    runner._schedule(
        future, 1, lambda generation, result: delivered.append((generation, result))
    )
    runner.close()
    callback, args = scheduled[0]
    callback(*args)

    assert delivered == []


def test_stale_non_cancelled_generation_is_not_delivered() -> None:
    delivered = []
    runner = PreviewRunner(lambda callback, *args: callback(*args))
    runner._generation = 2

    runner._deliver(
        lambda generation, result: delivered.append((generation, result)),
        1,
        PreviewAdmissionError(PreviewErrorCode.BLOCKED_ACTION, "blocked"),
    )

    assert delivered == []
    runner.close()


def test_cancelled_admission_error_is_delivered_as_cancellation() -> None:
    delivered = []
    runner = PreviewRunner(lambda callback, *args: callback(*args))
    runner._generation = 2
    runner._cancelled_generations.add(1)

    runner._deliver(
        lambda generation, result: delivered.append((generation, result)),
        1,
        PreviewAdmissionError(PreviewErrorCode.BLOCKED_ACTION, "blocked"),
    )

    assert delivered == [
        (1, PreviewWorkerCancelled("preview-1", PreviewErrorCode.WORKER_CANCELLED, 0))
    ]
    runner.close()
