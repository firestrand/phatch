import os
from pathlib import Path

import pytest
from PIL import Image

from phatch.core.execution_types import (
    CancellationState,
    ExecutionOutcome,
    FileOutcome,
    RollbackState,
)
from phatch.services import output_transaction, parallel_save, parallel_save_publication
from phatch.services.output_rollback import RollbackError, RollbackFailure
from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobBatchResult,
    ImageJobSuccess,
)
from phatch.services.recovery import RecoveryJournal, RecoverySession


def _publication_job(
    tmp_path: Path,
) -> tuple[ImageJob, ImageJobSuccess, bytes]:
    source = tmp_path / "source.png"
    stage = tmp_path / "stage.png"
    destination = tmp_path / "output.png"
    Image.new("RGB", (4, 3), "blue").save(source)
    Image.new("RGB", (4, 3), "red").save(stage)
    original_bytes = b"ORIGINAL_OUTPUT"
    destination.write_bytes(original_bytes)
    return (
        ImageJob(0, source, destination, stage, "PNG", 12),
        ImageJobSuccess(0, source, destination, stage, 4, 3, "RGB", "PNG", 1234),
        original_bytes,
    )


def _worker_success(
    monkeypatch: pytest.MonkeyPatch,
    success: ImageJobSuccess,
) -> None:
    monkeypatch.setattr(
        parallel_save,
        "execute_image_jobs",
        lambda _jobs, _workers: ImageJobBatchResult((success,), (1234,), 4321, 1),
    )


def test_interrupt_after_destination_replace_restores_original_and_reports_disk_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job, success, original_bytes = _publication_job(tmp_path)
    _worker_success(monkeypatch, success)
    real_replace = os.replace

    def interrupt_after_replace(source_path: Path, destination_path: Path) -> None:
        real_replace(source_path, destination_path)
        raise KeyboardInterrupt

    monkeypatch.setattr(output_transaction.os, "replace", interrupt_after_replace)
    journal = RecoveryJournal(tmp_path / "recovery.jsonl")

    result, _batch = parallel_save.execute_parallel_save(
        (job,), 1, RecoverySession(journal, "digest")
    )

    file_result = result.files[0]
    assert result.outcome is ExecutionOutcome.CANCELLED
    assert file_result.outcome is FileOutcome.CANCELLED
    assert file_result.cancellation is CancellationState.REQUESTED
    assert file_result.rollback is RollbackState.COMPLETED
    assert file_result.outputs[0].survived is False
    assert job.destination.read_bytes() == original_bytes
    assert not tuple(tmp_path.glob(".*.bak"))
    assert [record["state"] for record in journal.records()] == ["prepared"]


