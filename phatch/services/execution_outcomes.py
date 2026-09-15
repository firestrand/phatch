from __future__ import annotations

from typing import assert_never

from phatch.core.execution_types import (
    CancellationState,
    DiscoveredFile,
    ExecutionContext,
    ExecutionIssue,
    ExecutionOutcome,
    ExecutionResult,
    FileOutcome,
    FileResult,
    IssueSeverity,
    IssueStage,
)
from phatch.services.action_validation import ActionListRejectionReason


def invalid_file_result(
    source: DiscoveredFile,
    *,
    cancelled: bool,
) -> FileResult:
    issue = ExecutionIssue(
        IssueStage.PHOTO_OPEN,
        IssueSeverity.ERROR,
        "Image verification failed.",
        source.path,
    )
    return FileResult(
        source.path,
        FileOutcome.FAILED,
        issues=(issue,),
        cancellation=(
            CancellationState.REQUESTED
            if cancelled
            else CancellationState.NOT_REQUESTED
        ),
    )


def fail_unfinished(
    context: ExecutionContext,
    sources: tuple[DiscoveredFile, ...],
    issue: ExecutionIssue,
) -> None:
    completed = {file.source for file in context.files}
    context.files.extend(
        FileResult(source.path, FileOutcome.FAILED, issues=(issue,))
        for source in sources
        if source.path not in completed
    )


def execution_result(
    context: ExecutionContext,
    outcome: ExecutionOutcome,
    elapsed_seconds: float,
) -> ExecutionResult:
    files_by_source = {file.source: file for file in context.files}
    return ExecutionResult(
        outcome,
        context.planned_sources,
        tuple(files_by_source[source] for source in context.planned_sources),
        tuple(context.issues),
        elapsed_seconds,
    )


def validation_issue(
    reason: ActionListRejectionReason,
    diagnostic: str,
) -> ExecutionIssue:
    match reason:
        case ActionListRejectionReason.EMPTY:
            message = "The action list is empty."
        case ActionListRejectionReason.UNSAFE:
            message = diagnostic
        case ActionListRejectionReason.ALL_DISABLED:
            message = "There is no enabled action."
        case unreachable:
            assert_never(unreachable)
    return ExecutionIssue(
        IssueStage.ACTION_VALIDATION,
        IssueSeverity.ERROR,
        message,
    )
