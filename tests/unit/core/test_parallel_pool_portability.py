from collections.abc import Callable
from concurrent.futures import Future
from pathlib import Path
from typing import Any, cast

import pytest

from phatch.services import parallel_image_pool
from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobResult,
    execute_image_jobs,
)


class _ProcessProbe:
    pid = 4321

    def __init__(self) -> None:
        self.alive = True
        self.calls: list[str] = []

    def is_alive(self) -> bool:
        return self.alive

    def terminate(self) -> None:
        self.calls.append("terminate")

    def join(self, timeout: float | None = None) -> None:
        self.calls.append(f"join:{timeout}")
        self.alive = False

    def kill(self) -> None:
        self.calls.append("kill")


class _InterruptingExecutor:
    def __init__(self) -> None:
        self.shutdown_calls: list[tuple[bool, bool]] = []

    def submit(
        self, function: Callable[[ImageJob], ImageJobResult], job: ImageJob
    ) -> Future[ImageJobResult]:
        raise KeyboardInterrupt

    def shutdown(self, wait: bool, *, cancel_futures: bool) -> None:
        self.shutdown_calls.append((wait, cancel_futures))


class _RuntimeErrorExecutor(_InterruptingExecutor):
    def submit(
        self, function: Callable[[ImageJob], ImageJobResult], job: ImageJob
    ) -> Future[ImageJobResult]:
        raise _SubmissionFailure("submission failed")


class _SubmissionFailure(RuntimeError):
    pass


class _StubbornProcess(_ProcessProbe):
    def join(self, timeout: float | None = None) -> None:
        self.calls.append(f"join:{timeout}")

    def kill(self) -> None:
        super().kill()
        self.alive = False


def _job(tmp_path: Path, index: int) -> ImageJob:
    return ImageJob(
        index,
        tmp_path / f"source-{index}.png",
        tmp_path / f"output-{index}.png",
        tmp_path / f"stage-{index}.png",
        "PNG",
        1,
    )


def test_submission_interrupt_shuts_down_and_terminates_owned_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    executor = _InterruptingExecutor()
    process = _ProcessProbe()
    monkeypatch.setattr(
        parallel_image_pool, "_create_executor", lambda _workers, _registry: executor
    )
    monkeypatch.setattr(
        parallel_image_pool.multiprocessing,
        "active_children",
        iter(([], [process])).__next__,
    )

    # When / Then
    with pytest.raises(KeyboardInterrupt):
        execute_image_jobs((_job(tmp_path, 0), _job(tmp_path, 1)), 2)
    assert executor.shutdown_calls == [(False, True)]
    assert process.calls == ["terminate", "join:1.0"]


def test_submission_runtime_error_cancels_and_shuts_down_pool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    executor = _RuntimeErrorExecutor()
    monkeypatch.setattr(
        parallel_image_pool, "_create_executor", lambda _workers, _registry: executor
    )

    # When
    result = execute_image_jobs((_job(tmp_path, 0), _job(tmp_path, 1)), 2)

    # Then
    assert all(
        isinstance(item, parallel_image_pool.ImageJobFailure)
        and item.reason.endswith("submission failed")
        for item in result.results
    )
    assert executor.shutdown_calls == [(True, True)]


def test_terminate_workers_skips_dead_process_and_escalates_stubborn_process() -> None:
    dead = _ProcessProbe()
    dead.alive = False
    stubborn = _StubbornProcess()

    parallel_image_pool._terminate_workers(cast(Any, (dead, stubborn)))

    assert dead.calls == ["join:1.0"]
    assert stubborn.calls == [
        "terminate",
        "join:1.0",
        "kill",
        "join:1.0",
    ]


def test_new_worker_processes_excludes_preexisting_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = _ProcessProbe()
    new = _ProcessProbe()
    new.pid = 5678
    monkeypatch.setattr(
        parallel_image_pool.multiprocessing,
        "active_children",
        lambda: cast(Any, [existing, new]),
    )

    assert parallel_image_pool._new_worker_processes(frozenset({existing.pid})) == (
        new,
    )
