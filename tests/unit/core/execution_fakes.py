from __future__ import annotations

from phatch.core.execution_ports import Action, ActionRun, Photo
from phatch.core.execution_types import (
    ActionApplication,
    DiscoveredFile,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOptions,
    ExecutionPosition,
    ExecutionRequest,
    ExecutionSelection,
    IssueResponse,
    ProgressDecision,
    ReportFile,
)


class ActionFake:
    __slots__ = ("_label",)

    def __init__(self, label: str = "action") -> None:
        self._label = label

    @property
    def label(self) -> str:
        return self._label

    @property
    def tags(self) -> tuple[str, ...]:
        return ()

    @property
    def metadata(self) -> tuple[str, ...]:
        return ()

    @property
    def valid_last(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True

    def is_overwrite_existing_images_forced(self) -> bool:
        return False


class PhotoFake:
    __slots__ = ("_reports", "_source", "closed", "position", "repeat")

    def __init__(
        self,
        source: DiscoveredFile,
        reports: tuple[ReportFile, ...] = (),
    ) -> None:
        self._source = source
        self._reports = reports
        self.position: ExecutionPosition | None = None
        self.repeat: tuple[int, int] | None = None
        self.closed = False

    @property
    def source(self) -> DiscoveredFile:
        return self._source

    def set_position(self, position: ExecutionPosition) -> None:
        self.position = position

    def prepare_repeat_image(self, repeat_index: int, repeat_count: int) -> None:
        self.repeat = (repeat_index, repeat_count)

    def reports(self) -> tuple[ReportFile, ...]:
        return self._reports

    def set_output_transaction(self, transaction) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class ActionRunFake:
    __slots__ = ("applied_labels", "next_application")

    def __init__(self) -> None:
        self.applied_labels: list[str] = []
        self.next_application: ActionApplication | None = None

    def required_variables(self, actions: tuple[Action, ...]) -> tuple[str, ...]:
        return tuple(action.label for action in actions)

    def safety_issue(self, actions: tuple[Action, ...]) -> ExecutionIssue | None:
        return None

    def initialize(self, action: Action) -> ExecutionIssue | None:
        return None

    def is_done(self, action: Action, photo: Photo) -> bool:
        return False

    def apply(self, action: Action, photo: Photo) -> ActionApplication:
        self.applied_labels.append(action.label)
        if self.next_application is not None:
            return self.next_application
        return ActionApplication(photo=photo, succeeded=True)


class ActionDependenciesFake:
    __slots__ = ("next_application", "runs")

    def __init__(self) -> None:
        self.runs: list[ActionRunFake] = []
        self.next_application: ActionApplication | None = None

    def begin_run(self, options: ExecutionOptions) -> ActionRun:
        run = ActionRunFake()
        run.next_application = self.next_application
        self.runs.append(run)
        return run


class ActionRegistryFake:
    __slots__ = ("action",)

    def __init__(self, action: Action) -> None:
        self.action = action

    def labels(self) -> tuple[str, ...]:
        return (self.action.label,)

    def create(self, label: str) -> Action | ExecutionIssue:
        return self.action


class UpdateCallbackFake:
    __slots__ = ("calls",)

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


class ClockFake:
    __slots__ = ()

    def monotonic(self) -> float:
        return 1.5


class IssueRecorderFake:
    __slots__ = ("closed", "records", "started")

    def __init__(self) -> None:
        self.started = False
        self.records: list[tuple[ExecutionIssue, int]] = []
        self.closed = False

    def begin(self) -> None:
        self.started = True

    def record(self, issue: ExecutionIssue, sequence: int) -> None:
        self.records.append((issue, sequence))

    def close(self) -> None:
        self.closed = True


class ExecutionInteractionFake:
    __slots__ = ("confirm_invalid", "confirm_valid", "response", "selection")

    def __init__(self, selection: ExecutionSelection | None) -> None:
        self.selection: ExecutionSelection | None = selection
        self.response = IssueResponse(ExecutionDecision.CONTINUE, True)
        self.confirm_invalid = True
        self.confirm_valid = True

    def select_execution(self, request: ExecutionRequest) -> ExecutionSelection | None:
        return self.selection

    def present_issue(self, issue: ExecutionIssue) -> None:
        return None

    def request_save_action(self, actions: tuple[Action, ...]) -> None:
        return None

    def confirm_invalid_files(self, files: tuple[DiscoveredFile, ...]) -> bool:
        return self.confirm_invalid

    def confirm_valid_files(self, files: tuple[DiscoveredFile, ...]) -> bool:
        return self.confirm_valid

    def decide_issue(self, issue: ExecutionIssue, can_continue: bool) -> IssueResponse:
        return self.response


class ExecutionProgressFake:
    __slots__ = ("action_decision", "closed", "file_decision", "started")

    def __init__(self) -> None:
        self.started: tuple[int, int] | None = None
        self.closed = False
        self.file_decision = ProgressDecision.CONTINUE
        self.action_decision = ProgressDecision.CONTINUE

    def start(self, item_count: int, step_count: int) -> None:
        self.started = (item_count, step_count)

    def file_started(
        self, source: DiscoveredFile, position: ExecutionPosition
    ) -> ProgressDecision:
        return self.file_decision

    def action_started(
        self, position: ExecutionPosition, action_index: int
    ) -> ProgressDecision:
        return self.action_decision

    def close(self) -> None:
        self.closed = True


class PhotoAccessFake:
    __slots__ = ("photo",)

    def __init__(self, photo: Photo) -> None:
        self.photo = photo

    def verify(self, source: DiscoveredFile) -> bool:
        return True

    def open(
        self,
        source: DiscoveredFile,
        required_variables: tuple[str, ...],
    ) -> Photo | ExecutionIssue:
        return self.photo
