from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from pathlib import Path
from typing import TypeVar, assert_never

_TupleItem = TypeVar("_TupleItem")


class ExecutionInvariantError(ValueError):
    __slots__ = ("reason",)

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def require_tuple(values: tuple[_TupleItem, ...], field_name: str) -> None:
    if not isinstance(values, tuple):
        raise ExecutionInvariantError(f"{field_name} must be a tuple")


class ExecutionOutcome(StrEnum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class FileOutcome(StrEnum):
    PROCESSED = "processed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CancellationState(StrEnum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"


class RollbackState(StrEnum):
    NOT_REQUIRED = "not_required"
    COMPLETED = "completed"
    FAILED = "failed"


class IssueSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


class IssueStage(StrEnum):
    FILE_DISCOVERY = "file_discovery"
    ACTION_VALIDATION = "action_validation"
    PLUGIN_IMPORT = "plugin_import"
    ACTION_INITIALIZATION = "action_initialization"
    PHOTO_OPEN = "photo_open"
    ACTION_EXECUTION = "action_execution"
    RECOVERY = "recovery"


@dataclass(frozen=True, slots=True)
class ReportFile:
    source: Path
    path: Path
    width: int | None = None
    height: int | None = None
    mode: str | None = None

    def __post_init__(self) -> None:
        if self.width is None and self.height is None and self.mode is None:
            return
        if self.width is None or self.height is None or self.mode is None:
            raise ExecutionInvariantError(
                "report width, height, and mode must be all present or all absent"
            )
        if self.width <= 0 or self.height <= 0 or not self.mode:
            raise ExecutionInvariantError(
                "report details require positive dimensions and a nonempty mode"
            )

    @property
    def filename(self) -> str:
        return self.path.name


@dataclass(frozen=True, slots=True)
class ExecutionIssue:
    stage: IssueStage
    severity: IssueSeverity
    message: str
    source: Path | None = None
    action_label: str | None = None
    details: str | None = None

    def __post_init__(self) -> None:
        if not self.message:
            raise ExecutionInvariantError("issue message must not be empty")


@dataclass(frozen=True, slots=True)
class OutputRecord:
    report: ReportFile
    survived: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.survived, bool):
            raise ExecutionInvariantError("output survived must be a boolean")


@dataclass(frozen=True, slots=True)
class FileResult:
    source: Path
    outcome: FileOutcome
    issues: tuple[ExecutionIssue, ...] = ()
    outputs: tuple[OutputRecord, ...] = ()
    cancellation: CancellationState = CancellationState.NOT_REQUESTED
    rollback: RollbackState = RollbackState.NOT_REQUIRED

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, FileOutcome):
            raise ExecutionInvariantError("outcome must be a FileOutcome")
        if not isinstance(self.cancellation, CancellationState):
            raise ExecutionInvariantError("cancellation must be a CancellationState")
        if not isinstance(self.rollback, RollbackState):
            raise ExecutionInvariantError("rollback must be a RollbackState")
        require_tuple(self.issues, "issues")
        require_tuple(self.outputs, "outputs")
        errors = tuple(
            issue for issue in self.issues if issue.severity is IssueSeverity.ERROR
        )
        if self.outcome is FileOutcome.FAILED:
            if not errors:
                raise ExecutionInvariantError("a failed file must contain an error")
        elif errors:
            raise ExecutionInvariantError("only failed files may contain errors")
        if self.outcome is FileOutcome.CANCELLED:
            if self.cancellation is not CancellationState.REQUESTED:
                raise ExecutionInvariantError(
                    "cancelled file requires a cancellation annotation"
                )
        elif (
            self.outcome is not FileOutcome.FAILED
            and self.cancellation is CancellationState.REQUESTED
        ):
            raise ExecutionInvariantError(
                "a cancellation annotation requires a failed or cancelled file"
            )
        if any(issue.source not in (None, self.source) for issue in self.issues):
            raise ExecutionInvariantError("file issue source must match file source")
        if any(output.report.source != self.source for output in self.outputs):
            raise ExecutionInvariantError("output source must match file source")
        survived = tuple(output.survived for output in self.outputs)
        if self.rollback is RollbackState.NOT_REQUIRED and not all(survived):
            raise ExecutionInvariantError("non-surviving output requires rollback")
        if self.rollback is RollbackState.COMPLETED and any(survived):
            raise ExecutionInvariantError("completed rollback cannot retain outputs")
        if self.rollback is not RollbackState.NOT_REQUIRED and self.outcome not in (
            FileOutcome.FAILED,
            FileOutcome.CANCELLED,
        ):
            raise ExecutionInvariantError(
                "rollback requires a failed or cancelled file"
            )

    @property
    def reports(self) -> tuple[ReportFile, ...]:
        return tuple(output.report for output in self.outputs if output.survived)


@dataclass(frozen=True, slots=True)
class FileOutcomeCounts:
    processed: int
    skipped: int
    failed: int
    cancelled: int

    @property
    def total(self) -> int:
        return self.processed + self.skipped + self.failed + self.cancelled


def _count_outcomes(files: tuple[FileResult, ...]) -> FileOutcomeCounts:
    processed = skipped = failed = cancelled = 0
    for file in files:
        match file.outcome:
            case FileOutcome.PROCESSED:
                processed += 1
            case FileOutcome.SKIPPED:
                skipped += 1
            case FileOutcome.FAILED:
                failed += 1
            case FileOutcome.CANCELLED:
                cancelled += 1
            case unreachable:
                assert_never(unreachable)
    return FileOutcomeCounts(processed, skipped, failed, cancelled)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class ExecutionResult:
    outcome: ExecutionOutcome
    planned_sources: tuple[Path, ...]
    files: tuple[FileResult, ...] = ()
    issues: tuple[ExecutionIssue, ...] = ()
    elapsed_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, ExecutionOutcome):
            raise ExecutionInvariantError("outcome must be an ExecutionOutcome")
        require_tuple(self.planned_sources, "planned_sources")
        require_tuple(self.files, "files")
        require_tuple(self.issues, "issues")
        if len(set(self.planned_sources)) != len(self.planned_sources):
            raise ExecutionInvariantError("planned_sources must not contain duplicates")
        if tuple(file.source for file in self.files) != self.planned_sources:
            raise ExecutionInvariantError(
                "each planned source must have exactly one terminal outcome"
            )
        file_issues = tuple(issue for file in self.files for issue in file.issues)
        if any(issue not in self.issues for issue in file_issues):
            raise ExecutionInvariantError("result issues must include file issues")
        files_by_source = {file.source: file for file in self.files}
        source_errors = tuple(
            issue
            for issue in self.issues
            if issue.severity is IssueSeverity.ERROR and issue.source in files_by_source
        )
        if any(
            issue not in files_by_source[issue.source].issues
            for issue in source_errors
            if issue.source is not None
        ):
            raise ExecutionInvariantError("source errors must match a file result")
        has_cancellation = any(
            file.cancellation is CancellationState.REQUESTED for file in self.files
        )
        mismatched = has_cancellation != (self.outcome is ExecutionOutcome.CANCELLED)
        if mismatched and (has_cancellation or self.planned_sources):
            raise ExecutionInvariantError("execution cancellation does not reconcile")
        if not isfinite(self.elapsed_seconds) or self.elapsed_seconds < 0:
            raise ExecutionInvariantError("elapsed_seconds must be finite and >= 0")

    @property
    def counts(self) -> FileOutcomeCounts:
        return _count_outcomes(self.files)

    @property
    def report(self) -> tuple[ReportFile, ...]:
        return tuple(report for file in self.files for report in file.reports)
