from __future__ import annotations

from phatch.core.execution_types import (
    CancellationState,
    ExecutionContext,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOutcome,
    FileOutcome,
    FileResult,
    OutputRecord,
    RollbackState,
)
from phatch.services.execution_file_outcomes import (
    cancel_sources,
    finish_issue,
    is_interrupt,
    output_records,
)
from phatch.services.execution_issue_handling import ExecutionIssueHandler
from phatch.services.execution_plan import ExecutionPlan
from phatch.services.execution_recovery_boundary import SourceRecoveryBoundary
from phatch.services.recovery_outcomes import RecoveryFinishFailed


class RecoveryFailureResolver:
    __slots__ = ("context", "issues", "plan")

    def __init__(
        self,
        issues: ExecutionIssueHandler,
        context: ExecutionContext,
        plan: ExecutionPlan,
    ) -> None:
        self.issues = issues
        self.context = context
        self.plan = plan

    def finish(
        self,
        file_index: int,
        file_issues: tuple[ExecutionIssue, ...],
        failure: RecoveryFinishFailed,
        outputs: tuple[OutputRecord, ...],
    ) -> ExecutionOutcome | None:
        source = self.plan.sources[file_index]
        errors = (failure.cause, *failure.cleanup_errors)
        recovery_issues = tuple(finish_issue(source.path, error) for error in errors)
        for issue in recovery_issues:
            self.issues.record(self.context, issue)
        cancelled = any(is_interrupt(error) for error in errors)
        if not cancelled:
            cancelled = (
                self.issues.decide_recovery(self.context, recovery_issues[0])
                is ExecutionDecision.ABORT
            )
        self.context.files.append(
            FileResult(
                source.path,
                FileOutcome.FAILED,
                issues=(*file_issues, *recovery_issues),
                outputs=outputs,
                cancellation=(
                    CancellationState.REQUESTED
                    if cancelled
                    else CancellationState.NOT_REQUESTED
                ),
                rollback=failure.rollback,
            )
        )
        if cancelled:
            cancel_sources(self.context, self.plan.sources[file_index + 1 :])
            return ExecutionOutcome.CANCELLED
        if self.plan.update is not None:
            self.plan.update()
        return None

    def boundary(
        self,
        file_index: int,
        issue_start: int,
        result_start: int,
        failures: tuple[OSError | KeyboardInterrupt, ...],
        boundary: SourceRecoveryBoundary,
    ) -> bool:
        source = self.plan.sources[file_index]
        recovery_issues = tuple(finish_issue(source.path, error) for error in failures)
        for issue in recovery_issues:
            self.issues.record(self.context, issue)
        existing = (
            self.context.files[result_start]
            if len(self.context.files) > result_start
            else None
        )
        prior = (
            existing.issues
            if existing is not None
            else tuple(self.context.issues[issue_start : -len(recovery_issues)])
        )
        cancelled = (
            boundary.cancelled
            or (
                existing is not None
                and existing.cancellation is CancellationState.REQUESTED
            )
            or any(is_interrupt(error) for error in failures)
        )
        if not cancelled:
            cancelled = (
                self.issues.decide_recovery(self.context, recovery_issues[0])
                is ExecutionDecision.ABORT
            )
        outputs = (
            existing.outputs
            if existing is not None
            else output_records(boundary.reports, source.path, survived=False)
        )
        rollback = (
            existing.rollback
            if existing is not None
            else RollbackState.COMPLETED
            if boundary.reports
            else RollbackState.NOT_REQUIRED
        )
        result = FileResult(
            source.path,
            FileOutcome.FAILED,
            issues=(*prior, *recovery_issues),
            outputs=outputs,
            cancellation=(
                CancellationState.REQUESTED
                if cancelled
                else CancellationState.NOT_REQUESTED
            ),
            rollback=rollback,
        )
        if existing is None:
            self.context.files.insert(result_start, result)
        else:
            self.context.files[result_start] = result
        if cancelled and len(self.context.files) == result_start + 1:
            cancel_sources(self.context, self.plan.sources[file_index + 1 :])
        return cancelled
