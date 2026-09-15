from pathlib import Path

import pytest
from PIL import Image

from phatch.core.execution_types import (
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
    ImageJobFailure,
    ImageJobSuccess,
)
from phatch.services.parallel_save import execute_parallel_save
from phatch.services.recovery_outcomes import RecoveryFinishSucceeded


class FaultAttempt:
    def __init__(self, method: str, error: OSError | KeyboardInterrupt) -> None:
        self.method = method
        self.error = error
        self.transaction = DeferredOutputTransaction()

    def finish(self, reports, issues):
        del issues
        if self.method == "finish":
            raise self.error
        return RecoveryFinishSucceeded(
            tuple(OutputRecord(report) for report in reports)
        )

    def fail(self, issues: tuple[ExecutionIssue, ...]) -> None:
        del issues
        if self.method == "fail":
            raise self.error

    def abort(self) -> None:
        if self.method == "abort":
            raise self.error


class FaultRecovery:
    def __init__(self, method: str, error: OSError | KeyboardInterrupt) -> None:
        self.method = method
        self.error = error
        self.attempts: list[FaultAttempt] = []

    def completed_reports(
        self, source: Path
    ) -> tuple[ReportFile, ...] | RecoveryReevaluation | None:
        del source
        if self.method == "completed_reports":
            raise self.error
        return None

    def begin(self, source: Path) -> FaultAttempt:
        del source
        if self.method == "begin":
            raise self.error
        attempt = FaultAttempt(self.method, self.error)
        self.attempts.append(attempt)
        return attempt


class WarmRecovery(FaultRecovery):
    def __init__(self, source: Path, output: Path) -> None:
        super().__init__("none", OSError())
        self.source = source
        self.output = output

    def completed_reports(
        self, source: Path
    ) -> tuple[ReportFile, ...] | RecoveryReevaluation | None:
        if source == self.source:
            return (ReportFile(source, self.output),)
        return None


def _jobs(tmp_path: Path) -> tuple[ImageJob, ...]:
    jobs = []
    for index, name in enumerate(("first", "second")):
        source = tmp_path / f"{name}.png"
        color = "red" if name == "first" else "blue"
        Image.new("RGB", (4, 3), color).save(source)
        jobs.append(
            ImageJob(
                index,
                source,
                tmp_path / f"{name}-output.png",
                tmp_path / f".{name}.stage.png",
                "PNG",
                12,
            )
        )
    return tuple(jobs)


def _worker_success(jobs: tuple[ImageJob, ...], _workers: int) -> ImageJobBatchResult:
    results = []
    for job in jobs:
        Image.new("RGB", (4, 3), "green").save(job.stage)
        results.append(
            ImageJobSuccess(
                job.index,
                job.source,
                job.destination,
                job.stage,
                4,
                3,
                "RGB",
                "PNG",
                1234,
            )
        )
    return ImageJobBatchResult(tuple(results), (1234,), 4321, 2)


@pytest.mark.parametrize("method", ["completed_reports", "begin", "finish"])
@pytest.mark.parametrize("error", [OSError("recovery io"), KeyboardInterrupt()])
def test_parallel_recovery_boundary_terminalizes_every_source(
    method: str,
    error: OSError | KeyboardInterrupt,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path)
    monkeypatch.setattr(parallel_save, "execute_image_jobs", _worker_success)

    result, _batch = execute_parallel_save(jobs, 2, FaultRecovery(method, error))

    assert [item.source for item in result.files] == [job.source for job in jobs]
    assert len(result.files) == len(jobs)
    assert not any(job.stage.exists() for job in jobs)


@pytest.mark.parametrize("error", [OSError("fail io"), KeyboardInterrupt()])
def test_parallel_fail_boundary_preserves_worker_failure(
    error: OSError | KeyboardInterrupt,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path)
    batch = ImageJobBatchResult(
        tuple(
            ImageJobFailure(
                job.index,
                job.source,
                job.destination,
                job.stage,
                "worker failed",
                1234,
            )
            for job in jobs
        ),
        (1234,),
        4321,
        2,
    )
    monkeypatch.setattr(parallel_save, "execute_image_jobs", lambda *_args: batch)

    result, _batch = execute_parallel_save(jobs, 2, FaultRecovery("fail", error))

    assert len(result.files) == len(jobs)
    assert result.files[0].outcome is FileOutcome.FAILED
    assert result.files[0].issues[0].message == "worker failed"
    assert result.files[1].outcome is (
        FileOutcome.CANCELLED
        if isinstance(error, KeyboardInterrupt)
        else FileOutcome.FAILED
    )


@pytest.mark.parametrize("error", [OSError("abort io"), KeyboardInterrupt()])
def test_parallel_abort_boundary_cannot_override_worker_interrupt(
    error: OSError | KeyboardInterrupt,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path)
    for job in jobs:
        job.stage.write_bytes(b"partial")
    monkeypatch.setattr(
        parallel_save,
        "execute_image_jobs",
        lambda *_args: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    result, _batch = execute_parallel_save(jobs, 2, FaultRecovery("abort", error))

    assert len(result.files) == len(jobs)
    assert not any(job.stage.exists() for job in jobs)


def test_parallel_stage_cleanup_error_is_reported_after_fallback_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path)
    monkeypatch.setattr(parallel_save, "execute_image_jobs", _worker_success)
    real_unlink = Path.unlink

    def fail_stage_once(path: Path, *, missing_ok: bool = False) -> None:
        if path == jobs[0].stage:
            raise OSError("stage cleanup")
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_stage_once)

    result, _batch = execute_parallel_save(jobs, 2)

    assert result.files[0].outcome is FileOutcome.FAILED
    assert result.files[0].issues[-1].message == "stage cleanup"
    assert not any(job.stage.exists() for job in jobs)


def test_warm_recovery_skips_completed_job_before_worker_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path)
    jobs[0].destination.write_bytes(b"CACHED_OUTPUT")
    launched: list[Path] = []

    def record_workers(
        runnable: tuple[ImageJob, ...], workers: int
    ) -> ImageJobBatchResult:
        launched.extend(job.source for job in runnable)
        return _worker_success(runnable, workers)

    monkeypatch.setattr(parallel_save, "execute_image_jobs", record_workers)

    result, _batch = execute_parallel_save(
        jobs, 2, WarmRecovery(jobs[0].source, jobs[0].destination)
    )

    assert launched == [jobs[1].source]
    assert [item.outcome for item in result.files] == [
        FileOutcome.SKIPPED,
        FileOutcome.PROCESSED,
    ]
