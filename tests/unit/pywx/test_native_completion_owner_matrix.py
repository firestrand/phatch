from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import UUID

import pytest
import wx

from phatch.core.execution_types import ExecutionOutcome, ExecutionResult
from phatch.pyWx import gui
from phatch.pyWx.dialog_service import DialogService
from phatch.pyWx.frame_dependencies import FrameDependencies
from phatch.services.action_list import (
    ActionListLoadResult,
    ActionListService,
)
from phatch.services.completion import collect_completion_events

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


OUTCOMES = tuple(ExecutionOutcome)


class ResultService(ActionListService):
    def __init__(self, result: ExecutionResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def load(self, filename: str) -> ActionListLoadResult:
        from phatch.core import api

        actions = api.ACTIONS
        if actions is None:
            pytest.fail("action registry was not initialized")
        return ActionListLoadResult(
            data={"actions": [actions["Save"]()]},
            warning="",
            invalid_labels=(),
        )

    def execute(
        self, actions, settings, update_callback=None, recovery=None, **options
    ) -> ExecutionResult:
        self.calls.append(options)
        return self.result


class ResultDialogs(DialogService):
    def __init__(self) -> None:
        self.presentations: list[tuple[ExecutionResult, str]] = []

    def set_report(self, report) -> None:
        return None

    def show_execution_result(self, result: ExecutionResult, message: str) -> None:
        self.presentations.append((result, message))


class RaisingResultService(ResultService):
    def execute(
        self, actions, settings, update_callback=None, recovery=None, **options
    ) -> ExecutionResult:
        raise RuntimeError("execution failed")


@pytest.mark.parametrize("outcome", OUTCOMES)
def test_gui_public_route_emits_one_identifiable_completion(
    native_frame_harness,
    outcome: ExecutionOutcome,
) -> None:
    frame = native_frame_harness.frame
    service = ResultService(ExecutionResult(outcome, ()))
    frame._action_service = service
    frame.controller.add_action_by_label("Border")
    receipts = []

    with collect_completion_events(receipts.append):
        result = frame._execute(frame.controller.export_actions(), paths=["input.png"])

    assert result.outcome is outcome
    assert service.calls == [{"paths": ["input.png"]}]
    assert frame._last_completion.owner == "gui"
    assert receipts == [frame._last_completion]
    assert UUID(receipts[0].request_id).version == 4
    sys.stdout.write(
        json.dumps(
            {
                "owner": receipts[0].owner,
                "outcome": outcome.value,
                "presentations": 1,
                "request_id": receipts[0].request_id,
            },
            sort_keys=True,
        )
        + "\n"
    )


@pytest.mark.parametrize(
    ("drop", "owner"),
    ((False, "gui"), (True, "droplet")),
)
def test_gui_execution_error_emits_one_completion(
    native_frame_harness,
    drop: bool,
    owner: str,
) -> None:
    frame = native_frame_harness.frame
    frame._action_service = RaisingResultService(
        ExecutionResult(ExecutionOutcome.FAILED, ())
    )
    frame.controller.add_action_by_label("Border")
    receipts = []

    with (
        collect_completion_events(receipts.append),
        pytest.raises(RuntimeError, match="execution failed"),
    ):
        frame._execute(
            frame.controller.export_actions(),
            paths=["input.png"],
            drop=drop,
        )

    assert len(receipts) == 1
    assert receipts[0].owner == owner
    assert UUID(receipts[0].request_id).version == 4


@pytest.mark.parametrize("outcome", OUTCOMES)
def test_gui_drop_public_route_has_one_unique_droplet_completion(
    native_frame_harness,
    outcome: ExecutionOutcome,
) -> None:
    frame = native_frame_harness.frame
    service = ResultService(ExecutionResult(outcome, ()))
    frame._action_service = service
    frame.controller.add_action_by_label("Border")
    receipts = []

    with collect_completion_events(receipts.append):
        result = frame.on_drop(["input.png"], 4, 5)

    calls = [
        call
        for call in native_frame_harness.dialogs.calls
        if call[0] == "execution_result"
    ]
    assert result.outcome is outcome
    assert service.calls == [{"paths": ["input.png"], "drop": True}]
    assert len(calls) == 1
    assert frame._last_completion.owner == "droplet"
    assert frame._last_completion.request_id
    assert receipts == [frame._last_completion]
    assert UUID(receipts[0].request_id).version == 4
    sys.stdout.write(
        json.dumps(
            {
                "owner": receipts[0].owner,
                "outcome": outcome.value,
                "presentations": len(calls),
                "request_id": receipts[0].request_id,
            },
            sort_keys=True,
        )
        + "\n"
    )


@pytest.mark.parametrize("outcome", OUTCOMES)
def test_standalone_droplet_public_route_presents_once_before_destroy(
    native_frame_harness,
    tmp_path: Path,
    outcome: ExecutionOutcome,
) -> None:
    actionlist = tmp_path / f"{outcome.value}.phatch"
    actionlist.touch()
    service = ResultService(ExecutionResult(outcome, ()))
    dialogs = ResultDialogs()
    dependencies = FrameDependencies(
        action_service_factory=lambda: service,
        dialog_service_factory=lambda _parent: dialogs,
    )

    receipts = []
    with collect_completion_events(receipts.append):
        frame = gui.DropletFrame(
            str(actionlist),
            ["input.png"],
            None,
            wx.ID_ANY,
            "droplet",
            dependencies=dependencies,
        )
        wx.Yield()

    assert service.calls == [{"paths": ["input.png"], "drop": True}]
    assert len(dialogs.presentations) == 1
    assert dialogs.presentations[0][0].outcome is outcome
    assert frame._last_completion.owner == "droplet"
    assert frame._last_completion.request_id
    assert receipts == [frame._last_completion]
    assert UUID(receipts[0].request_id).version == 4
    assert frame._listeners == []
    assert not frame
