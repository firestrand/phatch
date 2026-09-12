from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import TypedDict, assert_never

from phatch.core.execution_types import (
    ExecutionDecision,
    ExecutionOutcome,
    ExecutionResult,
    IssueSeverity,
)
from phatch.services.action_schema import normalize_identifier


class AutomationOutcome(StrEnum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    VALIDATION_FAILURE = "validation_failure"
    UNAVAILABLE_CAPABILITY = "unavailable_capability"
    PROCESSING_FAILURE = "processing_failure"
    USER_CANCELLATION = "user_cancellation"


class ExitCode(IntEnum):
    SUCCESS = 0
    PARTIAL_SUCCESS = 1
    VALIDATION_FAILURE = 2
    UNAVAILABLE_CAPABILITY = 3
    PROCESSING_FAILURE = 4
    USER_CANCELLATION = 130


class FileReportData(TypedDict):
    source: str
    decision: str
    outputs: list[str]


class IssueReportData(TypedDict):
    stage: str
    severity: str
    message: str
    source: str | None
    action_id: str | None
    details: str | None


class ExecutionReportData(TypedDict):
    report_version: int
    outcome: str
    elapsed_seconds: float
    files: list[FileReportData]
    issues: list[IssueReportData]


def exit_code(outcome: AutomationOutcome) -> ExitCode:
    match outcome:
        case AutomationOutcome.SUCCESS:
            return ExitCode.SUCCESS
        case AutomationOutcome.PARTIAL_SUCCESS:
            return ExitCode.PARTIAL_SUCCESS
        case AutomationOutcome.VALIDATION_FAILURE:
            return ExitCode.VALIDATION_FAILURE
        case AutomationOutcome.UNAVAILABLE_CAPABILITY:
            return ExitCode.UNAVAILABLE_CAPABILITY
        case AutomationOutcome.PROCESSING_FAILURE:
            return ExitCode.PROCESSING_FAILURE
        case AutomationOutcome.USER_CANCELLATION:
            return ExitCode.USER_CANCELLATION
        case unreachable:
            assert_never(unreachable)


def execution_report(result: ExecutionResult) -> ExecutionReportData:
    outcome = _execution_outcome(result)
    return {
        "report_version": 1,
        "outcome": outcome.value,
        "elapsed_seconds": result.elapsed_seconds,
        "files": [
            {
                "source": str(file.source.resolve()),
                "decision": file.decision.value,
                "outputs": [str(report.path.resolve()) for report in file.reports],
            }
            for file in result.files
        ],
        "issues": [
            {
                "stage": issue.stage.value,
                "severity": issue.severity.value,
                "message": issue.message,
                "source": (
                    str(issue.source.resolve()) if issue.source is not None else None
                ),
                "action_id": (
                    normalize_identifier(issue.action_label)
                    if issue.action_label is not None
                    else None
                ),
                "details": issue.details,
            }
            for issue in result.issues
        ],
    }


def _execution_outcome(result: ExecutionResult) -> AutomationOutcome:
    match result.outcome:
        case ExecutionOutcome.CANCELLED:
            return AutomationOutcome.USER_CANCELLATION
        case ExecutionOutcome.FAILED:
            return AutomationOutcome.PROCESSING_FAILURE
        case ExecutionOutcome.COMPLETED:
            has_errors = any(
                issue.severity is IssueSeverity.ERROR for issue in result.issues
            )
            has_success = any(
                file.decision is ExecutionDecision.CONTINUE for file in result.files
            )
            if has_errors and has_success:
                return AutomationOutcome.PARTIAL_SUCCESS
            if has_errors:
                return AutomationOutcome.PROCESSING_FAILURE
            return AutomationOutcome.SUCCESS
        case unreachable:
            assert_never(unreachable)
