from pathlib import Path

import pytest

from phatch.core.execution_types import (
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOutcome,
    ExecutionResult,
    FileResult,
    IssueSeverity,
    IssueStage,
)
from phatch.services.structured_report import (
    AutomationOutcome,
    ExitCode,
    execution_report,
    exit_code,
)


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (AutomationOutcome.SUCCESS, ExitCode.SUCCESS),
        (AutomationOutcome.PARTIAL_SUCCESS, ExitCode.PARTIAL_SUCCESS),
        (AutomationOutcome.VALIDATION_FAILURE, ExitCode.VALIDATION_FAILURE),
        (AutomationOutcome.UNAVAILABLE_CAPABILITY, ExitCode.UNAVAILABLE_CAPABILITY),
        (AutomationOutcome.PROCESSING_FAILURE, ExitCode.PROCESSING_FAILURE),
        (AutomationOutcome.USER_CANCELLATION, ExitCode.USER_CANCELLATION),
    ],
)
def test_every_outcome_has_stable_exit_code(
    outcome: AutomationOutcome, expected: ExitCode
) -> None:
    assert exit_code(outcome) is expected


def test_execution_report_classifies_partial_failure_with_stable_json_keys() -> None:
    # Given
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.ERROR,
        "failed",
        source=Path("bad.png"),
    )
    result = ExecutionResult(
        ExecutionOutcome.COMPLETED,
        (
            FileResult(Path("good.png"), ExecutionDecision.CONTINUE),
            FileResult(Path("bad.png"), ExecutionDecision.SKIP),
        ),
        (issue,),
        1.25,
    )

    # When
    report = execution_report(result)

    # Then
    assert report["report_version"] == 1
    assert report["outcome"] == "partial_success"
    assert set(report) == {
        "report_version",
        "outcome",
        "elapsed_seconds",
        "files",
        "issues",
    }


@pytest.mark.parametrize(
    ("execution_outcome", "issues", "expected"),
    [
        (ExecutionOutcome.CANCELLED, (), "user_cancellation"),
        (ExecutionOutcome.FAILED, (), "processing_failure"),
        (ExecutionOutcome.COMPLETED, (), "success"),
        (
            ExecutionOutcome.COMPLETED,
            (
                ExecutionIssue(
                    IssueStage.ACTION_EXECUTION,
                    IssueSeverity.ERROR,
                    "failed",
                ),
            ),
            "processing_failure",
        ),
    ],
)
def test_execution_report_maps_terminal_outcomes(
    execution_outcome, issues, expected
) -> None:
    result = ExecutionResult(execution_outcome, (), issues, 0.0)

    assert execution_report(result)["outcome"] == expected


def test_execution_report_serializes_file_outputs_and_issue_details() -> None:
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.WARNING,
        "warning",
        source=Path("source.png"),
        action_label="save",
        details="detail",
    )
    file_result = FileResult(Path("source.png"), ExecutionDecision.CONTINUE)
    result = ExecutionResult(ExecutionOutcome.COMPLETED, (file_result,), (issue,), 0.5)

    report = execution_report(result)

    assert report["files"][0]["source"] == str(Path("source.png").resolve())
    assert report["issues"][0]["source"] == str(Path("source.png").resolve())
    assert report["issues"][0]["action_id"] == "save"
    assert report["issues"][0]["details"] == "detail"
