from __future__ import annotations

import pytest

from phatch.core import api
from phatch.services.action_list import (
    ActionListLoadResult,
    ActionListService,
    IncompatibleActionListError,
    MissingRequiredActionError,
    UnsafeActionListError,
)

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


class MissingActionService(ActionListService):
    def load(self, filename: str) -> ActionListLoadResult:
        raise MissingRequiredActionError(KeyError("Resize"))


class UnsafeActionService(ActionListService):
    def load(self, filename: str) -> ActionListLoadResult:
        raise UnsafeActionListError("unsafe expression")


class IncompatibleActionService(ActionListService):
    def load(self, filename: str) -> ActionListLoadResult:
        raise IncompatibleActionListError(filename)


class WarningActionService(ActionListService):
    def load(self, filename: str) -> ActionListLoadResult:
        return ActionListLoadResult(
            data={"description": "warning", "actions": [api.ACTIONS["Border"]()]},
            warning="unsafe warning",
            invalid_labels=("Old field",),
        )


@pytest.mark.parametrize(
    ("service", "fragment"),
    [
        (MissingActionService(), "Resize"),
        (UnsafeActionService(), "unsafe expression"),
        (IncompatibleActionService(), "incompatible"),
    ],
)
def test_actionlist_service_errors_are_reported_by_real_frame(
    native_frame_harness, tmp_path, service: ActionListService, fragment: str
) -> None:
    # Given: an existing path and a typed action-list service failure
    path = tmp_path / "failure.phatch"
    path.touch()
    native_frame_harness.frame._action_service = service

    # When: the frame loads through that production boundary
    result = native_frame_harness.frame.load_actionlist_data(str(path))

    # Then: loading stops and the user receives a specific error
    assert result is None
    assert fragment.lower() in native_frame_harness.dialogs.errors[-1].lower()


def test_actionlist_warnings_report_lost_values_and_unsafe_content(
    native_frame_harness, tmp_path
) -> None:
    # Given: a load result with invalid labels and an accepted unsafe warning
    path = tmp_path / "warning.phatch"
    path.touch()
    native_frame_harness.frame._action_service = WarningActionService()

    # When: the real frame translates the service result
    result = native_frame_harness.frame.load_actionlist_data(str(path))
    wx.Yield()

    # Then: returned data and both messages retain service details
    assert result is not None
    assert result["invalid labels"] == ["Old field"]
    assert "Old field" in native_frame_harness.dialogs.messages[-1][0]
    assert "unsafe warning" in native_frame_harness.dialogs.errors[-1]


def test_nonexistent_actionlist_skips_service_and_messages(
    native_frame_harness,
) -> None:
    # Given: an absent isolated action-list path
    path = native_frame_harness.root / "absent.phatch"

    # When: the frame data loader checks it
    result = native_frame_harness.frame.load_actionlist_data(str(path))

    # Then: absence is represented without a modal error at this lower boundary
    assert result is None
    assert not native_frame_harness.dialogs.errors


def test_settings_report_and_icon_state_use_real_app(native_frame_harness) -> None:
    # Given: a native app/frame pair and isolated configured image path
    frame = native_frame_harness.frame
    expected = frame.get_icon_filename()

    # When: settings and report APIs mutate application state
    frame.set_setting("description", True)
    frame.set_report([("image.png",)])

    # Then: application state and cached icon path are observable
    assert frame.get_setting("description")
    assert frame.get_icon_filename() is expected
    assert native_frame_harness.app.report == [("image.png",)]


def test_update_event_reaches_other_native_top_level_window(
    native_frame_harness,
) -> None:
    # Given: another real top-level window subscribed to inspector updates
    from phatch.lib.pyWx import imageInspector

    received: list[bool] = []
    observer = wx.Frame(None, title="observer")
    observer.Bind(imageInspector.UPDATE_EVENT, lambda _event: received.append(True))
    observer.Show()

    # When: the main frame publishes its update event
    native_frame_harness.frame._send_update_event()
    wx.Yield()

    # Then: the sibling native window receives it while the sender does not close
    assert received == [True]
    assert native_frame_harness.frame.IsShown()


def test_execute_resets_report_and_supplies_update_callback(
    native_frame_harness,
) -> None:
    # Given: a real action in the native tree and recording execution service
    executions: list[tuple] = []

    def apply_actions(actions, settings, **options) -> None:
        executions.append((tuple(actions), settings, options))

    service = ActionListService(apply_actions_to_photos=apply_actions)
    frame = native_frame_harness.frame
    frame._action_service = service
    frame.controller.add_action_by_label("Border")

    # When: the internal frame execution path runs
    frame._execute(frame.controller.export_actions(), paths=["input.png"])

    # Then: app report resets and the service gets the frame update callback
    assert native_frame_harness.app.report == []
    assert executions[0][2]["update"] == frame._send_update_event
    assert executions[0][2]["paths"] == ["input.png"]
