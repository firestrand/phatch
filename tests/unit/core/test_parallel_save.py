from pathlib import Path

import pytest
from PIL import Image

from phatch.core.execution_types import (
    ExecutionOutcome,
    FileOutcome,
    OutputRecord,
    RollbackState,
)
from phatch.services import parallel_save
from phatch.services.action_schema import ActionDocument
from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobBatchResult,
    ImageJobCancelled,
    ImageJobFailure,
)
from phatch.services.parallel_save import (
    build_image_jobs,
    execute_parallel_save,
)
from phatch.services.parallel_save_spec import SaveJobSpec
from phatch.services.preflight import PreflightResult
from phatch.services.recovery import RecoveryJournal, RecoverySession
from phatch.services.recovery_outcomes import RecoveryFinishFailed


def _job(tmp_path: Path, index: int, name: str) -> ImageJob:
    source = tmp_path / f"{name}.png"
    Image.new("RGB", (12, 10), (index, 20, 30)).save(source)
    return ImageJob(
        index,
        source,
        tmp_path / "outputs" / f"{name}.png",
        tmp_path / f".{name}.stage.png",
        "PNG",
        120,
    )


def test_coordinator_commits_ordered_worker_results_and_journal(tmp_path: Path) -> None:
    # Given
    jobs = (_job(tmp_path, 0, "first"), _job(tmp_path, 1, "second"))
    jobs[0].destination.parent.mkdir()
    journal = RecoveryJournal(tmp_path / "journal.jsonl")
    recovery = RecoverySession(journal, "digest")

    # When
    result, batch = execute_parallel_save(jobs, 2, recovery)

    # Then
    assert [file.source for file in result.files] == [job.source for job in jobs]
    assert result.planned_sources == tuple(job.source for job in jobs)
    assert all(file.outcome is FileOutcome.PROCESSED for file in result.files)
    assert all(job.destination.is_file() for job in jobs)
    assert not any(job.stage.exists() for job in jobs)
    assert [record["state"] for record in journal.records()] == [
        "prepared",
        "completed",
        "prepared",
        "completed",
    ]
    assert batch.coordinator_pid not in batch.worker_pids


def test_worker_failure_preserves_unrelated_commit_and_failed_journal(
    tmp_path: Path,
) -> None:
    # Given
    jobs = (_job(tmp_path, 0, "good"), _job(tmp_path, 1, "bad"))
    jobs[0].destination.parent.mkdir()
    jobs[1].source.write_bytes(b"broken")
    journal = RecoveryJournal(tmp_path / "journal.jsonl")

    # When
    result, _batch = execute_parallel_save(jobs, 2, RecoverySession(journal, "digest"))

    # Then
    assert jobs[0].destination.is_file()
    assert not jobs[1].destination.exists()
    assert len(result.issues) == 1
    assert [file.outcome for file in result.files] == [
        FileOutcome.PROCESSED,
        FileOutcome.FAILED,
    ]
    assert [record["state"] for record in journal.records()] == [
        "prepared",
        "completed",
        "failed",
    ]


def test_worker_failure_and_cancellation_are_preserved_without_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_job = _job(tmp_path, 0, "failed")
    cancelled_job = _job(tmp_path, 1, "cancelled")
    failed_job.stage.write_bytes(b"failed stage")
    cancelled_job.stage.write_bytes(b"cancelled stage")
    batch = ImageJobBatchResult(
        (
            ImageJobFailure(
                failed_job.index,
                failed_job.source,
                failed_job.destination,
                failed_job.stage,
                "worker failed",
                1234,
            ),
            ImageJobCancelled(
                cancelled_job.index,
                cancelled_job.source,
                cancelled_job.destination,
                cancelled_job.stage,
                1235,
            ),
        ),
        (1234, 1235),
        4321,
        2,
    )
    monkeypatch.setattr(
        parallel_save,
        "execute_image_jobs",
        lambda _jobs, _workers: batch,
    )

    result, returned_batch = execute_parallel_save((failed_job, cancelled_job), 2)

    assert returned_batch is batch
    assert result.outcome is ExecutionOutcome.CANCELLED
    assert [file.outcome for file in result.files] == [
        FileOutcome.FAILED,
        FileOutcome.CANCELLED,
    ]
    assert result.issues[0].message == "worker failed"
    assert not failed_job.stage.exists()
    assert not cancelled_job.stage.exists()


