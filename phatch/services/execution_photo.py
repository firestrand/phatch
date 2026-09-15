from __future__ import annotations

from dataclasses import dataclass

from phatch.core.execution_ports import Photo
from phatch.core.execution_types import (
    ExecutionContext,
    ExecutionDecision,
    ExecutionPosition,
    ProgressDecision,
)
from phatch.services.execution_issue_handling import ExecutionIssueHandler
from phatch.services.execution_plan import ExecutionPlan, RunnerServices


@dataclass(frozen=True, slots=True)
class PhotoExecution:
    context: ExecutionContext
    plan: ExecutionPlan
    photo: Photo
    file_index: int


@dataclass(frozen=True, slots=True)
class PhotoRunResult:
    photo: Photo
    processed: bool
    failed: bool
    cancelled: bool


class PhotoExecutor:
    __slots__ = ("issues", "services")

    def __init__(self, services: RunnerServices) -> None:
        self.services = services
        self.issues = ExecutionIssueHandler(services)

    def run(self, execution: PhotoExecution) -> PhotoRunResult:
        context = execution.context
        plan = execution.plan
        photo = execution.photo
        processed = False
        failed = False
        for repeat_index in range(plan.repeat):
            position = ExecutionPosition(
                execution.file_index,
                repeat_index,
                execution.file_index * plan.repeat + repeat_index,
            )
            photo.set_position(position)
            if (
                self.services.progress.file_started(photo.source, position)
                is ProgressDecision.CANCEL
            ):
                return PhotoRunResult(photo, processed, failed, True)
            if plan.skip_existing and context.action_run.is_done(
                plan.actions[-1], photo
            ):
                continue
            processed = True
            photo.prepare_repeat_image(repeat_index, plan.repeat)
            for action_index, action in enumerate(plan.actions):
                if (
                    self.services.progress.action_started(position, action_index)
                    is ProgressDecision.CANCEL
                ):
                    return PhotoRunResult(photo, processed, failed, True)
                application = context.action_run.apply(action, photo)
                photo = application.photo
                for issue in application.issues:
                    self.issues.record(context, issue)
                if application.succeeded:
                    continue
                failed = True
                decision = self.issues.decide(context, application.issues[-1], True)
                if decision is ExecutionDecision.ABORT:
                    return PhotoRunResult(photo, processed, failed, True)
        return PhotoRunResult(photo, processed, failed, False)
