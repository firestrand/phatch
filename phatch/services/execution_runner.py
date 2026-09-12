from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from phatch.core.execution_ports import (
    Action,
    ExecutionInteraction,
    ExecutionProgress,
    IssueRecorder,
    Photo,
    PhotoAccess,
    Recovery,
    UpdateCallback,
)
from phatch.core.execution_types import (
    DiscoveredFile,
    ExecutionContext,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOutcome,
    ExecutionPosition,
    FileResult,
    IssueSeverity,
    IssueStage,
    ProgressDecision,
    RecoveryReevaluation,
)


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    actions: tuple[Action, ...]
    sources: tuple[DiscoveredFile, ...]
    required_variables: tuple[str, ...]
    repeat: int
    skip_existing: bool
    update: UpdateCallback | None
    recovery: Recovery | None = None


@dataclass(frozen=True, slots=True)
class RunnerServices:
    interaction: ExecutionInteraction
    progress: ExecutionProgress
    photo_access: PhotoAccess
    issue_recorder: IssueRecorder


class BatchRunner(Protocol):
    def run(
        self,
        context: ExecutionContext,
        plan: ExecutionPlan,
    ) -> ExecutionOutcome: ...


class ExecutionRunner:
    __slots__ = ("services",)

    def __init__(self, services: RunnerServices) -> None:
        self.services = services

    def run(
        self,
        context: ExecutionContext,
        plan: ExecutionPlan,
    ) -> ExecutionOutcome:
        for file_index, source in enumerate(plan.sources):
            recovery_result = (
                plan.recovery.completed_reports(source.path)
                if plan.recovery is not None
                else None
            )
            match recovery_result:
                case tuple() as recovered:
                    context.files.append(
                        FileResult(source.path, ExecutionDecision.SKIP, recovered)
                    )
                    if plan.update is not None:
                        plan.update()
                    continue
                case RecoveryReevaluation(reason=reason):
                    self._record(
                        context,
                        ExecutionIssue(
                            IssueStage.RECOVERY,
                            IssueSeverity.WARNING,
                            reason.value,
                            source.path,
                        ),
                    )
                case None:
                    pass
            attempt = (
                plan.recovery.begin(source.path) if plan.recovery is not None else None
            )
            opened = self.services.photo_access.open(
                source,
                plan.required_variables,
            )
            match opened:
                case ExecutionIssue() as issue:
                    self._record(context, issue)
                    if attempt is not None:
                        attempt.fail((issue,))
                    decision = self._decide(context, issue, False)
                    if decision is ExecutionDecision.ABORT:
                        return ExecutionOutcome.CANCELLED
                    context.files.append(
                        FileResult(source.path, ExecutionDecision.SKIP)
                    )
                    if plan.update is not None:
                        plan.update()
                    continue
                case _ as photo:
                    pass
            if attempt is not None:
                photo.set_output_transaction(attempt.transaction)
            issue_start = len(context.issues)
            finished = False
            try:
                outcome, photo = self._run_photo(context, plan, photo, file_index)
                if outcome is ExecutionOutcome.CANCELLED:
                    if attempt is not None:
                        attempt.abort()
                    return outcome
                reports = photo.reports()
                file_issues = tuple(context.issues[issue_start:])
                if attempt is not None:
                    attempt.finish(reports, file_issues)
                    reports = photo.reports()
                context.files.append(
                    FileResult(source.path, ExecutionDecision.CONTINUE, reports)
                )
                photo.close()
                finished = True
            finally:
                if attempt is not None and not finished:
                    attempt.abort()
            if plan.update is not None:
                plan.update()
        return ExecutionOutcome.COMPLETED

    def _run_photo(
        self,
        context: ExecutionContext,
        plan: ExecutionPlan,
        photo: Photo,
        file_index: int,
    ) -> tuple[ExecutionOutcome, Photo]:
        for repeat_index in range(plan.repeat):
            position = ExecutionPosition(
                file_index,
                repeat_index,
                file_index * plan.repeat + repeat_index,
            )
            photo.set_position(position)
            if (
                self.services.progress.file_started(photo.source, position)
                is ProgressDecision.CANCEL
            ):
                photo.close()
                return ExecutionOutcome.CANCELLED, photo
            if plan.skip_existing and context.action_run.is_done(
                plan.actions[-1], photo
            ):
                continue
            photo.prepare_repeat_image(repeat_index, plan.repeat)
            for action_index, action in enumerate(plan.actions):
                if (
                    self.services.progress.action_started(position, action_index)
                    is ProgressDecision.CANCEL
                ):
                    photo.close()
                    return ExecutionOutcome.CANCELLED, photo
                application = context.action_run.apply(action, photo)
                photo = application.photo
                for issue in application.issues:
                    self._record(context, issue)
                if application.succeeded:
                    continue
                decision = self._decide(context, application.issues[-1], True)
                if decision is ExecutionDecision.ABORT:
                    photo.close()
                    return ExecutionOutcome.CANCELLED, photo
        return ExecutionOutcome.COMPLETED, photo

    def _record(self, context: ExecutionContext, issue: ExecutionIssue) -> None:
        self.services.issue_recorder.record(issue, len(context.issues))
        context.issues.append(issue)

    def _decide(
        self,
        context: ExecutionContext,
        issue: ExecutionIssue,
        can_continue: bool,
    ) -> ExecutionDecision:
        if not context.prompt_on_issue and context.remembered_decision is not None:
            return context.remembered_decision
        response = self.services.interaction.decide_issue(issue, can_continue)
        context.prompt_on_issue = response.prompt_on_future_issues
        if not response.prompt_on_future_issues:
            context.remembered_decision = response.decision
        return response.decision
