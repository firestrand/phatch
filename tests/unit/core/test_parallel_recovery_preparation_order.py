from pathlib import Path

import pytest
from PIL import Image

from phatch.core.execution_types import (
    CancellationState,
    ExecutionIssue,
    FileOutcome,
    OutputRecord,
    RecoveryReevaluation,
    ReportFile,
)
from phatch.services import parallel_save
from phatch.services.output_transaction import DeferredOutputTransaction
from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobBatchResult,
    ImageJobSuccess,
)
from phatch.services.parallel_save import execute_parallel_save
from phatch.services.recovery_outcomes import RecoveryFinishSucceeded


class PreparationAttempt:
    def __init__(self, abort_error: OSError | None = None) -> None:
        self.aborts = 0
        self.abort_error = abort_error
        self.transaction = DeferredOutputTransaction()

    def finish(
        self,
        reports: tuple[ReportFile, ...],
        issues: tuple[ExecutionIssue, ...],
    ) -> RecoveryFinishSucceeded:
        del issues
        self.transaction.discard()
        return RecoveryFinishSucceeded(
            tuple(OutputRecord(report) for report in reports)
        )

    def fail(self, issues: tuple[ExecutionIssue, ...]) -> None:
        del issues

    def abort(self) -> None:
        self.aborts += 1
        if self.abort_error is not None:
            raise self.abort_error
        self.transaction.discard()


class PositionFaultRecovery:
    def __init__(
        self,
        jobs: tuple[ImageJob, ...],
        method: str,
        position: int,
        error: OSError | KeyboardInterrupt,
        cached_positions: tuple[int, ...] = (),
        abort_error: OSError | None = None,
    ) -> None:
        self.jobs = jobs
        self.method = method
        self.position = position
        self.error = error
        self.cached_positions = cached_positions
        self.abort_error = abort_error
        self.attempts: dict[int, PreparationAttempt] = {}

    def completed_reports(
        self, source: Path
    ) -> tuple[ReportFile, ...] | RecoveryReevaluation | None:
        position = self._position(source)
        if position in self.cached_positions:
            return (ReportFile(source, self.jobs[position].destination),)
        if self.method == "completed_reports" and position == self.position:
            raise self.error
        return None

    def begin(self, source: Path) -> PreparationAttempt:
        position = self._position(source)
        if self.method == "begin" and position == self.position:
            raise self.error
        attempt = PreparationAttempt(self.abort_error)
        self.attempts[position] = attempt
        return attempt

    def _position(self, source: Path) -> int:
        return next(
            position
            for position, job in enumerate(self.jobs)
            if job.source == source
        )


def three_jobs(tmp_path: Path) -> tuple[ImageJob, ...]:
    jobs = []
    for position, index in enumerate((8, 2, 11)):
        source = tmp_path / f"source-{index}.png"
        Image.new("RGB", (3, 2), "blue").save(source)
        jobs.append(
            ImageJob(
                index,
                source,
                tmp_path / f"output-{position}.png",
                tmp_path / f"stage-{position}.png",
                "PNG",
                6,
            )
        )
    return tuple(jobs)


def successful_workers(
    jobs: tuple[ImageJob, ...], workers: int
) -> ImageJobBatchResult:
    results = []
    for job in jobs:
        Image.new("RGB", (3, 2), "green").save(job.stage)
        results.append(
            ImageJobSuccess(
                job.index,
                job.source,
                job.destination,
                job.stage,
                3,
                2,
                "RGB",
                "PNG",
                1234,
            )
        )
    return ImageJobBatchResult(tuple(results), (1234,), 4321, workers)


@pytest.mark.parametrize("method", ["completed_reports", "begin"])
@pytest.mark.parametrize("position", range(3))
@pytest.mark.parametrize("interrupt", [False, True])
def test_preparation_fault_position_matrix_terminalizes_exact_manifest(
    method: str,
    position: int,
    interrupt: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = three_jobs(tmp_path)
    worker_calls = 0

    def workers(runnable: tuple[ImageJob, ...], count: int) -> ImageJobBatchResult:
        nonlocal worker_calls
        worker_calls += 1
        return successful_workers(runnable, count)

    monkeypatch.setattr(parallel_save, "execute_image_jobs", workers)
    error = KeyboardInterrupt() if interrupt else OSError("preparation io")
    recovery = PositionFaultRecovery(jobs, method, position, error)

    result, _batch = execute_parallel_save(jobs, 2, recovery)

    assert [item.source for item in result.files] == [job.source for job in jobs]
    assert len(result.files) == 3
    if interrupt:
        assert worker_calls == 0
        assert all(
            item.outcome is FileOutcome.CANCELLED for item in result.files
        )
        assert all(attempt.aborts == 1 for attempt in recovery.attempts.values())
    else:
        assert worker_calls == 1
        assert result.files[position].outcome is FileOutcome.FAILED
        assert all(
            item.outcome is FileOutcome.PROCESSED
            for index, item in enumerate(result.files)
            if index != position
        )
    assert not any(job.stage.exists() for job in jobs)


def test_cached_prefix_survives_later_preparation_interrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = three_jobs(tmp_path)
    jobs[0].destination.write_bytes(b"CACHED")
    worker_calls = 0

    def workers(_jobs: tuple[ImageJob, ...], _count: int) -> ImageJobBatchResult:
        nonlocal worker_calls
        worker_calls += 1
        return ImageJobBatchResult((), (), 4321, 2)

    monkeypatch.setattr(parallel_save, "execute_image_jobs", workers)
    recovery = PositionFaultRecovery(
        jobs, "begin", 2, KeyboardInterrupt(), cached_positions=(0,)
    )

    result, _batch = execute_parallel_save(jobs, 2, recovery)

    assert worker_calls == 0
    assert [item.outcome for item in result.files] == [
        FileOutcome.SKIPPED,
        FileOutcome.CANCELLED,
        FileOutcome.CANCELLED,
    ]
    assert recovery.attempts[1].aborts == 1
    assert result.files[0].outputs[0].survived


def test_preparation_interrupt_retains_cancellation_when_abort_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = three_jobs(tmp_path)
    worker_calls = 0

    def workers(_jobs: tuple[ImageJob, ...], _count: int) -> ImageJobBatchResult:
        nonlocal worker_calls
        worker_calls += 1
        return ImageJobBatchResult((), (), 4321, 2)

    monkeypatch.setattr(parallel_save, "execute_image_jobs", workers)
    recovery = PositionFaultRecovery(
        jobs,
        "begin",
        1,
        KeyboardInterrupt(),
        abort_error=OSError("abort cleanup"),
    )

    result, _batch = execute_parallel_save(jobs, 2, recovery)

    assert worker_calls == 0
    assert [item.outcome for item in result.files] == [
        FileOutcome.FAILED,
        FileOutcome.CANCELLED,
        FileOutcome.CANCELLED,
    ]
    assert all(
        item.cancellation is CancellationState.REQUESTED for item in result.files
    )
    assert result.files[0].issues[-1].message == "abort cleanup"
    assert recovery.attempts[0].aborts == 1
