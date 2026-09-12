from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from phatch.core.execution_ports import Action, ActionRun, Photo, UpdateCallback

_TupleItem = TypeVar("_TupleItem")


@dataclass(frozen=True, slots=True)
class ExecutionInvariantError(ValueError):
    reason: str

    def __str__(self) -> str:
        return self.reason


def _require_tuple(values: tuple[_TupleItem, ...], field_name: str) -> None:
    if not isinstance(values, tuple):
        raise ExecutionInvariantError(f"{field_name} must be a tuple")


class ExecutionDecision(StrEnum):
    CONTINUE = "continue"
    SKIP = "skip"
    ABORT = "abort"


class ExecutionOutcome(StrEnum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ProgressDecision(StrEnum):
    CONTINUE = "continue"
    CANCEL = "cancel"


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


class RecoveryReason(StrEnum):
    INPUT_CHANGED = "input_changed"
    ACTIONS_CHANGED = "actions_changed"
    OUTPUT_CHANGED = "output_changed"
    PREVIOUSLY_FAILED = "previously_failed"


@dataclass(frozen=True, slots=True)
class ExecutionOptions:
    extensions: tuple[str, ...]
    recursive: bool = False
    prompt_on_issue: bool = True
    overwrite_existing: bool = True
    require_save_action: bool = True
    verify_images: bool = True
    always_show_status: bool = True
    safe_mode: bool = True
    repeat: int = 1

    def __post_init__(self) -> None:
        _require_tuple(self.extensions, "extensions")
        if (
            isinstance(self.repeat, bool)
            or not isinstance(self.repeat, int)
            or self.repeat < 1
        ):
            raise ExecutionInvariantError("repeat must be an integer of at least one")


@dataclass(frozen=True, slots=True)
class RecoveryConfiguration:
    journal_path: Path

    def __post_init__(self) -> None:
        if not self.journal_path.is_absolute():
            raise ExecutionInvariantError("recovery journal path must be absolute")


@dataclass(frozen=True, slots=True)
class RecoveryReevaluation:
    reason: RecoveryReason


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    actions: tuple[Action, ...]
    options: ExecutionOptions
    paths: tuple[Path, ...] | None = None
    drop: bool = False
    update: UpdateCallback | None = None

    def __post_init__(self) -> None:
        _require_tuple(self.actions, "actions")
        if self.paths is not None:
            _require_tuple(self.paths, "paths")


@dataclass(frozen=True, slots=True)
class ExecutionSelection:
    paths: tuple[Path, ...]
    options: ExecutionOptions

    def __post_init__(self) -> None:
        _require_tuple(self.paths, "paths")


@dataclass(frozen=True, slots=True)
class DiscoveredFile:
    path: Path
    source_root: Path | None = None
    folder_index: int = 0

    def __post_init__(self) -> None:
        if self.folder_index < 0:
            raise ExecutionInvariantError("folder_index must be nonnegative")


@dataclass(frozen=True, slots=True)
class ExecutionPosition:
    file_index: int
    repeat_index: int
    item_index: int

    def __post_init__(self) -> None:
        if min(self.file_index, self.repeat_index, self.item_index) < 0:
            raise ExecutionInvariantError("execution indices must be nonnegative")


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
class IssueResponse:
    decision: ExecutionDecision
    prompt_on_future_issues: bool


@dataclass(frozen=True, slots=True)
class ActionApplication:
    photo: Photo
    succeeded: bool
    issues: tuple[ExecutionIssue, ...] = ()

    def __post_init__(self) -> None:
        _require_tuple(self.issues, "issues")
        has_error = any(issue.severity is IssueSeverity.ERROR for issue in self.issues)
        if self.succeeded and has_error:
            raise ExecutionInvariantError(
                "a successful action application cannot contain an error"
            )
        if not self.succeeded and not has_error:
            raise ExecutionInvariantError(
                "a failed action application must contain an error"
            )


@dataclass(frozen=True, slots=True)
class FileResult:
    source: Path
    decision: ExecutionDecision
    reports: tuple[ReportFile, ...] = ()

    def __post_init__(self) -> None:
        _require_tuple(self.reports, "reports")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    outcome: ExecutionOutcome
    files: tuple[FileResult, ...] = ()
    issues: tuple[ExecutionIssue, ...] = ()
    elapsed_seconds: float = 0.0

    def __post_init__(self) -> None:
        _require_tuple(self.files, "files")
        _require_tuple(self.issues, "issues")
        if not isfinite(self.elapsed_seconds) or self.elapsed_seconds < 0:
            raise ExecutionInvariantError(
                "elapsed_seconds must be finite and nonnegative"
            )

    @property
    def report(self) -> tuple[ReportFile, ...]:
        return tuple(report for file in self.files for report in file.reports)


@dataclass(slots=True)
class ExecutionContext:
    """Mutable state owned by exactly one execution."""

    action_run: ActionRun
    prompt_on_issue: bool
    remembered_decision: ExecutionDecision | None = field(default=None, init=False)
    issues: list[ExecutionIssue] = field(default_factory=list, init=False)
    files: list[FileResult] = field(default_factory=list, init=False)
