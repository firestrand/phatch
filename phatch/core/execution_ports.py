from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from phatch.services.output_transaction import DeferredOutputTransaction

from phatch.core.execution_types import (
    ActionApplication,
    DiscoveredFile,
    ExecutionIssue,
    ExecutionOptions,
    ExecutionPosition,
    ExecutionRequest,
    ExecutionSelection,
    IssueResponse,
    ProgressDecision,
    RecoveryReevaluation,
    ReportFile,
)


class UpdateCallback(Protocol):
    def __call__(self) -> None: ...


class Clock(Protocol):
    def monotonic(self) -> float: ...


class IssueRecorder(Protocol):
    def begin(self) -> None: ...

    def record(self, issue: ExecutionIssue, sequence: int) -> None: ...

    def close(self) -> None: ...


class ExecutionInteraction(Protocol):
    def select_execution(
        self, request: ExecutionRequest
    ) -> ExecutionSelection | None: ...

    def present_issue(self, issue: ExecutionIssue) -> None: ...

    def request_save_action(self, actions: tuple[Action, ...]) -> None: ...

    def confirm_invalid_files(self, files: tuple[DiscoveredFile, ...]) -> bool: ...

    def confirm_valid_files(self, files: tuple[DiscoveredFile, ...]) -> bool: ...

    def decide_issue(
        self, issue: ExecutionIssue, can_continue: bool
    ) -> IssueResponse: ...


class ExecutionProgress(Protocol):
    def start(self, item_count: int, step_count: int) -> None: ...

    def file_started(
        self, source: DiscoveredFile, position: ExecutionPosition
    ) -> ProgressDecision: ...

    def action_started(
        self, position: ExecutionPosition, action_index: int
    ) -> ProgressDecision: ...

    def close(self) -> None: ...


class FileDiscovery(Protocol):
    def discover(
        self,
        paths: tuple[Path, ...],
        extensions: tuple[str, ...],
        *,
        recursive: bool,
    ) -> tuple[DiscoveredFile, ...] | ExecutionIssue: ...


class Action(Protocol):
    @property
    def label(self) -> str: ...

    @property
    def tags(self) -> tuple[str, ...]: ...

    @property
    def metadata(self) -> tuple[str, ...]: ...

    @property
    def valid_last(self) -> bool: ...

    def is_enabled(self) -> bool: ...

    def is_overwrite_existing_images_forced(self) -> bool: ...


class ActionRegistry(Protocol):
    def labels(self) -> tuple[str, ...]: ...

    def create(self, label: str) -> Action | ExecutionIssue: ...


class ActionDependencies(Protocol):
    def begin_run(self, options: ExecutionOptions) -> ActionRun: ...


class ActionRun(Protocol):
    """Per-run action adapter whose implementation privately owns its cache."""

    def required_variables(self, actions: tuple[Action, ...]) -> tuple[str, ...]: ...

    def safety_issue(self, actions: tuple[Action, ...]) -> ExecutionIssue | None: ...

    def initialize(self, action: Action) -> ExecutionIssue | None: ...

    def is_done(self, action: Action, photo: Photo) -> bool: ...

    def apply(self, action: Action, photo: Photo) -> ActionApplication: ...


class Photo(Protocol):
    @property
    def source(self) -> DiscoveredFile: ...

    def set_position(self, position: ExecutionPosition) -> None: ...

    def prepare_repeat_image(self, repeat_index: int, repeat_count: int) -> None: ...

    def reports(self) -> tuple[ReportFile, ...]: ...

    def set_output_transaction(
        self, transaction: DeferredOutputTransaction
    ) -> None: ...

    def close(self) -> None: ...


class PhotoAccess(Protocol):
    def verify(self, source: DiscoveredFile) -> bool: ...

    def open(
        self,
        source: DiscoveredFile,
        required_variables: tuple[str, ...],
    ) -> Photo | ExecutionIssue: ...


class Recovery(Protocol):
    def completed_reports(
        self, source: Path
    ) -> tuple[ReportFile, ...] | RecoveryReevaluation | None: ...

    def begin(self, source: Path) -> RecoveryAttempt: ...


class RecoveryAttempt(Protocol):
    @property
    def transaction(self) -> DeferredOutputTransaction: ...

    def finish(
        self,
        reports: tuple[ReportFile, ...],
        issues: tuple[ExecutionIssue, ...],
    ) -> None: ...

    def fail(self, issues: tuple[ExecutionIssue, ...]) -> None: ...

    def abort(self) -> None: ...
