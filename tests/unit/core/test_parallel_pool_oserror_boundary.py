from collections.abc import Callable
from concurrent.futures import Future
from pathlib import Path
from typing import Never

import pytest
from PIL import Image

from phatch.core.execution_types import FileOutcome, IssueStage
from phatch.services import parallel_image_pool
from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobResult,
    ImageJobSuccess,
)
from phatch.services.parallel_save import execute_parallel_save


class SubmissionExecutor:
    def __init__(self, outcomes: tuple[Future[ImageJobResult] | OSError, ...]) -> None:
        self.outcomes = outcomes
        self.submitted = 0
        self.shutdown_calls: list[tuple[bool, bool]] = []

    def submit(
        self, function: Callable[[ImageJob], ImageJobResult], job: ImageJob
    ) -> Future[ImageJobResult]:
        del function, job
        outcome = self.outcomes[self.submitted]
        self.submitted += 1
        if isinstance(outcome, OSError):
            raise outcome
        return outcome

    def shutdown(self, wait: bool, *, cancel_futures: bool) -> None:
        self.shutdown_calls.append((wait, cancel_futures))


def jobs(tmp_path: Path) -> tuple[ImageJob, ...]:
    prepared = []
    for index in range(2):
        source = tmp_path / f"source-{index}.png"
        Image.new("RGB", (4, 3), "green").save(source)
        prepared.append(
            ImageJob(
                index,
                source,
                tmp_path / f"output-{index}.png",
                tmp_path / f"stage-{index}.png",
                "PNG",
                12,
            )
        )
    return tuple(prepared)


def completed(result: ImageJobResult) -> Future[ImageJobResult]:
    future: Future[ImageJobResult] = Future()
    future.set_result(result)
    return future


def test_public_save_terminalizes_executor_construction_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    planned = jobs(tmp_path)

    def unavailable_executor(_workers: int, _registry: Path) -> Never:
        raise OSError("spawn unavailable")

    monkeypatch.setattr(parallel_image_pool, "_create_executor", unavailable_executor)

    result, batch = execute_parallel_save(planned, 2)

    assert [item.source for item in result.files] == [job.source for job in planned]
    assert [item.outcome for item in result.files] == [
        FileOutcome.FAILED,
        FileOutcome.FAILED,
    ]
    assert all(
        item.issues[0].stage is IssueStage.ACTION_EXECUTION
        and item.issues[0].message
        == "image worker pool terminated: spawn unavailable"
        for item in result.files
    )
    assert len(batch.results) == 2
    assert not any(job.stage.exists() for job in planned)


def test_public_save_terminalizes_first_submission_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    planned = jobs(tmp_path)
    executor = SubmissionExecutor((OSError("submit unavailable"),))
    monkeypatch.setattr(
        parallel_image_pool, "_create_executor", lambda _workers, _registry: executor
    )

    result, _batch = execute_parallel_save(planned, 2)

    assert [item.source for item in result.files] == [job.source for job in planned]
    assert all(item.outcome is FileOutcome.FAILED for item in result.files)
    assert all(
        item.issues[0].message
        == "image worker pool terminated: submit unavailable"
        for item in result.files
    )
    assert executor.shutdown_calls == [(True, True)]
    assert not any(job.stage.exists() for job in planned)


def test_public_save_preserves_completed_result_before_later_submission_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    planned = jobs(tmp_path)
    Image.new("RGB", (4, 3), "blue").save(planned[0].stage)
    success = ImageJobSuccess(
        planned[0].index,
        planned[0].source,
        planned[0].destination,
        planned[0].stage,
        4,
        3,
        "RGB",
        "PNG",
        1234,
    )
    executor = SubmissionExecutor(
        (completed(success), OSError("later submit unavailable"))
    )
    monkeypatch.setattr(
        parallel_image_pool, "_create_executor", lambda _workers, _registry: executor
    )

    result, _batch = execute_parallel_save(planned, 2)

    assert [item.source for item in result.files] == [job.source for job in planned]
    assert [item.outcome for item in result.files] == [
        FileOutcome.PROCESSED,
        FileOutcome.FAILED,
    ]
    assert result.files[1].issues[0].message == (
        "image worker pool terminated: later submit unavailable"
    )
    assert planned[0].destination.is_file()
    assert executor.shutdown_calls == [(True, True)]
    assert not any(job.stage.exists() for job in planned)
