from __future__ import annotations

from pathlib import Path

from phatch.core.execution_types import (
    ActionApplication,
    DiscoveredFile,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOptions,
    ExecutionOutcome,
    ExecutionRequest,
    ExecutionSelection,
    IssueResponse,
    IssueSeverity,
    IssueStage,
    ProgressDecision,
    ReportFile,
)
from phatch.services.execution import (
    ExecutionService,
    ExecutionServices,
    TypedExecutionValidator,
)
from phatch.services.execution_runner import ExecutionRunner, RunnerServices
from tests.unit.core.execution_fakes import (
    ActionDependenciesFake,
    ActionFake,
    ClockFake,
    ExecutionInteractionFake,
    ExecutionProgressFake,
    IssueRecorderFake,
    PhotoAccessFake,
    PhotoFake,
    UpdateCallbackFake,
)


class DiscoveryFake:
    def __init__(self, result: tuple[DiscoveredFile, ...] | ExecutionIssue) -> None:
        self.result = result
        self.calls: list[tuple[tuple[Path, ...], tuple[str, ...], bool]] = []

    def discover(
        self,
        paths: tuple[Path, ...],
        extensions: tuple[str, ...],
        *,
        recursive: bool,
    ) -> tuple[DiscoveredFile, ...] | ExecutionIssue:
        self.calls.append((paths, extensions, recursive))
        return self.result


def make_service(
    source: DiscoveredFile,
    discovery_result: tuple[DiscoveredFile, ...] | ExecutionIssue | None = None,
) -> tuple[
    ExecutionService,
    ActionDependenciesFake,
    ExecutionInteractionFake,
    ExecutionProgressFake,
    IssueRecorderFake,
    PhotoAccessFake,
]:
    options = ExecutionOptions(
        ("png",),
        verify_images=False,
        require_save_action=False,
    )
    interaction = ExecutionInteractionFake(ExecutionSelection((source.path,), options))
    dependencies = ActionDependenciesFake()
    progress = ExecutionProgressFake()
    recorder = IssueRecorderFake()
    photo_access = PhotoAccessFake(PhotoFake(source))
    service = ExecutionService(
        ExecutionServices(
            discovery=DiscoveryFake(
                (source,) if discovery_result is None else discovery_result
            ),
            dependencies=dependencies,
            interaction=interaction,
            progress=progress,
            photo_access=photo_access,
            issue_recorder=recorder,
            clock=ClockFake(),
            runner=ExecutionRunner(
                RunnerServices(
                    interaction=interaction,
                    progress=progress,
                    photo_access=photo_access,
                    issue_recorder=recorder,
                )
            ),
            validator=TypedExecutionValidator(),
        )
    )
    return service, dependencies, interaction, progress, recorder, photo_access


def test_execute_runs_repeats_with_run_local_state_and_reports() -> None:
    source = DiscoveredFile(Path("input.png"))
    report = ReportFile(source.path, Path("output.png"), 2, 3, "RGB")
    service, dependencies, interaction, progress, recorder, photo_access = make_service(
        source
    )
    photo_access.photo = PhotoFake(source, (report,))
    update = UpdateCallbackFake()
    options = ExecutionOptions(
        ("png",),
        verify_images=False,
        require_save_action=False,
        repeat=2,
    )
    interaction.selection = ExecutionSelection((source.path,), options)

    result = service.execute(
        ExecutionRequest(
            (ActionFake("resize"),), options, (source.path,), update=update
        )
    )

    assert result.outcome is ExecutionOutcome.COMPLETED
    assert result.report == (report,)
    assert result.files[0].decision is ExecutionDecision.CONTINUE
    assert len(dependencies.runs) == 1
    assert dependencies.runs[0].applied_labels == ["resize", "resize"]
    assert progress.started == (2, 2)
    assert progress.closed is True
    assert recorder.started is True
    assert recorder.closed is True
    assert update.calls == 2


def test_execute_maps_discovery_failure_without_starting_progress() -> None:
    source = DiscoveredFile(Path("missing.png"))
    issue = ExecutionIssue(
        IssueStage.FILE_DISCOVERY,
        IssueSeverity.ERROR,
        "missing input",
        source.path,
    )
    service, _dependencies, _interaction, progress, recorder, _photo_access = (
        make_service(source, issue)
    )
    result = service.execute(
        ExecutionRequest(
            (ActionFake(),),
            ExecutionOptions(
                ("png",),
                verify_images=False,
                require_save_action=False,
            ),
            (source.path,),
        )
    )

    assert result.outcome is ExecutionOutcome.FAILED
    assert result.issues == (issue,)
    assert progress.started is None
    assert recorder.records == [(issue, 0)]


def test_execute_aborts_on_action_failure_and_closes_photo() -> None:
    source = DiscoveredFile(Path("input.png"))
    service, dependencies, interaction, progress, recorder, photo_access = make_service(
        source
    )
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.ERROR,
        "action failed",
        source.path,
        "resize",
    )
    dependencies.next_application = ActionApplication(
        photo_access.photo,
        succeeded=False,
        issues=(issue,),
    )
    interaction.response = IssueResponse(ExecutionDecision.ABORT, True)

    result = service.execute(
        ExecutionRequest(
            (ActionFake("resize"),),
            ExecutionOptions(
                ("png",),
                verify_images=False,
                require_save_action=False,
            ),
            (source.path,),
        )
    )

    assert result.outcome is ExecutionOutcome.CANCELLED
    assert result.issues == (issue,)
    assert isinstance(photo_access.photo, PhotoFake)
    assert photo_access.photo.closed is True
    assert progress.closed is True
    assert recorder.records == [(issue, 0)]


def test_execute_cancellation_suppresses_updates() -> None:
    source = DiscoveredFile(Path("input.png"))
    service, _dependencies, _interaction, progress, _recorder, photo_access = (
        make_service(source)
    )
    progress.file_decision = ProgressDecision.CANCEL
    update = UpdateCallbackFake()

    result = service.execute(
        ExecutionRequest(
            (ActionFake(),),
            ExecutionOptions(
                ("png",),
                verify_images=False,
                require_save_action=False,
            ),
            (source.path,),
            update=update,
        )
    )

    assert result.outcome is ExecutionOutcome.CANCELLED
    assert isinstance(photo_access.photo, PhotoFake)
    assert photo_access.photo.closed is True
    assert update.calls == 0
