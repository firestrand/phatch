from __future__ import annotations

from pathlib import Path

import pytest

from phatch.core.execution_ports import Action, Photo
from phatch.core.execution_types import (
    ActionApplication,
    DiscoveredFile,
    ExecutionContext,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOutcome,
    IssueResponse,
    IssueSeverity,
    IssueStage,
    ProgressDecision,
)
from phatch.services.execution_runner import (
    ExecutionPlan,
    ExecutionRunner,
    RunnerServices,
)
from tests.unit.core.execution_fakes import (
    ActionFake,
    ActionRunFake,
    ExecutionInteractionFake,
    ExecutionProgressFake,
    IssueRecorderFake,
    PhotoAccessFake,
    PhotoFake,
    UpdateCallbackFake,
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


@pytest.mark.parametrize(
    ("decision", "outcome"),
    [
        (ExecutionDecision.CONTINUE, ExecutionOutcome.COMPLETED),
        (ExecutionDecision.ABORT, ExecutionOutcome.CANCELLED),
    ],
)
def test_open_issue_maps_decision(decision, outcome) -> None:
    source = DiscoveredFile(Path("input.png"))
    issue = ExecutionIssue(
        IssueStage.PHOTO_OPEN,
        IssueSeverity.ERROR,
        "open failed",
        source.path,
    )
    runner, context, plan, interaction, progress, recorder, _ = runner_parts(source)
    interaction.response = IssueResponse(decision, False)
    runner = ExecutionRunner(
        RunnerServices(interaction, progress, OpenIssuePhotoAccess(issue), recorder)
    )

    result = runner.run(context, plan)

    assert result is outcome
    assert context.issues == [issue]
    assert recorder.records == [(issue, 0)]
    if decision is ExecutionDecision.CONTINUE:
        assert context.files[0].decision is ExecutionDecision.SKIP


def test_open_issue_skip_invokes_update() -> None:
    source = DiscoveredFile(Path("input.png"))
    issue = ExecutionIssue(
        IssueStage.PHOTO_OPEN,
        IssueSeverity.ERROR,
        "open failed",
    )
    runner, context, plan, interaction, progress, recorder, _ = runner_parts(source)
    update = UpdateCallbackFake()
    plan = ExecutionPlan(plan.actions, plan.sources, (), 1, False, update)
    runner = ExecutionRunner(
        RunnerServices(interaction, progress, OpenIssuePhotoAccess(issue), recorder)
    )

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert update.calls == 1


def test_open_issue_reuses_remembered_decision_without_prompting_again() -> None:
    sources = (DiscoveredFile(Path("first.png")), DiscoveredFile(Path("second.png")))
    issue = ExecutionIssue(
        IssueStage.PHOTO_OPEN,
        IssueSeverity.ERROR,
        "open failed",
    )
    runner, context, plan, _, progress, recorder, _ = runner_parts(sources[0])
    interaction = CountingInteraction()
    interaction.response = IssueResponse(ExecutionDecision.CONTINUE, False)
    runner = ExecutionRunner(
        RunnerServices(interaction, progress, OpenIssuePhotoAccess(issue), recorder)
    )
    plan = ExecutionPlan(
        plan.actions,
        sources,
        plan.required_variables,
        plan.repeat,
        plan.skip_existing,
        plan.update,
    )

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert interaction.decisions == 1
    assert context.remembered_decision is ExecutionDecision.CONTINUE
    assert [result.decision for result in context.files] == [
        ExecutionDecision.SKIP,
        ExecutionDecision.SKIP,
    ]


def test_skip_existing_avoids_action_application() -> None:
    source = DiscoveredFile(Path("input.png"))
    action_run = DoneActionRunFake()
    runner, context, plan, _, _, _, _ = runner_parts(source, action_run)
    plan = ExecutionPlan(plan.actions, plan.sources, (), 1, True, None)

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert action_run.applied_labels == []


def test_action_progress_cancellation_closes_photo() -> None:
    source = DiscoveredFile(Path("input.png"))
    runner, context, plan, _, progress, _, photo = runner_parts(source)
    progress.action_decision = ProgressDecision.CANCEL

    assert runner.run(context, plan) is ExecutionOutcome.CANCELLED
    assert photo.closed is True


def test_failed_action_can_continue_to_file_result() -> None:
    source = DiscoveredFile(Path("input.png"))
    action_run = ActionRunFake()
    runner, context, plan, interaction, _, recorder, photo = runner_parts(
        source, action_run
    )
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.ERROR,
        "failed",
    )
    action_run.next_application = ActionApplication(
        photo,
        succeeded=False,
        issues=(issue,),
    )
    interaction.response = IssueResponse(ExecutionDecision.CONTINUE, False)

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert context.files[0].decision is ExecutionDecision.CONTINUE
    assert context.issues == [issue]
    assert recorder.records == [(issue, 0)]


@pytest.mark.parametrize("decision", [ExecutionDecision.CONTINUE, ExecutionDecision.SKIP])
def test_action_failure_continue_runs_the_next_action(
    decision: ExecutionDecision,
) -> None:
    source = DiscoveredFile(Path("input.png"))
    issue = ExecutionIssue(IssueStage.ACTION_EXECUTION, IssueSeverity.ERROR, "failed")
    action_run = FailFirstActionRun(issue)
    runner, context, plan, interaction, _, _, _ = runner_parts(source, action_run)
    interaction.response = IssueResponse(decision, True)
    plan = ExecutionPlan(
        (ActionFake("first"), ActionFake("second")), plan.sources, (), 1, False, None
    )

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert action_run.applied_labels == ["first", "second"]


@pytest.mark.parametrize("checkpoint", ["file", "action"])
def test_cancellation_checkpoint_closes_photo_without_report(
    checkpoint: str,
) -> None:
    source = DiscoveredFile(Path("input.png"))
    runner, context, plan, _, progress, _, photo = runner_parts(source)
    if checkpoint == "file":
        progress.file_decision = ProgressDecision.CANCEL
    else:
        progress.action_decision = ProgressDecision.CANCEL

    assert runner.run(context, plan) is ExecutionOutcome.CANCELLED
    assert photo.closed is True
    assert context.files == []


def test_repeats_prepare_each_image_before_action_application() -> None:
    source = DiscoveredFile(Path("input.png"))
    photo = RepeatPhotoFake(source)
    action_run = ActionRunFake()
    interaction = ExecutionInteractionFake(selection=None)
    progress = ExecutionProgressFake()
    runner = ExecutionRunner(
        RunnerServices(
            interaction, progress, PhotoAccessFake(photo), IssueRecorderFake()
        )
    )
    context = ExecutionContext(action_run, True)
    plan = ExecutionPlan((ActionFake(),), (source,), (), 3, False, None)

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert photo.repeats == [(0, 3), (1, 3), (2, 3)]
    assert action_run.applied_labels == ["action", "action", "action"]
