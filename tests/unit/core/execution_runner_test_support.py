from pathlib import Path

from phatch.core.execution_ports import Action, Photo, RecoveryAttempt
from phatch.core.execution_types import (
    ActionApplication,
    DiscoveredFile,
    ExecutionContext,
    ExecutionIssue,
    IssueResponse,
    OutputRecord,
    ReportFile,
)
from phatch.services.execution_runner import (
    ExecutionPlan,
    ExecutionRunner,
    RunnerServices,
)
from phatch.services.output_transaction import DeferredOutputTransaction
from phatch.services.recovery_outcomes import (
    RecoveryFinishResult,
    RecoveryFinishSucceeded,
)
from tests.unit.core.execution_fakes import (
    ActionFake,
    ActionRunFake,
    ExecutionInteractionFake,
    ExecutionProgressFake,
    IssueRecorderFake,
    PhotoAccessFake,
    PhotoFake,
)


class OpenIssuePhotoAccess:
    def __init__(self, issue: ExecutionIssue) -> None:
        self.issue = issue

    def verify(self, source: DiscoveredFile) -> bool:
        return True

    def open(
        self,
        source: DiscoveredFile,
        required_variables: tuple[str, ...],
    ) -> ExecutionIssue:
        return self.issue


class DoneActionRunFake(ActionRunFake):
    def is_done(self, action: Action, photo: Photo) -> bool:
        return True


class FailFirstActionRun(ActionRunFake):
    def __init__(self, issue: ExecutionIssue) -> None:
        super().__init__()
        self.issue = issue

    def apply(self, action: Action, photo: Photo) -> ActionApplication:
        self.applied_labels.append(action.label)
        if len(self.applied_labels) == 1:
            return ActionApplication(photo, False, (self.issue,))
        return ActionApplication(photo, True)


class RepeatPhotoFake(PhotoFake):
    __slots__ = ("repeats",)

    def __init__(self, source: DiscoveredFile) -> None:
        super().__init__(source)
        self.repeats: list[tuple[int, int]] = []

    def prepare_repeat_image(self, repeat_index: int, repeat_count: int) -> None:
        self.repeats.append((repeat_index, repeat_count))


class CountingInteraction(ExecutionInteractionFake):
    __slots__ = ("decisions",)

    def __init__(self) -> None:
        super().__init__(selection=None)
        self.decisions = 0

    def decide_issue(self, issue: ExecutionIssue, can_continue: bool) -> IssueResponse:
        self.decisions += 1
        return self.response


class CompletedRecovery:
    def __init__(self, reports: tuple[ReportFile, ...]) -> None:
        self.reports = reports

    def completed_reports(self, source: Path) -> tuple[ReportFile, ...]:
        del source
        return self.reports

    def begin(self, source: Path):
        del source
        raise AssertionError("completed recovery must not begin a new attempt")


class RecordingAttempt:
    def __init__(self) -> None:
        self.transaction = DeferredOutputTransaction()
        self.failed: tuple[ExecutionIssue, ...] = ()
        self.finished = False
        self.aborted = False

    def finish(
        self,
        reports: tuple[ReportFile, ...],
        issues: tuple[ExecutionIssue, ...],
    ) -> RecoveryFinishResult:
        del issues
        self.finished = True
        return RecoveryFinishSucceeded(
            tuple(OutputRecord(report) for report in reports)
        )

    def fail(self, issues: tuple[ExecutionIssue, ...]) -> None:
        self.failed = issues

    def abort(self) -> None:
        self.aborted = True


class RecordingRecovery:
    def __init__(self, attempt: RecordingAttempt) -> None:
        self.attempt = attempt

    def completed_reports(self, source: Path):
        del source
        return None

    def begin(self, source: Path) -> RecoveryAttempt:
        del source
        return self.attempt


def runner_parts(
    source: DiscoveredFile,
    action_run: ActionRunFake | None = None,
) -> tuple[
    ExecutionRunner,
    ExecutionContext,
    ExecutionPlan,
    ExecutionInteractionFake,
    ExecutionProgressFake,
    IssueRecorderFake,
    PhotoFake,
]:
    interaction = ExecutionInteractionFake(selection=None)
    progress = ExecutionProgressFake()
    recorder = IssueRecorderFake()
    photo = PhotoFake(source)
    runner = ExecutionRunner(
        RunnerServices(interaction, progress, PhotoAccessFake(photo), recorder)
    )
    context = ExecutionContext(action_run or ActionRunFake(), True)
    plan = ExecutionPlan(
        (ActionFake(),),
        (source,),
        (),
        1,
        False,
        None,
    )
    return runner, context, plan, interaction, progress, recorder, photo
