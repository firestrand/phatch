from __future__ import annotations

import pytest
import wx

from phatch.pyWx import gui

from .native_popup_support import pump_events, wait_until

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


def _field(frame: gui.Frame, action_label: str, field_label: str):
    frame.controller.add_action_by_label(action_label)
    frame.enable_actions(True)
    frame.Layout()
    pump_events()
    action = frame.tree.GetSelection()
    return next(
        item
        for item in frame.tree.GetItemChildren(action)
        if frame.tree.GetItemData(item)[0] == field_label
    )


def _open_field(frame: gui.Frame, field) -> None:
    frame.tree.SelectItem(field)
    wait_until(lambda: frame.tree.popup is not None)


def test_popup_commit_creates_one_history_entry_and_round_trips_raw_value(
    native_frame_harness,
) -> None:
    # Given
    frame = native_frame_harness.frame
    width = _field(frame, "Border", "Border Width")
    _open_field(frame, width)
    frame.tree.popup.edit.size.SetValue("41")
    frame.tree.popup.edit.unit.SetStringSelection("px")

    # When
    frame.tree.close_popup()
    pump_events()
    frame.on_menu_edit_undo(None)
    undone = next(iter(frame.controller.export_actions())).get_field_string(
        "Border Width"
    )
    frame.on_menu_edit_redo(None)

    # Then
    assert undone == "1px"
    assert (
        next(iter(frame.controller.export_actions())).get_field_string("Border Width")
        == "41 px"
    )


def test_direct_field_edit_creates_one_history_entry(
    native_frame_harness,
) -> None:
    # Given
    frame = native_frame_harness.frame
    width = _field(frame, "Border", "Border Width")

    # When
    transaction = frame.controller.begin_transaction()
    frame.tree.set_form_field_value(width, "41px")
    frame.controller.commit_transaction(transaction)
    frame.on_menu_edit_undo(None)

    # Then
    assert not frame.IsEmpty()
    assert (
        next(iter(frame.controller.export_actions())).get_field_string("Border Width")
        == "1px"
    )


def test_escape_invalid_and_noop_popup_edits_create_no_history_entry(
    native_frame_harness,
) -> None:
    # Given
    frame = native_frame_harness.frame
    width = _field(frame, "Border", "Border Width")
    _open_field(frame, width)
    frame.tree.popup.edit.size.SetValue("invalid")

    # When
    frame.tree.cancel_popup()
    frame.on_menu_edit_undo(None)

    # Then: only the action insertion is undone.
    assert frame.IsEmpty()
    assert not frame.controller.can_undo


def test_noop_popup_close_keeps_single_existing_history_entry(
    native_frame_harness,
) -> None:
    # Given
    frame = native_frame_harness.frame
    width = _field(frame, "Border", "Border Width")
    _open_field(frame, width)

    # When
    frame.tree.close_popup()
    frame.on_menu_edit_undo(None)

    # Then
    assert frame.IsEmpty()
    assert not frame.controller.can_undo


@pytest.mark.parametrize("key_code", [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER])
def test_enter_key_finalizes_popup_transaction(
    native_frame_harness, key_code: int
) -> None:
    # Given
    frame = native_frame_harness.frame
    width = _field(frame, "Border", "Border Width")
    _open_field(frame, width)
    frame.tree.popup.edit.size.SetValue("17")
    edit_panel = frame.tree.popup
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(key_code)

    # When
    edit_panel._OnKey(event)

    # Then
    assert frame.tree.popup is None
    assert (
        next(iter(frame.controller.export_actions())).get_field_string("Border Width")
        == "17 px"
    )


def test_escape_key_rolls_back_popup_transaction(native_frame_harness) -> None:
    # Given
    frame = native_frame_harness.frame
    width = _field(frame, "Border", "Border Width")
    _open_field(frame, width)
    frame.tree.popup.edit.size.SetValue("17")
    edit_panel = frame.tree.popup
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(wx.WXK_ESCAPE)

    # When
    edit_panel._OnKey(event)

    # Then
    assert frame.tree.popup is None
    assert (
        next(iter(frame.controller.export_actions())).get_field_string("Border Width")
        == "1px"
    )


def test_document_undo_discards_invalid_active_editor_before_traversal(
    native_frame_harness,
) -> None:
    # Given
    frame = native_frame_harness.frame
    width = _field(frame, "Border", "Border Width")
    _open_field(frame, width)
    frame.tree.popup.edit.size.SetValue("invalid")

    # When
    frame.on_menu_edit_undo(None)

    # Then
    assert frame.tree.popup is None
    assert frame.IsEmpty()
    assert native_frame_harness.dialogs.errors


def test_menu_state_and_checkpoint_follow_edit_save_undo_redo(
    native_frame_harness, tmp_path
) -> None:
    # Given
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    path = tmp_path / "history.phatch"
    frame._save(str(path))
    frame.controller.add_action_by_label_to_last("Save")

    # When
    frame.on_menu_edit_undo(None)
    clean_title = frame.GetTitle()
    frame.on_menu_edit_redo(None)

    # Then
    assert "*" not in clean_title
    assert "*" in frame.GetTitle()
    assert frame.menu_edit_undo.IsEnabled()
    assert not frame.menu_edit_redo.IsEnabled()
