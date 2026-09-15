from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from .execution_results import CancellationState as CancellationState
from .execution_results import (
    ExecutionInvariantError,
    ExecutionIssue,
    FileResult,
    IssueSeverity,
    require_tuple,
)
from .execution_results import ExecutionOutcome as ExecutionOutcome
from .execution_results import ExecutionResult as ExecutionResult
from .execution_results import FileOutcome as FileOutcome
from .execution_results import FileOutcomeCounts as FileOutcomeCounts
from .execution_results import IssueStage as IssueStage
from .execution_results import OutputRecord as OutputRecord
from .execution_results import ReportFile as ReportFile
from .execution_results import RollbackState as RollbackState

if TYPE_CHECKING:
    from phatch.core.execution_ports import Action, ActionRun, Photo, UpdateCallback

_TupleItem = TypeVar("_TupleItem")


def _require_tuple(values: tuple[_TupleItem, ...], field_name: str) -> None:
    require_tuple(values, field_name)


class ExecutionDecision(StrEnum):
    CONTINUE = "continue"
    SKIP = "skip"
    ABORT = "abort"


class ProgressDecision(StrEnum):
    CONTINUE = "continue"
    CANCEL = "cancel"


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


@dataclass(slots=True)
class ExecutionContext:
    """Mutable state owned by exactly one execution."""

    action_run: ActionRun
    prompt_on_issue: bool
    remembered_decision: ExecutionDecision | None = field(default=None, init=False)
    planned_sources: tuple[Path, ...] = field(default=(), init=False)
    issues: list[ExecutionIssue] = field(default_factory=list, init=False)
    files: list[FileResult] = field(default_factory=list, init=False)
