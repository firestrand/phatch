from __future__ import annotations

import pytest

pytest.importorskip("wx")
import wx

from phatch.lib.pyWx.autoCompleteCtrls import AutoCompleteTextCtrl

from .native_popup_support import (
    panel,
    pump_events,
    replace_text,
    send_key,
    wait_until,
)

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def make_control(native_frame: wx.Frame) -> AutoCompleteTextCtrl:
    control = AutoCompleteTextCtrl(
        panel(native_frame),
        wx.ID_ANY,
        "",
        wx.TE_PROCESS_ENTER,
        ["Beta", "http://python.org", "www.wxpython.org", "Alpha"],
    )
    control.SetSize(wx.Size(260, 28))
    pump_events()
    return control


def test_initialization_sorts_choices_and_shows_native_popup(native_frame):
    # Given
    control = make_control(native_frame)

    # When
    wait_until(control.dropdown.IsShown)

    # Then
    assert control.GetChoices() == [
        "Alpha",
        "Beta",
        "http://python.org",
        "www.wxpython.org",
    ]
    assert control.dropdown.IsShownOnScreen()
    assert control.dropdownlistbox.GetItemCount() == 4

    control._showDropDown(False)


def test_typed_value_filters_protocol_prefixed_choices(native_frame):
    # Given
    control = make_control(native_frame)

    # When
    replace_text(control, "py")

    # Then
    assert control.GetValue() == "py"
    assert control.GetChoices() == ["http://python.org"]
    assert control.dropdown.IsShown()

    control._showDropDown(False)


def test_unknown_typed_value_hides_popup(native_frame):
    # Given
    control = make_control(native_frame)

    # When
    replace_text(control, "not-a-choice")

    # Then
    assert control.GetChoices() == []
    assert not control.dropdown.IsShown()


def test_down_and_return_commit_selected_value(native_frame):
    # Given
    control = make_control(native_frame)
    replace_text(control, "a")

    # When
    send_key(control, wx.WXK_DOWN)
    send_key(control, wx.WXK_RETURN)

    # Then
    assert control.GetValue() == "Alpha"
    assert not control.dropdown.IsShown()


def test_escape_closes_visible_popup_without_changing_value(native_frame):
    # Given
    control = make_control(native_frame)
    replace_text(control, "b")
    assert control.dropdown.IsShown()

    # When
    send_key(control, wx.WXK_ESCAPE)

    # Then
    assert control.GetValue() == "b"
    assert not control.dropdown.IsShown()


def test_selected_list_item_is_committed_and_popup_closes(native_frame):
    # Given
    control = make_control(native_frame)
    control.dropdownlistbox.Select(1)
    control._showDropDown(True)

    # When
    control._setValueFromSelected()
    pump_events()

    # Then
    assert control.GetValue() == "Beta"
    assert not control.dropdown.IsShown()


def test_top_level_move_hides_popup_while_events_are_started(native_frame):
    # Given
    control = make_control(native_frame)
    control.StartEvents()
    wait_until(control.dropdown.IsShown)

    # When
    position = native_frame.GetPosition()
    native_frame.Move(wx.Point(position.x + 1, position.y + 1))
    wait_until(lambda: not control.dropdown.IsShown())

    # Then
    assert not control.dropdown.IsShownOnScreen()

    control.StopEvents()


def test_stopped_top_level_events_leave_popup_visible(native_frame):
    # Given
    control = make_control(native_frame)
    control.StartEvents()
    control.StopEvents()
    control._showDropDown(True)

    # When
    position = native_frame.GetPosition()
    native_frame.Move(wx.Point(position.x + 1, position.y + 1))
    pump_events()

    # Then
    assert control.dropdown.IsShown()

    control._showDropDown(False)


def test_destroyed_control_skips_move_event_without_touching_popup(native_frame):
    # Given
    control = make_control(native_frame)
    event = wx.MoveEvent(native_frame.GetPosition(), native_frame.GetId())
    control.Destroy()
    pump_events()

    # When
    control.onControlChanged(event)

    # Then
    assert not control
    assert event.GetSkipped()
