from pathlib import Path

import pytest
from PIL import Image

from phatch.core.execution_types import (
    ExecutionIssue,
    ExecutionOutcome,
    FileOutcome,
    OutputRecord,
    RecoveryReevaluation,
    ReportFile,
    RollbackState,
)
from phatch.services import parallel_save
from phatch.services.output_transaction import DeferredOutputTransaction
from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobBatchResult,
    ImageJobSuccess,
)
from phatch.services.parallel_save import execute_parallel_save
from phatch.services.recovery_outcomes import (
    RecoveryFinishFailed,
    RecoveryFinishSucceeded,
)


class _RecordingAttempt:
    def __init__(self) -> None:
        self.aborts = 0
        self.transaction = DeferredOutputTransaction()

    def finish(
        self,
        reports: tuple[ReportFile, ...],
        issues: tuple[ExecutionIssue, ...],
    ) -> RecoveryFinishSucceeded:
        del issues
        return RecoveryFinishSucceeded(
            tuple(OutputRecord(report) for report in reports)
        )

    def fail(self, issues: tuple[ExecutionIssue, ...]) -> None:
        del issues
        raise AssertionError("fail must not run after interruption")

    def abort(self) -> None:
        self.aborts += 1


class _RecordingRecovery:
    def __init__(self, attempt: _RecordingAttempt) -> None:
        self.attempt = attempt

    def begin(self, source: Path) -> _RecordingAttempt:
        del source
        return self.attempt

    def completed_reports(
        self, source: Path
    ) -> tuple[ReportFile, ...] | RecoveryReevaluation | None:
        del source
        return None


class _InterruptingAttempt(_RecordingAttempt):
    def finish(
        self,
        reports: tuple[ReportFile, ...],
        issues: tuple[ExecutionIssue, ...],
    ) -> RecoveryFinishFailed:
        del issues
        return RecoveryFinishFailed(
            KeyboardInterrupt(),
            tuple(OutputRecord(report, survived=False) for report in reports),
            RollbackState.COMPLETED,
        )


def test_interrupt_aborts_all_attempts_and_removes_stages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    source = tmp_path / "source.png"
    stage = tmp_path / "stage.png"
    Image.new("RGB", (4, 3)).save(source)
    stage.write_bytes(b"partial worker output")
    job = ImageJob(0, source, tmp_path / "output.png", stage, "PNG", 12)
    attempt = _RecordingAttempt()
    monkeypatch.setattr(
        parallel_save,
        "execute_image_jobs",
        lambda _jobs, _workers: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    # When
    result, batch = execute_parallel_save((job,), 2, _RecordingRecovery(attempt))

    # Then
    assert result.outcome is ExecutionOutcome.CANCELLED
    assert result.files[0].outcome is FileOutcome.CANCELLED
    assert batch.results == ()
    assert attempt.aborts == 1
    assert not stage.exists()


def test_interrupt_after_prepare_aborts_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    source = tmp_path / "source.png"
    stage = tmp_path / "stage.png"
    Image.new("RGB", (4, 3)).save(source)
    Image.new("RGB", (4, 3)).save(stage)
    job = ImageJob(0, source, tmp_path / "output.png", stage, "PNG", 12)
    attempt = _InterruptingAttempt()
    success = ImageJobSuccess(
        0, source, job.destination, stage, 4, 3, "RGB", "PNG", 1234
    )
    monkeypatch.setattr(
        parallel_save,
        "execute_image_jobs",
        lambda _jobs, _workers: ImageJobBatchResult((success,), (1234,), 4321, 2),
    )

    # When
    result, _batch = execute_parallel_save((job,), 2, _RecordingRecovery(attempt))

    # Then
    assert result.files[0].outcome is FileOutcome.CANCELLED
    assert result.files[0].outputs[0].survived is False
    assert attempt.aborts == 1
    assert not job.destination.exists()
    assert not stage.exists()
