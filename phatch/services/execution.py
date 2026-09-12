from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, assert_never

from phatch.core.execution_ports import (
    ActionDependencies,
    ActionRun,
    Clock,
    ExecutionInteraction,
    ExecutionProgress,
    FileDiscovery,
    IssueRecorder,
    PhotoAccess,
    Recovery,
)
from phatch.core.execution_types import (
    ExecutionContext,
    ExecutionIssue,
    ExecutionOutcome,
    ExecutionRequest,
    ExecutionResult,
    IssueSeverity,
    IssueStage,
)
from phatch.services.action_validation import (
    AcceptedActionList,
    ActionListRejectionReason,
    ActionListValidationResult,
    RejectedActionList,
    SaveActionRequired,
    validate_actionlist,
)
from phatch.services.execution_runner import (
    BatchRunner,
    ExecutionPlan,
)


class ExecutionValidator(Protocol):
    def validate(
        self,
        request: ExecutionRequest,
        action_run: ActionRun,
    ) -> ActionListValidationResult: ...


class TypedExecutionValidator:
    __slots__ = ()

    def validate(
        self,
        request: ExecutionRequest,
        action_run: ActionRun,
    ) -> ActionListValidationResult:
        return validate_actionlist(
            request.actions,
            request.options,
            lambda actions: (
                issue.message
                if (issue := action_run.safety_issue(actions)) is not None
                else ""
            ),
        )


@dataclass(frozen=True, slots=True)
class ExecutionServices:
    discovery: FileDiscovery
    dependencies: ActionDependencies
    interaction: ExecutionInteraction
    progress: ExecutionProgress
    photo_access: PhotoAccess
    issue_recorder: IssueRecorder
    clock: Clock
    runner: BatchRunner
    validator: ExecutionValidator
    recovery: Recovery | None = None


class ExecutionService:
    __slots__ = ("services",)

    def __init__(self, services: ExecutionServices) -> None:
        self.services = services

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        started = self.services.clock.monotonic()
        self.services.issue_recorder.begin()
        action_run = self.services.dependencies.begin_run(request.options)
        context = ExecutionContext(action_run, request.options.prompt_on_issue)
        progress_started = False
        try:
            validation = self.services.validator.validate(request, action_run)
            match validation:
                case RejectedActionList(reason=reason, diagnostic=diagnostic):
                    issue = _validation_issue(reason, diagnostic)
                    self._record(context, issue)
                    self.services.interaction.present_issue(issue)
                    return self._result(context, ExecutionOutcome.FAILED, started)
                case SaveActionRequired(enabled_actions=actions):
                    self.services.interaction.request_save_action(actions)
                    return self._result(context, ExecutionOutcome.FAILED, started)
                case AcceptedActionList(
                    enabled_actions=actions,
                    overwrite_existing_forced=overwrite_forced,
                ):
                    pass
                case unreachable:
                    assert_never(unreachable)

            selection = self.services.interaction.select_execution(request)
            if selection is None:
                return self._result(context, ExecutionOutcome.CANCELLED, started)
            discovered = self.services.discovery.discover(
                selection.paths,
                selection.options.extensions,
                recursive=selection.options.recursive,
            )
            match discovered:
                case ExecutionIssue() as issue:
                    self._record(context, issue)
                    self.services.interaction.present_issue(issue)
                    return self._result(context, ExecutionOutcome.FAILED, started)
                case tuple() as sources:
                    pass
                case unreachable:
                    assert_never(unreachable)
            if not sources:
                issue = ExecutionIssue(
                    IssueStage.FILE_DISCOVERY,
                    IssueSeverity.ERROR,
                    "No image files were found.",
                )
                self._record(context, issue)
                self.services.interaction.present_issue(issue)
                return self._result(context, ExecutionOutcome.FAILED, started)

            if selection.options.verify_images:
                valid = tuple(
                    source
                    for source in sources
                    if self.services.photo_access.verify(source)
                )
                invalid = tuple(source for source in sources if source not in valid)
                if invalid and not self.services.interaction.confirm_invalid_files(
                    invalid
                ):
                    return self._result(context, ExecutionOutcome.CANCELLED, started)
                if not valid:
                    issue = ExecutionIssue(
                        IssueStage.PHOTO_OPEN,
                        IssueSeverity.ERROR,
                        "No valid image files were found.",
                    )
                    self._record(context, issue)
                    self.services.interaction.present_issue(issue)
                    return self._result(context, ExecutionOutcome.FAILED, started)
                if not self.services.interaction.confirm_valid_files(valid):
                    return self._result(context, ExecutionOutcome.CANCELLED, started)
                sources = valid

            for action in actions:
                if (issue := action_run.initialize(action)) is not None:
                    self._record(context, issue)
                    self.services.interaction.present_issue(issue)
                    return self._result(context, ExecutionOutcome.FAILED, started)

            required_variables = action_run.required_variables(actions)
            self.services.progress.start(
                len(sources) * selection.options.repeat,
                len(actions) + 1,
            )
            progress_started = True
            skip_existing = (
                not (selection.options.overwrite_existing or overwrite_forced)
                and selection.options.require_save_action
            )
            outcome = self.services.runner.run(
                context,
                ExecutionPlan(
                    actions=actions,
                    sources=sources,
                    required_variables=required_variables,
                    repeat=selection.options.repeat,
                    skip_existing=skip_existing,
                    update=request.update,
                    recovery=self.services.recovery,
                ),
            )
            self.services.progress.close()
            progress_started = False
            if outcome is ExecutionOutcome.COMPLETED and request.update is not None:
                request.update()
            return self._result(context, outcome, started)
        finally:
            if progress_started:
                self.services.progress.close()
            self.services.issue_recorder.close()

    def _record(self, context: ExecutionContext, issue: ExecutionIssue) -> None:
        self.services.issue_recorder.record(issue, len(context.issues))
        context.issues.append(issue)

    def _result(
        self,
        context: ExecutionContext,
        outcome: ExecutionOutcome,
        started: float,
    ) -> ExecutionResult:
        return ExecutionResult(
            outcome,
            tuple(context.files),
            tuple(context.issues),
            self.services.clock.monotonic() - started,
        )


def _validation_issue(
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
