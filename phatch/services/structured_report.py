from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Final, TypedDict, assert_never

from phatch.core.execution_types import (
    ExecutionOutcome,
    ExecutionResult,
)
from phatch.services.action_schema import normalize_identifier
from phatch.services.report_privacy import (
    ReportPrivacyContext,
    privacy_for_paths,
    redact_path,
    redact_text,
)

REPORT_VERSION: Final = 2


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


class OutputReportData(TypedDict):
    path: str
    survived: bool


class FileReportData(TypedDict):
    source: str
    outcome: str
    cancellation: str
    rollback: str
    outputs: list[OutputReportData]


class IssueReportData(TypedDict):
    stage: str
    severity: str
    message: str
    source: str | None
    action_id: str | None
    details: str | None


class CountReportData(TypedDict):
    processed: int
    skipped: int
    failed: int
    cancelled: int
    total: int


class ExecutionReportData(TypedDict):
    report_version: int
    outcome: str
    elapsed_seconds: float
    counts: CountReportData
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


def execution_report(
    result: ExecutionResult,
    *,
    privacy: ReportPrivacyContext | None = None,
) -> ExecutionReportData:
    report_privacy = privacy or privacy_for_paths(
        result.planned_sources,
        tuple(output.report.path for file in result.files for output in file.outputs),
    )
    counts = result.counts
    return {
        "report_version": REPORT_VERSION,
        "outcome": _execution_outcome(result).value,
        "elapsed_seconds": result.elapsed_seconds,
        "counts": {
            "processed": counts.processed,
            "skipped": counts.skipped,
            "failed": counts.failed,
            "cancelled": counts.cancelled,
            "total": counts.total,
        },
        "files": [
            {
                "source": redact_path(file.source, report_privacy),
                "outcome": file.outcome.value,
                "cancellation": file.cancellation.value,
                "rollback": file.rollback.value,
                "outputs": [
                    {
                        "path": redact_path(output.report.path, report_privacy),
                        "survived": output.survived,
                    }
                    for output in file.outputs
                ],
            }
            for file in result.files
        ],
        "issues": [
            {
                "stage": issue.stage.value,
                "severity": issue.severity.value,
                "message": redact_text(issue.message, report_privacy),
                "source": (
                    redact_path(issue.source, report_privacy)
                    if issue.source is not None
                    else None
                ),
                "action_id": (
                    normalize_identifier(issue.action_label)
                    if issue.action_label is not None
                    else None
                ),
                "details": (
                    redact_text(issue.details, report_privacy)
                    if issue.details is not None
                    else None
                ),
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
            has_failures = result.counts.failed > 0
            has_successes = result.counts.processed + result.counts.skipped > 0
            if has_failures and has_successes:
                return AutomationOutcome.PARTIAL_SUCCESS
            if has_failures:
                return AutomationOutcome.PROCESSING_FAILURE
            return AutomationOutcome.SUCCESS
        case unreachable:
            assert_never(unreachable)
