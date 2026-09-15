from __future__ import annotations

from dataclasses import dataclass

from phatch.core.execution_types import ExecutionIssue, IssueResponse
from phatch.services.legacy_interaction import LegacyInteraction


@dataclass(frozen=True, slots=True)
class LegacyRecoveryDecision:
    interaction: LegacyInteraction

    def __call__(
        self,
        issue: ExecutionIssue,
        can_continue: bool,
    ) -> IssueResponse:
        self.interaction.record_execution_error(
            None,
            issue,
            None,
            can_continue=can_continue,
        )
        return self.interaction.decide_issue(issue, can_continue)
