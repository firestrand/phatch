from __future__ import annotations

from pathlib import Path

from phatch.core.execution_ports import ActionDependencies
from phatch.core.execution_types import (
    DiscoveredFile,
    ExecutionContext,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOptions,
    ExecutionOutcome,
    ExecutionResult,
    FileResult,
    IssueSeverity,
    IssueStage,
    ReportFile,
)
from tests.unit.core.execution_fakes import ActionDependenciesFake


def test_result_report_flattens_in_order_without_deduplication() -> None:
    first = ReportFile(Path("one.jpg"), Path("first.jpg"))
    duplicate = ReportFile(Path("two.jpg"), Path("same.jpg"))
    result = ExecutionResult(
        ExecutionOutcome.COMPLETED,
        files=(
            FileResult(
                Path("one.jpg"),
                ExecutionDecision.CONTINUE,
                (first, duplicate),
            ),
            FileResult(
                Path("two.jpg"),
                ExecutionDecision.SKIP,
                (duplicate,),
            ),
        ),
        elapsed_seconds=1.25,
    )

    assert result.report == (first, duplicate, duplicate)


def test_execution_contexts_own_independent_run_state() -> None:
    options = ExecutionOptions(("jpg",), prompt_on_issue=True)
    dependencies: ActionDependencies = ActionDependenciesFake()
    first = ExecutionContext(
        action_run=dependencies.begin_run(options),
        prompt_on_issue=options.prompt_on_issue,
    )
    second = ExecutionContext(
        action_run=dependencies.begin_run(options),
        prompt_on_issue=options.prompt_on_issue,
    )
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.WARNING,
        "warning",
    )
    file_result = FileResult(Path("source.jpg"), ExecutionDecision.CONTINUE)

    first.prompt_on_issue = False
    first.remembered_decision = ExecutionDecision.SKIP
    first.issues.append(issue)
    first.files.append(file_result)

    assert first.action_run is not second.action_run
    assert first.issues is not second.issues
    assert first.files is not second.files
    assert second.prompt_on_issue is True
    assert second.remembered_decision is None
    assert second.issues == []
    assert second.files == []
    assert not hasattr(first, "__dict__")


def test_zero_values_are_valid_execution_boundaries() -> None:
    source = DiscoveredFile(Path("source.jpg"), folder_index=0)
    result = ExecutionResult(
        ExecutionOutcome.CANCELLED,
        files=(FileResult(source.path, ExecutionDecision.ABORT),),
        elapsed_seconds=0.0,
    )

    assert result.outcome is ExecutionOutcome.CANCELLED
    assert result.elapsed_seconds == 0.0
