from pathlib import Path

import pytest
from PIL import Image

from phatch.services.parallel_image_jobs import ImageJob
from phatch.services.action_schema import ActionDocument
from phatch.services.parallel_save import (
    build_image_jobs,
    execute_parallel_save,
    parallel_constraint,
)
from phatch.services.parallel_save_spec import SaveJobSpec
from phatch.services.preflight import PreflightResult
from phatch.services.recovery import RecoveryJournal, RecoverySession


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
    assert [record["state"] for record in journal.records()] == [
        "prepared",
        "completed",
        "failed",
    ]


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
    assert result.files[1].decision.value == "skip"
    assert len(result.issues) == 1


def test_job_builder_skips_unavailable_output_codec(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "input.png"
    destination = tmp_path / "output" / "result.unavailable"
    Image.new("RGB", (2, 2)).save(source)
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
    jobs = build_image_jobs(spec, preflight)

    # Then
    assert jobs == ()


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
    assert not first.destination.exists()
    assert batch.worker_pids == ()


def test_dynamic_index_naming_explicitly_stays_serial() -> None:
    # Given
    document = ActionDocument.from_values(
        "",
        (("save", (("file_name", "<filename>-<index>"),)),),
    )

    # When
    constraint = parallel_constraint(document)

    # Then
    assert constraint == "parallel Save does not support dynamic variables: index"


def test_non_save_action_set_explicitly_stays_serial() -> None:
    document = ActionDocument.from_values("", (("scale", ()),))

    assert parallel_constraint(document) == (
        "parallel execution requires exactly one enabled Save action"
    )


def test_build_and_execute_jobs_uses_preflight_paths_and_save_options(
    tmp_path: Path,
) -> None:
    # Given
    source = tmp_path / "input.png"
    destination = tmp_path / "output" / "result.png"
    Image.new("RGB", (14, 11), "orange").save(source)
    document = ActionDocument.from_values(
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
    jobs = build_image_jobs(SaveJobSpec(91, True, "none", 72, False), preflight)
    result, _batch = execute_parallel_save(jobs, 1)

    # Then
    assert jobs[0].quality is None
    assert jobs[0].optimize is True
    assert result.files[0].reports[0].path == destination
    assert destination.is_file()
