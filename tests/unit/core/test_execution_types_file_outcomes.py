from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from phatch.core.execution_types import (
    CancellationState,
    ExecutionDecision,
    ExecutionInvariantError,
    ExecutionIssue,
    ExecutionOutcome,
    ExecutionResult,
    FileOutcome,
    FileResult,
    IssueSeverity,
    IssueStage,
    OutputRecord,
    ReportFile,
    RollbackState,
)


def error(source: Path) -> ExecutionIssue:
    return ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.ERROR,
        "processing failed",
        source,
    )


def output(source: Path, name: str, *, survived: bool = True) -> OutputRecord:
    return OutputRecord(ReportFile(source, Path(name)), survived=survived)


def test_file_outcome_is_exhaustive_and_independent_of_interaction_decisions() -> None:
    assert tuple(FileOutcome) == (
        FileOutcome.PROCESSED,
        FileOutcome.SKIPPED,
        FileOutcome.FAILED,
        FileOutcome.CANCELLED,
    )
    with pytest.raises(ExecutionInvariantError, match="FileOutcome"):
        replace(
            FileResult(Path("source.jpg"), FileOutcome.PROCESSED),
            outcome=ExecutionDecision.CONTINUE,
        )


def test_file_result_rejects_untyped_state_enums() -> None:
    source = Path("source.jpg")

    with pytest.raises(ExecutionInvariantError, match="CancellationState"):
        replace(
            FileResult(source, FileOutcome.PROCESSED),
            cancellation="requested",
        )
    with pytest.raises(ExecutionInvariantError, match="RollbackState"):
        replace(
            FileResult(source, FileOutcome.PROCESSED),
            rollback="completed",
        )


def test_output_record_rejects_non_boolean_survival() -> None:
    report = ReportFile(Path("source.jpg"), Path("output.jpg"))

    with pytest.raises(ExecutionInvariantError, match="boolean"):
        replace(OutputRecord(report), survived=1)


def test_result_reconciles_every_planned_source_and_surviving_output() -> None:
    sources = tuple(
        Path(name) for name in ("processed", "recovery", "failed", "pending")
    )
    surviving = output(sources[0], "kept.jpg")
    rolled_back = output(sources[2], "removed.jpg", survived=False)
    failure = error(sources[2])
    files = (
        FileResult(sources[0], FileOutcome.PROCESSED, outputs=(surviving,)),
        FileResult(sources[1], FileOutcome.SKIPPED),
        FileResult(
            sources[2],
            FileOutcome.FAILED,
            issues=(failure,),
            outputs=(rolled_back,),
            cancellation=CancellationState.REQUESTED,
            rollback=RollbackState.COMPLETED,
        ),
        FileResult(
            sources[3],
            FileOutcome.CANCELLED,
            cancellation=CancellationState.REQUESTED,
        ),
    )

    result = ExecutionResult(
        ExecutionOutcome.CANCELLED,
        sources,
        files,
        issues=(failure,),
    )

    assert result.counts.processed == 1
    assert result.counts.skipped == 1
    assert result.counts.failed == 1
    assert result.counts.cancelled == 1
    assert result.counts.total == len(sources)
    assert result.report == (surviving.report,)
    assert files[2].outcome is FileOutcome.FAILED
    assert files[2].cancellation is CancellationState.REQUESTED


@pytest.mark.parametrize(
    ("planned", "files", "message"),
    [
        (
            (Path("one"), Path("two")),
            (FileResult(Path("one"), FileOutcome.PROCESSED),),
            "one terminal outcome",
        ),
        (
            (Path("one"),),
            (
                FileResult(Path("one"), FileOutcome.PROCESSED),
                FileResult(Path("one"), FileOutcome.SKIPPED),
            ),
            "one terminal outcome",
        ),
        (
            (Path("one"), Path("one")),
            (
                FileResult(Path("one"), FileOutcome.PROCESSED),
                FileResult(Path("one"), FileOutcome.PROCESSED),
            ),
            "planned_sources",
        ),
    ],
)
def test_result_rejects_missing_or_duplicate_source_outcomes(
    planned: tuple[Path, ...],
    files: tuple[FileResult, ...],
    message: str,
) -> None:
    with pytest.raises(ExecutionInvariantError, match=message):
        ExecutionResult(ExecutionOutcome.COMPLETED, planned, files)


@pytest.mark.parametrize("outcome", [FileOutcome.PROCESSED, FileOutcome.SKIPPED])
def test_nonfailed_outcome_rejects_source_error(outcome: FileOutcome) -> None:
    source = Path("source.jpg")

    with pytest.raises(ExecutionInvariantError, match="only failed"):
        FileResult(source, outcome, issues=(error(source),))


def test_failed_outcome_requires_error_and_cancelled_requires_annotation() -> None:
    source = Path("source.jpg")

    with pytest.raises(ExecutionInvariantError, match="failed file"):
        FileResult(source, FileOutcome.FAILED)
    with pytest.raises(ExecutionInvariantError, match="cancelled file"):
        FileResult(source, FileOutcome.CANCELLED)


def test_cancellation_annotation_is_only_valid_for_failed_or_cancelled_file() -> None:
    with pytest.raises(ExecutionInvariantError, match="cancellation annotation"):
        FileResult(
            Path("source.jpg"),
            FileOutcome.PROCESSED,
            cancellation=CancellationState.REQUESTED,
        )


@pytest.mark.parametrize(
    ("rollback", "survived", "message"),
    [
        (RollbackState.NOT_REQUIRED, False, "non-surviving"),
        (RollbackState.COMPLETED, True, "completed rollback"),
    ],
)
def test_rollback_state_reconciles_output_survival(
    rollback: RollbackState,
    survived: bool,
    message: str,
) -> None:
    source = Path("source.jpg")
    failure = error(source)

    with pytest.raises(ExecutionInvariantError, match=message):
        FileResult(
            source,
            FileOutcome.FAILED,
            issues=(failure,),
            outputs=(output(source, "output.jpg", survived=survived),),
            rollback=rollback,
        )


def test_output_record_source_must_match_file_source() -> None:
    with pytest.raises(ExecutionInvariantError, match="output source"):
        FileResult(
            Path("source.jpg"),
            FileOutcome.PROCESSED,
            outputs=(output(Path("other.jpg"), "output.jpg"),),
        )


def test_result_rejects_unreconciled_source_error() -> None:
    source = Path("source.jpg")
    source_error = error(source)

    with pytest.raises(ExecutionInvariantError, match="source errors"):
        ExecutionResult(
            ExecutionOutcome.COMPLETED,
            (source,),
            (FileResult(source, FileOutcome.PROCESSED),),
            issues=(source_error,),
        )


def test_result_rejects_unreconciled_batch_cancellation() -> None:
    source = Path("source.jpg")

    with pytest.raises(ExecutionInvariantError, match="cancellation"):
        ExecutionResult(
            ExecutionOutcome.CANCELLED,
            (source,),
            (FileResult(source, FileOutcome.PROCESSED),),
        )


def test_cancelled_result_without_discovered_sources_needs_no_file_annotation() -> None:
    result = ExecutionResult(ExecutionOutcome.CANCELLED, ())

    assert result.files == ()
    assert result.counts.total == 0
