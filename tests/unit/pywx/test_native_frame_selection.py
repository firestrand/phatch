from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


def test_disable_menu_updates_selected_native_action(native_frame_harness) -> None:
    # Given: an enabled action selected in the real tree
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")

    # When: its bound Disable menu item is dispatched through wx
    native_frame_harness.dispatch_menu(frame.menu_edit_disable)

    # Then: the exported action and frame title expose the changed state
    action = next(iter(frame.controller.export_actions()))
    assert not action._get_fields()["__enabled__"].get()
    assert frame.controller.state.dirty
    assert "*" in frame.GetTitle()


def test_enable_menu_updates_selected_native_action(native_frame_harness) -> None:
    # Given: a disabled action selected in the real tree
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    frame.controller.enable_selected_action(False)

    # When: its bound Enable menu item is dispatched through wx
    native_frame_harness.dispatch_menu(frame.menu_edit_enable)

    # Then: the real tree exports the action as enabled
    action = next(iter(frame.controller.export_actions()))
    assert action._get_fields()["__enabled__"].get()


def test_move_menu_reorders_native_actions(native_frame_harness) -> None:
    # Given: two real actions with the last action selected
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    frame.controller.add_action_by_label_to_last("Save")

    # When: the bound Up menu item is dispatched through wx
    native_frame_harness.dispatch_menu(frame.menu_edit_up)

    # Then: native tree export order changes
    assert [action.label for action in frame.controller.export_actions()] == [
        "Save",
        "Border",
    ]


def test_remove_menu_clears_last_native_action_and_hides_tree(
    native_frame_harness,
) -> None:
    # Given: one selected action in the real tree
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    frame.enable_actions(True)

    # When: the bound Remove menu item is dispatched through wx
    native_frame_harness.dispatch_menu(frame.menu_edit_remove)

    # Then: the editor returns to its empty native-control state
    assert frame.IsEmpty()
    assert not frame.controller.state.has_actions
    assert not frame.tree.IsShown()
    assert frame.empty.IsShown()


def test_description_event_updates_controller_and_title(native_frame_harness) -> None:
    # Given: a clean native editor description control
    frame = native_frame_harness.frame
    event = pytest.importorskip("wx").CommandEvent(
        pytest.importorskip("wx").EVT_TEXT.typeId,
        frame.description.GetId(),
    )
    event.SetString("changed description")

    # When: the frame handles the native text event
    frame.on_description_text(event)

    # Then: controller state and title reflect the edit
    assert frame.controller.state.description == "changed description"
    assert frame.controller.state.dirty
    assert "*" in frame.GetTitle()


def test_view_handlers_change_real_control_visibility(native_frame_harness) -> None:
    # Given: a real frame with an action and hidden description
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    frame.enable_actions(True)
    event = pytest.importorskip("wx").CommandEvent()
    event.SetInt(1)

    # When: view handlers receive a checked native command event
    frame.on_menu_view_description(event)
    frame.on_menu_view_collapse_automatic(event)

    # Then: actual controls and menu state expose both choices
    assert frame.description.IsShown()
    assert frame.menu_view_description.IsChecked()
    assert frame.tree.collapse_automatic
    assert native_frame_harness.app.settings["description"]
    assert native_frame_harness.app.settings["collapse_automatic"]
