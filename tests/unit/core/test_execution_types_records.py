from __future__ import annotations

from dataclasses import FrozenInstanceError
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
    IssueResponse,
    IssueSeverity,
    IssueStage,
    ProgressDecision,
    ReportFile,
)
from tests.unit.core.execution_fakes import ActionFake, PhotoFake


def test_execution_enums_have_exact_members() -> None:
    assert tuple(ExecutionDecision.__members__.items()) == (
        ("CONTINUE", ExecutionDecision.CONTINUE),
        ("SKIP", ExecutionDecision.SKIP),
        ("ABORT", ExecutionDecision.ABORT),
    )
    assert tuple(ExecutionOutcome.__members__.items()) == (
        ("COMPLETED", ExecutionOutcome.COMPLETED),
        ("CANCELLED", ExecutionOutcome.CANCELLED),
        ("FAILED", ExecutionOutcome.FAILED),
    )
    assert tuple(ProgressDecision.__members__.items()) == (
        ("CONTINUE", ProgressDecision.CONTINUE),
        ("CANCEL", ProgressDecision.CANCEL),
    )
    assert tuple(IssueSeverity.__members__.items()) == (
        ("WARNING", IssueSeverity.WARNING),
        ("ERROR", IssueSeverity.ERROR),
    )
    assert tuple(IssueStage.__members__.items()) == (
        ("FILE_DISCOVERY", IssueStage.FILE_DISCOVERY),
        ("ACTION_VALIDATION", IssueStage.ACTION_VALIDATION),
        ("PLUGIN_IMPORT", IssueStage.PLUGIN_IMPORT),
        ("ACTION_INITIALIZATION", IssueStage.ACTION_INITIALIZATION),
        ("PHOTO_OPEN", IssueStage.PHOTO_OPEN),
        ("ACTION_EXECUTION", IssueStage.ACTION_EXECUTION),
        ("RECOVERY", IssueStage.RECOVERY),
    )


def test_records_are_frozen_and_slotted() -> None:
    source = DiscoveredFile(Path("source.jpg"))
    action = ActionFake()
    options = ExecutionOptions(("jpg",))
    report = ReportFile(Path("source.jpg"), Path("output.jpg"))
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.WARNING,
        "warning",
    )
    photo = PhotoFake(source)
    records = (
        (options, "repeat"),
        (ExecutionRequest((action,), options), "drop"),
        (ExecutionSelection((source.path,), options), "paths"),
        (source, "folder_index"),
        (ExecutionPosition(0, 0, 0), "item_index"),
        (report, "mode"),
        (issue, "message"),
        (IssueResponse(ExecutionDecision.CONTINUE, True), "decision"),
        (ActionApplication(photo, True), "succeeded"),
        (FileResult(source.path, ExecutionDecision.CONTINUE), "decision"),
        (ExecutionResult(ExecutionOutcome.COMPLETED), "outcome"),
    )

    for record, field_name in records:
        assert not hasattr(record, "__dict__")
        with pytest.raises(FrozenInstanceError):
            setattr(record, field_name, None)


def test_tuple_records_preserve_order_duplicates_and_none_distinction() -> None:
    first = ActionFake("first")
    second = ActionFake("second")
    path = Path("same.jpg")
    options = ExecutionOptions(("jpg", "png", "jpg"))
    implicit = ExecutionRequest((first, second, first), options)
    explicit_empty = ExecutionRequest((first,), options, paths=())
    selection = ExecutionSelection((path, Path("other.jpg"), path), options)

    assert options.extensions == ("jpg", "png", "jpg")
    assert implicit.actions == (first, second, first)
    assert implicit.paths is None
    assert explicit_empty.paths == ()
    assert selection.paths == (path, Path("other.jpg"), path)


def test_records_do_not_touch_the_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_access(path: Path) -> bool:
        raise AssertionError(path)

    monkeypatch.setattr(Path, "exists", unexpected_access)
    missing = Path("definitely-missing.jpg")

    discovered = DiscoveredFile(missing, source_root=Path("missing-root"))
    report = ReportFile(missing, Path("also-missing.jpg"))
    issue = ExecutionIssue(
        IssueStage.FILE_DISCOVERY,
        IssueSeverity.ERROR,
        "missing",
        source=missing,
    )

    assert discovered.path == missing
    assert report.filename == "also-missing.jpg"
    assert issue.source == missing


def test_invariant_error_preserves_typed_reason_and_string() -> None:
    error = ExecutionInvariantError("invalid execution record")

    assert error.reason == "invalid execution record"
    assert str(error) == "invalid execution record"
