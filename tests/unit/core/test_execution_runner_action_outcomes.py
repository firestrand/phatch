from pathlib import Path

import pytest

from phatch.core.execution_types import (
    ActionApplication,
    CancellationState,
    DiscoveredFile,
    ExecutionContext,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOutcome,
    FileOutcome,
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
)
from tests.unit.core.execution_runner_test_support import (
    FailFirstActionRun,
    RepeatPhotoFake,
    runner_parts,
)


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
    assert context.files[0].outcome is FileOutcome.FAILED
    assert context.files[0].issues == (issue,)
    assert context.issues == [issue]
    assert recorder.records == [(issue, 0)]


@pytest.mark.parametrize(
    "decision",
    [ExecutionDecision.CONTINUE, ExecutionDecision.SKIP],
)
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
    assert context.files[0].outcome is FileOutcome.CANCELLED
    assert context.files[0].cancellation is CancellationState.REQUESTED


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
    assert context.files[0].outcome is FileOutcome.PROCESSED


def test_cancellation_terminalizes_active_and_remaining_sources() -> None:
    sources = tuple(DiscoveredFile(Path(name)) for name in ("active.png", "queued.png"))
    runner, context, plan, _, progress, _, _ = runner_parts(sources[0])
    progress.file_decision = ProgressDecision.CANCEL
    plan = ExecutionPlan(plan.actions, sources, (), 1, False, None)

    outcome = runner.run(context, plan)

    assert outcome is ExecutionOutcome.CANCELLED
    assert [result.source for result in context.files] == [
        source.path for source in sources
    ]
    assert [result.outcome for result in context.files] == [
        FileOutcome.CANCELLED,
        FileOutcome.CANCELLED,
    ]


def test_action_failure_abort_preserves_failure_and_cancels_remaining() -> None:
    sources = tuple(DiscoveredFile(Path(name)) for name in ("failed.png", "queued.png"))
    action_run = ActionRunFake()
    runner, context, plan, interaction, _, _, photo = runner_parts(
        sources[0], action_run
    )
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.ERROR,
        "failed before cancellation",
        sources[0].path,
    )
    action_run.next_application = ActionApplication(photo, False, (issue,))
    interaction.response = IssueResponse(ExecutionDecision.ABORT, True)
    plan = ExecutionPlan(plan.actions, sources, (), 1, False, None)

    assert runner.run(context, plan) is ExecutionOutcome.CANCELLED
    assert [result.outcome for result in context.files] == [
        FileOutcome.FAILED,
        FileOutcome.CANCELLED,
    ]
    assert all(
        result.cancellation is CancellationState.REQUESTED for result in context.files
    )
