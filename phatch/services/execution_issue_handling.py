from __future__ import annotations

from phatch.core.execution_types import (
    ExecutionContext,
    ExecutionDecision,
    ExecutionIssue,
    IssueResponse,
)
from phatch.services.execution_plan import RunnerServices


class ExecutionIssueHandler:
    __slots__ = ("services",)

    def __init__(self, services: RunnerServices) -> None:
        self.services = services

    def record(self, context: ExecutionContext, issue: ExecutionIssue) -> None:
        self.services.issue_recorder.record(issue, len(context.issues))
        context.issues.append(issue)

    def decide(
        self,
        context: ExecutionContext,
        issue: ExecutionIssue,
        can_continue: bool,
    ) -> ExecutionDecision:
        if not context.prompt_on_issue and context.remembered_decision is not None:
            return context.remembered_decision
        response = self.services.interaction.decide_issue(issue, can_continue)
        return self._apply_response(context, response)

    def decide_recovery(
        self,
        context: ExecutionContext,
        issue: ExecutionIssue,
    ) -> ExecutionDecision:
        if self.services.recovery_decision is None:
            return self.decide(context, issue, False)
        response = self.services.recovery_decision(issue, False)
        return self._apply_response(context, response)

    @staticmethod
    def _apply_response(
        context: ExecutionContext,
        response: IssueResponse,
    ) -> ExecutionDecision:
        context.prompt_on_issue = response.prompt_on_future_issues
        if not response.prompt_on_future_issues:
            context.remembered_decision = response.decision
        return response.decision
