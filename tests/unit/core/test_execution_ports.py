from __future__ import annotations

from pathlib import Path

from phatch.core.execution_ports import (
    Action,
    ActionDependencies,
    ActionRegistry,
    ActionRun,
    Clock,
    ExecutionInteraction,
    ExecutionProgress,
    IssueRecorder,
    Photo,
    PhotoAccess,
    UpdateCallback,
)
from phatch.core.execution_types import (
    DiscoveredFile,
    ExecutionIssue,
    ExecutionOptions,
    ExecutionPosition,
    ExecutionRequest,
    ExecutionSelection,
    IssueSeverity,
    IssueStage,
)
from tests.unit.core.execution_fakes import (
    ActionDependenciesFake,
    ActionFake,
    ActionRegistryFake,
    ActionRunFake,
    ClockFake,
    ExecutionInteractionFake,
    ExecutionProgressFake,
    IssueRecorderFake,
    PhotoAccessFake,
    PhotoFake,
    UpdateCallbackFake,
)


def test_typed_fakes_satisfy_focused_protocols() -> None:
    source = DiscoveredFile(Path("source.jpg"))
    options = ExecutionOptions(("jpg",))
    action: Action = ActionFake()
    photo: Photo = PhotoFake(source)
    action_run: ActionRun = ActionRunFake()
    dependencies: ActionDependencies = ActionDependenciesFake()
    registry: ActionRegistry = ActionRegistryFake(action)
    update: UpdateCallback = UpdateCallbackFake()
    clock: Clock = ClockFake()
    recorder: IssueRecorder = IssueRecorderFake()
    selection = ExecutionSelection((source.path,), options)
    interaction: ExecutionInteraction = ExecutionInteractionFake(selection)
    progress: ExecutionProgress = ExecutionProgressFake()
    photo_access: PhotoAccess = PhotoAccessFake(photo)
    request = ExecutionRequest((action,), options)
    position = ExecutionPosition(0, 0, 0)
    issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.WARNING,
        "warning",
    )

    update()
    recorder.begin()
    recorder.record(issue, 0)
    progress.start(1, 2)

    assert clock.monotonic() == 1.5
    assert registry.labels() == ("action",)
    assert registry.create("action") is action
    assert dependencies.begin_run(options) is not dependencies.begin_run(options)
    assert action_run.required_variables((action,)) == ("action",)
    assert action_run.safety_issue((action,)) is None
    assert action_run.initialize(action) is None
    assert action_run.is_done(action, photo) is False
    assert action_run.apply(action, photo).succeeded is True
    assert interaction.select_execution(request) == selection
    assert interaction.confirm_invalid_files((source,)) is True
    assert interaction.confirm_valid_files((source,)) is True
    assert interaction.decide_issue(issue, can_continue=True).prompt_on_future_issues
    assert progress.file_started(source, position).value == "continue"
    assert progress.action_started(position, 0).value == "continue"
    assert photo_access.verify(source) is True
    assert photo_access.open(source, ()) is photo

    interaction.present_issue(issue)
    interaction.request_save_action((action,))
    recorder.close()
    progress.close()


def test_protocols_are_not_runtime_checkable() -> None:
    protocols = (
        UpdateCallback,
        Clock,
        IssueRecorder,
        ExecutionInteraction,
        ExecutionProgress,
        Action,
        ActionRegistry,
        ActionDependencies,
        ActionRun,
        Photo,
        PhotoAccess,
    )

    assert all(
        vars(protocol).get("_is_runtime_protocol") is not True for protocol in protocols
    )
