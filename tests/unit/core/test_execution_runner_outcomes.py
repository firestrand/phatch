from __future__ import annotations

from pathlib import Path

import pytest

from phatch.core.execution_types import (
    CancellationState,
    DiscoveredFile,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOutcome,
    FileOutcome,
    IssueResponse,
    IssueSeverity,
    IssueStage,
    ReportFile,
)
from phatch.services.execution_runner import (
    ExecutionPlan,
    ExecutionRunner,
    RunnerServices,
)
from tests.unit.core.execution_fakes import (
    UpdateCallbackFake,
)
from tests.unit.core.execution_runner_test_support import (
    CompletedRecovery,
    CountingInteraction,
    DoneActionRunFake,
    OpenIssuePhotoAccess,
    RecordingAttempt,
    RecordingRecovery,
    runner_parts,
)


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
    assert context.files[0].outcome is FileOutcome.FAILED
    expected_cancellation = (
        CancellationState.REQUESTED
        if decision is ExecutionDecision.ABORT
        else CancellationState.NOT_REQUESTED
    )
    assert context.files[0].cancellation is expected_cancellation


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


def test_open_issue_fails_active_recovery_attempt() -> None:
    source = DiscoveredFile(Path("input.png"))
    issue = ExecutionIssue(IssueStage.PHOTO_OPEN, IssueSeverity.ERROR, "open failed")
    runner, context, plan, interaction, progress, recorder, _ = runner_parts(source)
    interaction.response = IssueResponse(ExecutionDecision.CONTINUE, False)
    attempt = RecordingAttempt()
    runner = ExecutionRunner(
        RunnerServices(interaction, progress, OpenIssuePhotoAccess(issue), recorder)
    )
    plan = ExecutionPlan(
        plan.actions,
        plan.sources,
        (),
        1,
        False,
        None,
        RecordingRecovery(attempt),
    )

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert attempt.failed == (issue,)


def test_completed_recovery_skips_photo_and_invokes_update() -> None:
    source = DiscoveredFile(Path("input.png"))
    runner, context, plan, _, _, _, _ = runner_parts(source)
    update = UpdateCallbackFake()
    recovery = CompletedRecovery((ReportFile(source.path, Path("output.png")),))
    plan = ExecutionPlan(plan.actions, plan.sources, (), 1, False, update, recovery)

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert context.files[0].outcome is FileOutcome.SKIPPED
    assert update.calls == 1


def test_successful_photo_invokes_update() -> None:
    source = DiscoveredFile(Path("input.png"))
    runner, context, plan, _, _, _, _ = runner_parts(source)
    update = UpdateCallbackFake()
    plan = ExecutionPlan(plan.actions, plan.sources, (), 1, False, update)

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert update.calls == 1


def test_successful_photo_finishes_recovery_attempt() -> None:
    source = DiscoveredFile(Path("input.png"))
    runner, context, plan, _, _, _, _ = runner_parts(source)
    attempt = RecordingAttempt()
    plan = ExecutionPlan(
        plan.actions,
        plan.sources,
        (),
        1,
        False,
        None,
        RecordingRecovery(attempt),
    )

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert attempt.finished
    assert not attempt.aborted


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
    assert [result.outcome for result in context.files] == [
        FileOutcome.FAILED,
        FileOutcome.FAILED,
    ]


def test_skip_existing_avoids_action_application() -> None:
    source = DiscoveredFile(Path("input.png"))
    action_run = DoneActionRunFake()
    runner, context, plan, _, _, _, _ = runner_parts(source, action_run)
    plan = ExecutionPlan(plan.actions, plan.sources, (), 1, True, None)

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert action_run.applied_labels == []
    assert context.files[0].outcome is FileOutcome.SKIPPED
