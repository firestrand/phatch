from pathlib import Path

import pytest

from phatch.core.execution_types import (
    CancellationState,
    ExecutionIssue,
    ExecutionOutcome,
    ExecutionResult,
    FileOutcome,
    FileResult,
    IssueSeverity,
    IssueStage,
    OutputRecord,
    ReportFile,
    RollbackState,
)
from phatch.services.report_privacy import ReportPrivacyContext, SensitiveRoot
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


def test_execution_report_v2_reconciles_partial_failure() -> None:
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.ERROR,
        "failed",
        source=Path("bad.png"),
    )
    files = (
        FileResult(Path("good.png"), FileOutcome.PROCESSED),
        FileResult(Path("bad.png"), FileOutcome.FAILED, issues=(issue,)),
    )
    result = ExecutionResult(
        ExecutionOutcome.COMPLETED,
        tuple(file.source for file in files),
        files,
        (issue,),
        1.25,
    )

    report = execution_report(result)

    assert report["report_version"] == 2
    assert report["outcome"] == "partial_success"
    assert report["counts"] == {
        "processed": 1,
        "skipped": 0,
        "failed": 1,
        "cancelled": 0,
        "total": 2,
    }
    assert set(report) == {
        "report_version",
        "outcome",
        "elapsed_seconds",
        "counts",
        "files",
        "issues",
    }


def test_execution_report_reconciles_every_file_outcome() -> None:
    sources = tuple(
        Path(name)
        for name in ("processed.png", "skipped.png", "failed.png", "cancelled.png")
    )
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.ERROR,
        "failed before cancellation",
        sources[2],
    )
    files = (
        FileResult(sources[0], FileOutcome.PROCESSED),
        FileResult(sources[1], FileOutcome.SKIPPED),
        FileResult(
            sources[2],
            FileOutcome.FAILED,
            issues=(issue,),
            cancellation=CancellationState.REQUESTED,
        ),
        FileResult(
            sources[3],
            FileOutcome.CANCELLED,
            cancellation=CancellationState.REQUESTED,
        ),
    )
    result = ExecutionResult(
        ExecutionOutcome.CANCELLED,
        sources,
        files,
        (issue,),
    )

    report = execution_report(result)

    assert report["outcome"] == "user_cancellation"
    assert report["counts"] == {
        "processed": 1,
        "skipped": 1,
        "failed": 1,
        "cancelled": 1,
        "total": 4,
    }
    assert [file["outcome"] for file in report["files"]] == [
        "processed",
        "skipped",
        "failed",
        "cancelled",
    ]


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (
            ExecutionResult(
                ExecutionOutcome.CANCELLED,
                (Path("cancel.png"),),
                (
                    FileResult(
                        Path("cancel.png"),
                        FileOutcome.CANCELLED,
                        cancellation=CancellationState.REQUESTED,
                    ),
                ),
            ),
            "user_cancellation",
        ),
        (ExecutionResult(ExecutionOutcome.FAILED, ()), "processing_failure"),
        (ExecutionResult(ExecutionOutcome.COMPLETED, ()), "success"),
    ],
)
def test_execution_report_maps_batch_outcomes(
    result: ExecutionResult, expected: str
) -> None:
    assert execution_report(result)["outcome"] == expected


def test_execution_report_serializes_explicit_file_and_output_states() -> None:
    source = Path("inputs/source.png")
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.ERROR,
        "output failed",
        source=source,
        action_label="save",
        details="rollback complete",
    )
    output = OutputRecord(
        ReportFile(source, Path("outputs/output.png"), 20, 10, "RGB"),
        survived=False,
    )
    file_result = FileResult(
        source,
        FileOutcome.FAILED,
        issues=(issue,),
        outputs=(output,),
        rollback=RollbackState.COMPLETED,
    )
    result = ExecutionResult(
        ExecutionOutcome.COMPLETED,
        (source,),
        (file_result,),
        (issue,),
        0.5,
    )

    report = execution_report(result)

    assert report["files"][0] == {
        "source": "<input>/source.png",
        "outcome": "failed",
        "cancellation": "not_requested",
        "rollback": "completed",
        "outputs": [
            {
                "path": "<output>/output.png",
                "survived": False,
            }
        ],
    }
    assert report["issues"][0]["action_id"] == "save"


def test_execution_report_redacts_known_roots_and_credentials() -> None:
    private_root = Path("/private/input")
    source = private_root / "source.png"
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.ERROR,
        f"Authorization: Bearer secret-token at {source}",
        source=source,
        details="password=hunter2 GPS=51.0",
    )
    file_result = FileResult(source, FileOutcome.FAILED, issues=(issue,))
    privacy = ReportPrivacyContext((SensitiveRoot(private_root, "<input>"),))
    result = ExecutionResult(
        ExecutionOutcome.COMPLETED,
        (source,),
        (file_result,),
        (issue,),
    )

    report = execution_report(result, privacy=privacy)
    serialized = str(report)

    assert report["files"][0]["source"] == "<input>/source.png"
    assert "secret-token" not in serialized
    assert "hunter2" not in serialized
    assert "51.0" not in serialized
    assert str(private_root) not in serialized
