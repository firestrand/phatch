from __future__ import annotations

from phatch.core.execution_types import (
    CancellationState,
    ExecutionContext,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOutcome,
    FileOutcome,
    FileResult,
    IssueSeverity,
    IssueStage,
    RecoveryReevaluation,
    RollbackState,
)
from phatch.services.execution_file_outcomes import (
    cancel_sources,
    normalize_output_sources,
    output_records,
)
from phatch.services.execution_issue_handling import ExecutionIssueHandler
from phatch.services.execution_photo import PhotoExecution, PhotoExecutor
from phatch.services.execution_plan import BatchRunner, ExecutionPlan, RunnerServices
from phatch.services.execution_recovery_boundary import SourceRecoveryBoundary
from phatch.services.execution_recovery_resolution import RecoveryFailureResolver
from phatch.services.recovery_outcomes import RecoveryFinishSucceeded

__all__ = ["BatchRunner", "ExecutionPlan", "RunnerServices"]


class ExecutionRunner:
    __slots__ = ("issues", "services")

    def __init__(self, services: RunnerServices) -> None:
        self.services = services
        self.issues = ExecutionIssueHandler(services)

    def run(self, context: ExecutionContext, plan: ExecutionPlan) -> ExecutionOutcome:
        for file_index, source in enumerate(plan.sources):
            boundary = SourceRecoveryBoundary(source.path)
            issue_start = len(context.issues)
            result_start = len(context.files)
            try:
                outcome = self._run_source(context, plan, file_index, boundary)
                failures: tuple[OSError | KeyboardInterrupt, ...] = ()
            except (OSError, KeyboardInterrupt) as error:
                outcome = None
                failures = (error,)
            failures = (*failures, *boundary.cleanup())
            if failures:
                if RecoveryFailureResolver(self.issues, context, plan).boundary(
                    file_index, issue_start, result_start, failures, boundary
                ):
                    return ExecutionOutcome.CANCELLED
                if plan.update is not None:
                    plan.update()
                continue
            if outcome is not None:
                return outcome
        return ExecutionOutcome.COMPLETED

    def _run_source(
        self,
        context: ExecutionContext,
        plan: ExecutionPlan,
        file_index: int,
        boundary: SourceRecoveryBoundary,
    ) -> ExecutionOutcome | None:
        source = plan.sources[file_index]
        recovered = (
            plan.recovery.completed_reports(source.path)
            if plan.recovery is not None
            else None
        )
        if isinstance(recovered, tuple):
            context.files.append(
                FileResult(
                    source.path,
                    FileOutcome.SKIPPED,
                    outputs=output_records(recovered, source.path),
                )
            )
            if plan.update is not None:
                plan.update()
            return None
        if isinstance(recovered, RecoveryReevaluation):
            self.issues.record(
                context,
                ExecutionIssue(
                    IssueStage.RECOVERY,
                    IssueSeverity.WARNING,
                    recovered.reason.value,
                    source.path,
                ),
            )
        attempt = boundary.begin(plan.recovery) if plan.recovery is not None else None
        opened = self.services.photo_access.open(source, plan.required_variables)
        if isinstance(opened, ExecutionIssue):
            self.issues.record(context, opened)
            boundary.fail((opened,))
            cancelled = (
                self.issues.decide(context, opened, False) is ExecutionDecision.ABORT
            )
            context.files.append(
                FileResult(
                    source.path,
                    FileOutcome.FAILED,
                    issues=(opened,),
                    cancellation=(
                        CancellationState.REQUESTED
                        if cancelled
                        else CancellationState.NOT_REQUESTED
                    ),
                )
            )
            if cancelled:
                cancel_sources(context, plan.sources[file_index + 1 :])
                return ExecutionOutcome.CANCELLED
            if plan.update is not None:
                plan.update()
            return None
        photo = opened
        boundary.attach(photo)
        issue_start = len(context.issues)
        if attempt is not None:
            photo.set_output_transaction(attempt.transaction)
        run = PhotoExecutor(self.services).run(
            PhotoExecution(context, plan, photo, file_index)
        )
        photo = run.photo
        boundary.attach(photo)
        reports = photo.reports()
        boundary.reports = reports
        file_issues = tuple(context.issues[issue_start:])
        if run.cancelled:
            boundary.cancelled = True
            if run.failed:
                boundary.fail(file_issues)
            else:
                boundary.abort()
            context.files.append(
                FileResult(
                    source.path,
                    FileOutcome.FAILED if run.failed else FileOutcome.CANCELLED,
                    issues=file_issues,
                    outputs=output_records(
                        reports, source.path, survived=attempt is None
                    ),
                    cancellation=CancellationState.REQUESTED,
                    rollback=(
                        RollbackState.COMPLETED
                        if attempt is not None and reports
                        else RollbackState.NOT_REQUIRED
                    ),
                )
            )
            cancel_sources(context, plan.sources[file_index + 1 :])
            return ExecutionOutcome.CANCELLED
        outputs = output_records(
            reports, source.path, survived=attempt is None or not run.failed
        )
        rollback = (
            RollbackState.COMPLETED
            if attempt is not None and run.failed and reports
            else RollbackState.NOT_REQUIRED
        )
        if run.failed:
            boundary.fail(file_issues)
        elif attempt is not None:
            finish = boundary.finish(file_issues)
            outputs = normalize_output_sources(finish.outputs, source.path)
            if not isinstance(finish, RecoveryFinishSucceeded):
                return RecoveryFailureResolver(self.issues, context, plan).finish(
                    file_index, file_issues, finish, outputs
                )
        context.files.append(
            FileResult(
                source.path,
                FileOutcome.FAILED
                if run.failed
                else FileOutcome.PROCESSED
                if run.processed and (reports or not plan.skip_existing)
                else FileOutcome.SKIPPED,
                issues=file_issues,
                outputs=outputs,
                rollback=rollback,
            )
        )
        if plan.update is not None:
            plan.update()
        return None
