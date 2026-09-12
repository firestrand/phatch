from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from phatch.core.execution_ports import Action, ActionRun
from phatch.core.execution_types import (
    DiscoveredFile,
    ExecutionIssue,
    ExecutionOptions,
    ExecutionOutcome,
    ExecutionRequest,
    ExecutionSelection,
    IssueSeverity,
    IssueStage,
)
from phatch.services.action_validation import (
    ActionListRejectionReason,
    ActionListValidationResult,
    RejectedActionList,
    SaveActionRequired,
)
from phatch.services.execution import ExecutionService
from tests.unit.core.execution_fakes import ActionFake, ActionRunFake, PhotoFake
from tests.unit.core.test_execution_service import DiscoveryFake, make_service


class ValidatorFake:
    def __init__(self, result: ActionListValidationResult) -> None:
        self.result = result

    def validate(
        self,
        request: ExecutionRequest,
        action_run: ActionRun,
    ) -> ActionListValidationResult:
        return self.result


class InitializingRunFake(ActionRunFake):
    def __init__(self, issue: ExecutionIssue) -> None:
        super().__init__()
        self.issue = issue

    def initialize(self, action: Action) -> ExecutionIssue | None:
        return self.issue


class InitializingDependenciesFake:
    def __init__(self, run: ActionRun) -> None:
        self.run = run

    def begin_run(self, options: ExecutionOptions) -> ActionRun:
        return self.run


class InvalidPhotoAccessFake:
    def __init__(self, source: DiscoveredFile) -> None:
        self.photo = PhotoFake(source)

    def verify(self, source: DiscoveredFile) -> bool:
        return False

    def open(
        self,
        source: DiscoveredFile,
        required_variables: tuple[str, ...],
    ) -> PhotoFake:
        return self.photo


class RunnerFailure(RuntimeError):
    pass


class FailingRunner:
    def run(self, context, plan):
        raise RunnerFailure


def request(source: DiscoveredFile, *, verify: bool = False) -> ExecutionRequest:
    return ExecutionRequest(
        (ActionFake(),),
        ExecutionOptions(
            ("png",),
            verify_images=verify,
            require_save_action=False,
        ),
        (source.path,),
    )


@pytest.mark.parametrize(
    ("reason", "diagnostic"),
    [
        (ActionListRejectionReason.EMPTY, ""),
        (ActionListRejectionReason.UNSAFE, "unsafe"),
        (ActionListRejectionReason.ALL_DISABLED, ""),
    ],
)
def test_rejected_validation_returns_recorded_failure(reason, diagnostic) -> None:
    source = DiscoveredFile(Path("input.png"))
    service, _, _, progress, recorder, _ = make_service(source)
    service = ExecutionService(
        replace(
            service.services,
            validator=ValidatorFake(RejectedActionList(reason, diagnostic)),
        )
    )

    result = service.execute(request(source))

    assert result.outcome is ExecutionOutcome.FAILED
    assert len(result.issues) == 1
    assert recorder.records == [(result.issues[0], 0)]
    assert progress.started is None


def test_save_requirement_returns_failure_before_discovery() -> None:
    source = DiscoveredFile(Path("input.png"))
    action = ActionFake()
    service, _, _, progress, _, _ = make_service(source)
    service = ExecutionService(
        replace(
            service.services,
            validator=ValidatorFake(SaveActionRequired((action,))),
        )
    )

    result = service.execute(request(source))

    assert result.outcome is ExecutionOutcome.FAILED
    assert progress.started is None


def test_cancelled_selection_stops_before_discovery() -> None:
    source = DiscoveredFile(Path("input.png"))
    service, _, interaction, progress, _, _ = make_service(source)
    interaction.selection = None

    result = service.execute(request(source))

    assert result.outcome is ExecutionOutcome.CANCELLED
    assert progress.started is None


def test_empty_discovery_returns_recorded_failure() -> None:
    source = DiscoveredFile(Path("input.png"))
    service, _, _, progress, recorder, _ = make_service(source)
    service = ExecutionService(replace(service.services, discovery=DiscoveryFake(())))

    result = service.execute(request(source))

    assert result.outcome is ExecutionOutcome.FAILED
    assert result.issues[0].stage is IssueStage.FILE_DISCOVERY
    assert recorder.records == [(result.issues[0], 0)]
    assert progress.started is None


def test_invalid_files_can_cancel_verification() -> None:
    source = DiscoveredFile(Path("input.png"))
    service, _, interaction, _, _, _ = make_service(source)
    interaction.confirm_invalid = False
    execution_request = request(source, verify=True)
    interaction.selection = ExecutionSelection(
        (source.path,), execution_request.options
    )
    service = ExecutionService(
        replace(service.services, photo_access=InvalidPhotoAccessFake(source))
    )

    result = service.execute(execution_request)

    assert result.outcome is ExecutionOutcome.CANCELLED


def test_no_valid_files_returns_photo_open_failure() -> None:
    source = DiscoveredFile(Path("input.png"))
    service, _, interaction, _, recorder, _ = make_service(source)
    execution_request = request(source, verify=True)
    interaction.selection = ExecutionSelection(
        (source.path,), execution_request.options
    )
    service = ExecutionService(
        replace(service.services, photo_access=InvalidPhotoAccessFake(source))
    )

    result = service.execute(execution_request)

    assert result.outcome is ExecutionOutcome.FAILED
    assert result.issues[0].stage is IssueStage.PHOTO_OPEN
    assert recorder.records == [(result.issues[0], 0)]


def test_valid_files_can_cancel_verification() -> None:
    source = DiscoveredFile(Path("input.png"))
    service, _, interaction, progress, _, _ = make_service(source)
    execution_request = request(source, verify=True)
    interaction.selection = ExecutionSelection(
        (source.path,), execution_request.options
    )
    interaction.confirm_valid = False

    result = service.execute(execution_request)

    assert result.outcome is ExecutionOutcome.CANCELLED
    assert progress.started is None


def test_confirmed_valid_files_continue_to_execution() -> None:
    source = DiscoveredFile(Path("input.png"))
    service, _, interaction, progress, _, _ = make_service(source)
    execution_request = request(source, verify=True)
    interaction.selection = ExecutionSelection(
        (source.path,), execution_request.options
    )

    result = service.execute(execution_request)

    assert result.outcome is ExecutionOutcome.COMPLETED
    assert progress.started == (1, 2)


def test_initialization_failure_is_recorded() -> None:
    source = DiscoveredFile(Path("input.png"))
    issue = ExecutionIssue(
        IssueStage.ACTION_INITIALIZATION,
        IssueSeverity.ERROR,
        "failed",
    )
    service, _, _, progress, recorder, _ = make_service(source)
    service = ExecutionService(
        replace(
            service.services,
            dependencies=InitializingDependenciesFake(InitializingRunFake(issue)),
        )
    )

    result = service.execute(request(source))

    assert result.outcome is ExecutionOutcome.FAILED
    assert result.issues == (issue,)
    assert recorder.records == [(issue, 0)]
    assert progress.started is None


def test_runner_failure_still_closes_progress_and_recorder() -> None:
    source = DiscoveredFile(Path("input.png"))
    service, _, _, progress, recorder, _ = make_service(source)
    service = ExecutionService(replace(service.services, runner=FailingRunner()))

    with pytest.raises(RunnerFailure):
        service.execute(request(source))

    assert progress.closed is True
    assert recorder.closed is True
