from __future__ import annotations

from dataclasses import replace
from math import inf, nan
from pathlib import Path

import pytest

from phatch.core.execution_types import (
    ActionApplication,
    DiscoveredFile,
    ExecutionDecision,
    ExecutionInvariantError,
    ExecutionIssue,
    ExecutionOptions,
    ExecutionOutcome,
    ExecutionPosition,
    ExecutionRequest,
    ExecutionResult,
    ExecutionSelection,
    FileResult,
    IssueSeverity,
    IssueStage,
    ReportFile,
)
from tests.unit.core.execution_fakes import ActionFake, PhotoFake


def issue(severity: IssueSeverity = IssueSeverity.WARNING) -> ExecutionIssue:
    return ExecutionIssue(IssueStage.ACTION_EXECUTION, severity, "message")


@pytest.mark.parametrize("repeat", [0, -1, True, 1.5])
def test_options_reject_invalid_repeat(repeat: int | float) -> None:
    options = ExecutionOptions(("jpg",))

    with pytest.raises(ExecutionInvariantError, match="repeat"):
        replace(options, repeat=repeat)


def test_tuple_boundaries_reject_mutable_sequences() -> None:
    action = ActionFake()
    source = DiscoveredFile(Path("source.jpg"))
    options = ExecutionOptions(("jpg",))
    request = ExecutionRequest((action,), options, (source.path,))
    selection = ExecutionSelection((source.path,), options)
    photo = PhotoFake(source)
    application = ActionApplication(photo, True, ())
    report = ReportFile(source.path, Path("output.jpg"))
    file_result = FileResult(source.path, ExecutionDecision.CONTINUE, (report,))
    result = ExecutionResult(
        ExecutionOutcome.COMPLETED,
        (file_result,),
        (issue(),),
    )

    with pytest.raises(ExecutionInvariantError, match="extensions"):
        replace(options, extensions=["jpg"])
    with pytest.raises(ExecutionInvariantError, match="actions"):
        replace(request, actions=[action])
    with pytest.raises(ExecutionInvariantError, match="paths"):
        replace(request, paths=[source.path])
    with pytest.raises(ExecutionInvariantError, match="paths"):
        replace(selection, paths=[source.path])
    with pytest.raises(ExecutionInvariantError, match="issues"):
        replace(application, issues=[issue()])
    with pytest.raises(ExecutionInvariantError, match="reports"):
        replace(file_result, reports=[report])
    with pytest.raises(ExecutionInvariantError, match="files"):
        replace(result, files=[file_result])
    with pytest.raises(ExecutionInvariantError, match="issues"):
        replace(result, issues=[issue()])


@pytest.mark.parametrize("folder_index", [-1, -10])
def test_discovered_file_rejects_negative_folder_index(folder_index: int) -> None:
    with pytest.raises(ExecutionInvariantError, match="folder_index"):
        DiscoveredFile(Path("source.jpg"), folder_index=folder_index)


@pytest.mark.parametrize(
    ("file_index", "repeat_index", "item_index"),
    [(-1, 0, 0), (0, -1, 0), (0, 0, -1)],
)
def test_position_rejects_each_negative_index(
    file_index: int,
    repeat_index: int,
    item_index: int,
) -> None:
    with pytest.raises(ExecutionInvariantError, match="indices"):
        ExecutionPosition(file_index, repeat_index, item_index)


@pytest.mark.parametrize(
    ("width", "height", "mode"),
    [(1, None, "RGB"), (None, 1, "RGB"), (1, 1, None)],
)
def test_report_rejects_partial_image_details(
    width: int | None,
    height: int | None,
    mode: str | None,
) -> None:
    with pytest.raises(ExecutionInvariantError, match="all present"):
        ReportFile(Path("source.jpg"), Path("output.jpg"), width, height, mode)


@pytest.mark.parametrize(
    ("width", "height", "mode"),
    [(0, 1, "RGB"), (-1, 1, "RGB"), (1, 0, "RGB"), (1, -1, "RGB"), (1, 1, "")],
)
def test_report_rejects_invalid_present_image_details(
    width: int,
    height: int,
    mode: str,
) -> None:
    with pytest.raises(ExecutionInvariantError, match="positive dimensions"):
        ReportFile(Path("source.jpg"), Path("output.jpg"), width, height, mode)


def test_report_accepts_absent_or_complete_image_details() -> None:
    without_details = ReportFile(Path("source.jpg"), Path("first.jpg"))
    with_details = ReportFile(
        Path("source.jpg"),
        Path("second.jpg"),
        width=1,
        height=2,
        mode="RGB",
    )

    assert (without_details.width, without_details.height, without_details.mode) == (
        None,
        None,
        None,
    )
    assert (with_details.width, with_details.height, with_details.mode) == (
        1,
        2,
        "RGB",
    )


def test_issue_rejects_empty_message_and_preserves_optional_details() -> None:
    with pytest.raises(ExecutionInvariantError, match="message"):
        ExecutionIssue(IssueStage.PHOTO_OPEN, IssueSeverity.ERROR, "")

    valid = ExecutionIssue(
        IssueStage.PHOTO_OPEN,
        IssueSeverity.ERROR,
        "open failed",
        source=Path("source.jpg"),
        action_label="Open",
        details="trace",
    )

    assert (valid.source, valid.action_label, valid.details) == (
        Path("source.jpg"),
        "Open",
        "trace",
    )


def test_action_application_enforces_success_error_coherence() -> None:
    photo = PhotoFake(DiscoveredFile(Path("source.jpg")))
    warning = issue()
    error = issue(IssueSeverity.ERROR)

    assert ActionApplication(photo, True, (warning,)).issues == (warning,)
    assert ActionApplication(photo, False, (warning, error)).issues == (warning, error)
    with pytest.raises(ExecutionInvariantError, match="successful"):
        ActionApplication(photo, True, (error,))
    with pytest.raises(ExecutionInvariantError, match="failed"):
        ActionApplication(photo, False, ())
    with pytest.raises(ExecutionInvariantError, match="failed"):
        ActionApplication(photo, False, (warning,))


@pytest.mark.parametrize("elapsed", [-1.0, nan, inf, -inf])
def test_result_rejects_invalid_elapsed_seconds(elapsed: float) -> None:
    with pytest.raises(ExecutionInvariantError, match="elapsed_seconds"):
        ExecutionResult(ExecutionOutcome.FAILED, elapsed_seconds=elapsed)