@pytest.mark.parametrize("checkpoint", ["before_backup", "before_replace"])
def test_interrupt_before_destination_publish_preserves_original(
    checkpoint: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job, success, original_bytes = _publication_job(tmp_path)
    _worker_success(monkeypatch, success)

    def interrupt(*_paths: Path) -> None:
        raise KeyboardInterrupt

    if checkpoint == "before_backup":
        monkeypatch.setattr(output_transaction, "backup_originals", interrupt)
    else:
        monkeypatch.setattr(output_transaction.os, "replace", interrupt)
    journal = RecoveryJournal(tmp_path / "recovery.jsonl")

    result, _batch = parallel_save.execute_parallel_save(
        (job,), 1, RecoverySession(journal, "digest")
    )

    file_result = result.files[0]
    assert file_result.outcome is FileOutcome.CANCELLED
    assert file_result.rollback is RollbackState.COMPLETED
    assert file_result.outputs[0].survived is False
    assert job.destination.read_bytes() == original_bytes
    assert not tuple(tmp_path.glob(".*.bak"))
    assert [record["state"] for record in journal.records()] == ["prepared"]


def test_rollback_failure_reports_published_destination_and_retains_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job, success, original_bytes = _publication_job(tmp_path)
    _worker_success(monkeypatch, success)
    real_replace = os.replace

    def fail_after_replace(source_path: Path, destination_path: Path) -> None:
        real_replace(source_path, destination_path)
        raise PermissionError(13, "publication interrupted", destination_path)

    def fail_restore(originals) -> None:
        original = originals[0]
        raise RollbackError(
            (
                RollbackFailure(
                    original.destination,
                    original.backup,
                    PermissionError(13, "restore denied", original.destination),
                ),
            )
        )

    monkeypatch.setattr(output_transaction.os, "replace", fail_after_replace)
    monkeypatch.setattr(output_transaction, "restore_originals", fail_restore)
    journal = RecoveryJournal(tmp_path / "recovery.jsonl")

    result, _batch = parallel_save.execute_parallel_save(
        (job,), 1, RecoverySession(journal, "digest")
    )

    file_result = result.files[0]
    assert result.outcome is ExecutionOutcome.COMPLETED
    assert file_result.outcome is FileOutcome.FAILED
    assert file_result.rollback is RollbackState.FAILED
    assert file_result.outputs[0].survived is True
    assert job.destination.read_bytes() != original_bytes
    backups = tuple(tmp_path.glob(".*.bak"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == original_bytes
    records = journal.records()
    assert [record["state"] for record in records] == ["prepared"]
    assert records[0]["outputs"][0]["backup_path"] == str(backups[0].resolve())


@pytest.mark.parametrize("checkpoint", ["remove_backups", "after_publish", "discard"])
def test_post_publish_cleanup_failure_reports_surviving_output(
    checkpoint: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job, success, original_bytes = _publication_job(tmp_path)
    _worker_success(monkeypatch, success)
    if checkpoint == "remove_backups":
        monkeypatch.setattr(
            output_transaction,
            "remove_backups",
            lambda _originals: (_ for _ in ()).throw(OSError("remove backup")),
        )
    elif checkpoint == "after_publish":
        request_type = parallel_save_publication.OutputRequest

        def failing_request(destination, encoder, metadata, validator):
            return request_type(
                destination,
                encoder,
                metadata,
                validator,
                after_publish=lambda: (_ for _ in ()).throw(OSError("after publish")),
            )

        monkeypatch.setattr(parallel_save_publication, "OutputRequest", failing_request)
    else:
        monkeypatch.setattr(
            output_transaction.DeferredOutputTransaction,
            "discard",
            lambda _transaction: (_ for _ in ()).throw(OSError("discard")),
        )
    journal = RecoveryJournal(tmp_path / "recovery.jsonl")

    result, _batch = parallel_save.execute_parallel_save(
        (job,), 1, RecoverySession(journal, "digest")
    )

    file_result = result.files[0]
    assert file_result.outcome is FileOutcome.FAILED
    assert file_result.outputs[0].survived is True
    assert file_result.rollback is RollbackState.FAILED
    assert job.destination.read_bytes() != original_bytes
    assert [record["state"] for record in journal.records()] == ["prepared"]
    backups = tuple(tmp_path.glob(".*.bak"))
    assert bool(backups) is (checkpoint == "remove_backups")


def test_raised_finish_after_publication_reports_actual_survival(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job, success, _original_bytes = _publication_job(tmp_path)
    _worker_success(monkeypatch, success)

    def publish_then_raise(_success, _report, _attempt):
        job.destination.write_bytes(job.stage.read_bytes())
        raise OSError("finish after publication")

    monkeypatch.setattr(parallel_save, "commit_image", publish_then_raise)

    result, _batch = parallel_save.execute_parallel_save(
        (job,), 1, RecoverySession(RecoveryJournal(tmp_path / "recovery.jsonl"), "d")
    )

    file_result = result.files[0]
    assert file_result.outcome is FileOutcome.FAILED
    assert file_result.outputs[0].survived is True
    assert file_result.rollback is RollbackState.FAILED
    assert not job.stage.exists()