@pytest.mark.parametrize("with_recovery", [False, True])
def test_publication_failure_preserves_unrelated_commit(
    tmp_path: Path,
    with_recovery: bool,
) -> None:
    # Given
    good = _job(tmp_path, 0, "good")
    blocked = _job(tmp_path, 1, "blocked")
    bad_parent = tmp_path / "blocked-output"
    bad_parent.write_text("blocks directory", encoding="utf-8")
    blocked = ImageJob(
        blocked.index,
        blocked.source,
        bad_parent / blocked.destination.name,
        blocked.stage,
        blocked.format_name,
        blocked.pixel_count,
    )
    jobs = (good, blocked)
    recovery = (
        RecoverySession(RecoveryJournal(tmp_path / "publication.jsonl"), "digest")
        if with_recovery
        else None
    )

    # When
    result, _batch = execute_parallel_save(jobs, 2, recovery)

    # Then
    assert good.destination.is_file()
    assert len(result.files) == 2
    assert result.files[1].outcome is FileOutcome.FAILED
    assert result.files[1].rollback is RollbackState.COMPLETED
    assert result.files[1].outputs[0].survived is False
    assert len(result.issues) == 1


def test_publication_rollback_failure_is_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = _job(tmp_path, 0, "rollback-failure")
    job.destination.parent.mkdir()
    monkeypatch.setattr(
        parallel_save,
        "commit_image",
        lambda _success, report, _attempt: RecoveryFinishFailed(
            PermissionError(13, "publication blocked", job.destination),
            (OutputRecord(report, survived=False),),
            RollbackState.FAILED,
        ),
    )

    result, _batch = execute_parallel_save((job,), 1)

    assert result.files[0].outcome is FileOutcome.FAILED
    assert result.files[0].rollback is RollbackState.FAILED
    assert result.files[0].outputs[0].survived is False


def test_job_builder_records_unavailable_output_codec_failure(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "input.png"
    destination = tmp_path / "output" / "result.unavailable"
    spec = SaveJobSpec(85, False, "none", 72, False)
    preflight = PreflightResult(
        (source,),
        (destination,),
        (),
        (),
        (),
        (),
        1,
    )

    # When
    construction = build_image_jobs(spec, preflight)
    result, _batch = execute_parallel_save(construction.jobs, 1)
    result = construction.reconcile(result)

    # Then
    assert construction.jobs == ()
    assert construction.planned_sources == (source,)
    assert len(construction.failures) == 1
    failure = construction.failures[0]
    assert failure.source == source
    assert failure.outcome is FileOutcome.FAILED
    assert failure.issues[0].source == source
    assert "output codec" in failure.issues[0].message.lower()
    assert ".unavailable" in failure.issues[0].message
    assert result.planned_sources == (source,)
    assert result.files == construction.failures
    assert result.counts.failed == 1


def test_output_collision_fails_before_worker_or_publication(tmp_path: Path) -> None:
    # Given
    first = _job(tmp_path, 0, "first")
    second = _job(tmp_path, 1, "second")
    collision = ImageJob(
        second.index,
        second.source,
        first.destination,
        second.stage,
        second.format_name,
        second.pixel_count,
    )

    # When
    result, batch = execute_parallel_save((first, collision), 2)

    # Then
    assert result.outcome.value == "failed"
    assert result.planned_sources == (first.source, collision.source)
    assert all(file.outcome is FileOutcome.FAILED for file in result.files)
    assert not first.destination.exists()
    assert batch.worker_pids == ()


def test_build_and_execute_jobs_uses_preflight_paths_and_save_options(
    tmp_path: Path,
) -> None:
    # Given
    source = tmp_path / "input.png"
    destination = tmp_path / "output" / "result.png"
    Image.new("RGB", (14, 11), "orange").save(source)
    ActionDocument.from_values(
        "",
        (
            (
                "save",
                (
                    ("png_optimize", "yes"),
                    ("jpeg_quality", "91"),
                    ("tiff_compression", "none"),
                ),
            ),
        ),
    )
    preflight = PreflightResult(
        (source,),
        (destination,),
        (),
        (),
        (),
        (),
        1,
    )

    # When
    construction = build_image_jobs(SaveJobSpec(91, True, "none", 72, False), preflight)
    result, _batch = execute_parallel_save(construction.jobs, 1)
    result = construction.reconcile(result)

    # Then
    assert construction.jobs[0].quality is None
    assert construction.jobs[0].optimize is True
    assert result.files[0].reports[0].path == destination
    assert destination.is_file()
