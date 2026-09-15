from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from phatch.core.execution_types import (
    CancellationState,
    DiscoveredFile,
    ExecutionContext,
    ExecutionIssue,
    FileOutcome,
    FileResult,
    IssueSeverity,
    IssueStage,
    OutputRecord,
    ReportFile,
)


def cancel_sources(
    context: ExecutionContext,
    sources: tuple[DiscoveredFile, ...],
) -> None:
    context.files.extend(
        FileResult(
            source.path,
            FileOutcome.CANCELLED,
            cancellation=CancellationState.REQUESTED,
        )
        for source in sources
    )


def output_records(
    reports: tuple[ReportFile, ...],
    source: Path,
    *,
    survived: bool = True,
) -> tuple[OutputRecord, ...]:
    return tuple(
        OutputRecord(replace(report, source=source), survived) for report in reports
    )


def normalize_output_sources(
    outputs: tuple[OutputRecord, ...],
    source: Path,
) -> tuple[OutputRecord, ...]:
    return tuple(
        replace(output, report=replace(output.report, source=source))
        for output in outputs
    )


def finish_issue(
    source: Path,
    cause: OSError | KeyboardInterrupt,
) -> ExecutionIssue:
    return ExecutionIssue(
        IssueStage.RECOVERY,
        IssueSeverity.ERROR,
        str(cause) if str(cause) else "Execution interrupted during recovery.",
        source,
    )


def is_interrupt(cause: OSError | KeyboardInterrupt) -> bool:
    return isinstance(cause, KeyboardInterrupt)
