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
    PreviewDependencies,
    PreviewErrorCode,
    PreviewRequest,
    PreviewWorkerFailure,
)


class FixtureCatalog:
    def action_label(self, action_id: str) -> str | None:
        return action_id

    def field_label(self, action_id: str, field_id: str) -> str | None:
        return field_id

    def invalid_fields(self, spec) -> tuple[str, ...]:
        return ()


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


def test_start_oserror_becomes_terminal_worker_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(preview_runner, "admit_preview", lambda request, deps: request)

    def fail_start(specification, request_id):
        raise OSError("private startup detail")

    monkeypatch.setattr(preview_runner, "start_preview", fail_start)

    result = PreviewRunner._run(
        _request(tmp_path), _dependencies(tmp_path), 4, threading.Event()
    )

    assert result == PreviewWorkerFailure(
        "preview-4",
        PreviewErrorCode.WORKER_FAILED,
        "The preview worker could not be started.",
        0,
    )


def test_failed_future_schedules_bounded_terminal_failure() -> None:
    scheduled = []
    delivered = []
    runner = PreviewRunner(lambda callback, *args: scheduled.append((callback, args)))
    runner._generation = 5
    runner._active_generation = 5
    future = Future()
    future.set_exception(RuntimeError("/Volumes/private-client/input.png"))

    runner._schedule(
        future,
        5,
        lambda generation, result: delivered.append((generation, result)),
    )
    callback, args = scheduled[0]
    callback(*args)

    assert delivered == [
        (
            5,
            PreviewWorkerFailure(
                "preview-5",
                PreviewErrorCode.WORKER_FAILED,
                "The preview worker failed unexpectedly.",
                0,
            ),
        )
    ]
    runner.close()


def test_interrupting_future_propagates_interrupt() -> None:
    runner = PreviewRunner(lambda callback, *args: callback(*args))
    future = Future()
    future.set_exception(KeyboardInterrupt())

    with pytest.raises(KeyboardInterrupt):
        runner._schedule(future, 1, lambda generation, result: None)

    runner.close()
