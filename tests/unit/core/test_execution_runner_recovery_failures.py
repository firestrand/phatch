from dataclasses import replace
from pathlib import Path

import pytest

from phatch.core.execution_types import (
    ActionApplication,
    CancellationState,
    DiscoveredFile,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOutcome,
    FileOutcome,
    IssueResponse,
    IssueSeverity,
    IssueStage,
    OutputRecord,
    ProgressDecision,
    ReportFile,
    RollbackState,
)
from phatch.services.execution_recovery_boundary import (
    MissingRecoveryAttemptError,
    SourceRecoveryBoundary,
)
from phatch.services.execution_runner import ExecutionPlan
from phatch.services.recovery_outcomes import RecoveryFinishFailed
from tests.unit.core.execution_fakes import ActionRunFake
from tests.unit.core.test_execution_runner_outcomes import (
    RecordingAttempt,
    RecordingRecovery,
    runner_parts,
)


class FinishOSErrorAttempt(RecordingAttempt):
    def finish(
        self,
        reports: tuple[ReportFile, ...],
        issues: tuple[ExecutionIssue, ...],
    ) -> RecoveryFinishFailed:
        del issues
        return RecoveryFinishFailed(
            OSError("recovery publication failed"),
            tuple(OutputRecord(report, survived=False) for report in reports),
            RollbackState.COMPLETED,
        )


class MethodFailureAttempt(RecordingAttempt):
    def __init__(self, method: str) -> None:
        super().__init__()
        self.method = method

    def fail(self, issues: tuple[ExecutionIssue, ...]) -> None:
        if self.method == "fail":
            raise OSError("fail journal write")
        super().fail(issues)

    def abort(self) -> None:
        if self.method == "abort":
            raise OSError("abort discard")
        super().abort()


class ReadFailureRecovery(RecordingRecovery):
    def completed_reports(self, source: Path):
        del source
        raise OSError("journal read")


class BeginFailureRecovery(RecordingRecovery):
    def begin(self, source: Path):
        del source
        raise KeyboardInterrupt


def test_finish_requires_active_recovery_attempt() -> None:
    with pytest.raises(MissingRecoveryAttemptError):
        SourceRecoveryBoundary(Path("active.png")).finish(())


def test_finish_oserror_closes_photo_and_terminalizes_every_source() -> None:
    sources = tuple(DiscoveredFile(Path(name)) for name in ("active.png", "queued.png"))
    runner, context, plan, interaction, _, recorder, photo = runner_parts(sources[0])
    report = ReportFile(sources[0].path, Path("output.png"))
    photo._reports = (report,)
    interaction.response = IssueResponse(ExecutionDecision.ABORT, True)
    attempt = FinishOSErrorAttempt()
    plan = ExecutionPlan(
        plan.actions,
        sources,
        plan.required_variables,
        plan.repeat,
        plan.skip_existing,
        plan.update,
        RecordingRecovery(attempt),
    )

    outcome = runner.run(context, plan)

    assert outcome is ExecutionOutcome.CANCELLED
    assert photo.closed is True
    assert [result.source for result in context.files] == [
        source.path for source in sources
    ]
    assert [result.outcome for result in context.files] == [
        FileOutcome.FAILED,
        FileOutcome.CANCELLED,
    ]
    active = context.files[0]
    assert active.cancellation is CancellationState.REQUESTED
    assert active.rollback is RollbackState.COMPLETED
    assert active.outputs[0].survived is False
    assert active.issues[0].stage is IssueStage.RECOVERY
    assert active.issues[0].severity is IssueSeverity.ERROR
    assert context.issues == list(active.issues)
    assert recorder.records == [(active.issues[0], 0)]


def test_finish_failure_normalizes_output_source_to_planned_alias(
    tmp_path: Path,
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    source = DiscoveredFile(alias / "source.png")
    runner, context, plan, _, _, _, photo = runner_parts(source)
    photo._reports = (ReportFile(source.path.resolve(), real / "output.png"),)
    attempt = FinishOSErrorAttempt()
    updates: list[None] = []
    plan = ExecutionPlan(
        plan.actions,
        plan.sources,
        plan.required_variables,
        plan.repeat,
        plan.skip_existing,
        lambda: updates.append(None),
        RecordingRecovery(attempt),
    )

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert context.files[0].outputs[0].report.source == source.path
    assert updates == [None]


def test_completed_report_read_failure_terminalizes_current_and_queued() -> None:
    sources = tuple(DiscoveredFile(Path(name)) for name in ("active.png", "queued.png"))
    runner, context, plan, interaction, _, _, _ = runner_parts(sources[0])
    interaction.response = IssueResponse(ExecutionDecision.ABORT, True)
    plan = replace(
        plan, sources=sources, recovery=ReadFailureRecovery(RecordingAttempt())
    )

    assert runner.run(context, plan) is ExecutionOutcome.CANCELLED
    assert [result.outcome for result in context.files] == [
        FileOutcome.FAILED,
        FileOutcome.CANCELLED,
    ]


def test_begin_interrupt_terminalizes_current_and_queued() -> None:
    sources = tuple(DiscoveredFile(Path(name)) for name in ("active.png", "queued.png"))
    runner, context, plan, _, _, _, _ = runner_parts(sources[0])
    plan = replace(
        plan, sources=sources, recovery=BeginFailureRecovery(RecordingAttempt())
    )

    assert runner.run(context, plan) is ExecutionOutcome.CANCELLED
    assert len(context.files) == 2


def test_fail_journal_error_preserves_action_issue_and_closes_photo() -> None:
    source = DiscoveredFile(Path("active.png"))
    action_run = ActionRunFake()
    runner, context, plan, _, _, _, photo = runner_parts(source, action_run)
    issue = ExecutionIssue(IssueStage.ACTION_EXECUTION, IssueSeverity.ERROR, "action")
    action_run.next_application = ActionApplication(photo, False, (issue,))
    plan = replace(plan, recovery=RecordingRecovery(MethodFailureAttempt("fail")))

    assert runner.run(context, plan) is ExecutionOutcome.COMPLETED
    assert photo.closed is True
    assert [item.message for item in context.files[0].issues] == [
        "action",
        "fail journal write",
    ]


def test_abort_and_close_errors_become_recovery_issues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = DiscoveredFile(Path("active.png"))
    runner, context, plan, _, progress, _, photo = runner_parts(source)
    progress.file_decision = ProgressDecision.CANCEL
    monkeypatch.setattr(
        type(photo),
        "close",
        lambda _photo: (_ for _ in ()).throw(OSError("photo close")),
    )
    plan = replace(plan, recovery=RecordingRecovery(MethodFailureAttempt("abort")))

    assert runner.run(context, plan) is ExecutionOutcome.CANCELLED
    assert [issue.message for issue in context.files[0].issues] == [
        "abort discard",
        "photo close",
    ]
