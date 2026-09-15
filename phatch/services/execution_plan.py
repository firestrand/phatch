from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from phatch.core.execution_ports import (
    Action,
    ExecutionInteraction,
    ExecutionProgress,
    IssueRecorder,
    PhotoAccess,
    Recovery,
    UpdateCallback,
)
from phatch.core.execution_types import (
    DiscoveredFile,
    ExecutionContext,
    ExecutionIssue,
    ExecutionOutcome,
    IssueResponse,
)


class RecoveryIssueDecision(Protocol):
    def __call__(
        self,
        issue: ExecutionIssue,
        can_continue: bool,
    ) -> IssueResponse: ...


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
    recovery_decision: RecoveryIssueDecision | None = None


class BatchRunner(Protocol):
    def run(
        self,
        context: ExecutionContext,
        plan: ExecutionPlan,
    ) -> ExecutionOutcome: ...
