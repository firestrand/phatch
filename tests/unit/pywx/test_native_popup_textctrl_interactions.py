from __future__ import annotations

import pytest

pytest.importorskip("wx")
import wx

from phatch.other.pyWx.TextCtrlAutoComplete import TextCtrlAutoComplete

from .native_popup_support import panel, pump_events, send_key

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def text_event(control: wx.TextCtrl, value: str) -> wx.CommandEvent:
    event = wx.CommandEvent(wx.EVT_TEXT.typeId, control.GetId())
    event.SetString(value)
    return event


def test_single_column_constructor_applies_style_and_tuple_choices(native_frame):
    # Given / When
    control = TextCtrlAutoComplete(
        panel(native_frame),
        choices=("Beta", "Alpha"),
        dropDownClick=False,
        style=wx.BORDER_NONE,
    )

    # Then
    assert control.GetWindowStyleFlag() & wx.TE_PROCESS_ENTER
    assert control.GetChoices() == ["Alpha", "Beta"]
    assert control.dropdownlistbox.GetItemCount() == 2


def test_empty_entry_hides_visible_dropdown_and_calls_entry_callback(native_frame):
    # Given
    callbacks: list[str] = []
    control = TextCtrlAutoComplete(
        panel(native_frame),
        choices=["Alpha", "Beta"],
        entryCallback=lambda: callbacks.append("entry"),
    )
    control._showDropDown(True)

    # When
    event = text_event(control, "")
    control.onEnteredText(event)

    # Then
    assert callbacks == ["entry"]
    assert not control.dropdown.IsShown()
    assert event.GetSkipped()


def test_no_match_can_remain_visible_and_deselects_current_row(native_frame):
    # Given
    control = TextCtrlAutoComplete(
        panel(native_frame), choices=["Alpha", "Beta"], hideOnNoMatch=False
    )
    control.SetSize(wx.Size(260, 28))
    control.Unbind(wx.EVT_KILL_FOCUS)
    control.Unbind(wx.EVT_MOVE)
    control.Unbind(wx.EVT_SIZE)
    pump_events()
    control.dropdownlistbox.Select(0)
    control._showDropDown(True)

    # When
    event = text_event(control, "missing")
    control.onEnteredText(event)

    # Then
    assert control.dropdownlistbox.GetFirstSelected() == wx.NOT_FOUND
    assert event.GetSkipped()


def test_custom_match_checks_real_rows_until_match(native_frame):
    # Given
    matches: list[tuple[str, str]] = []

    def match(text: str, choice: str) -> bool:
        matches.append((text, choice))
        return choice.endswith(text)

    control = TextCtrlAutoComplete(
        panel(native_frame),
        choices=["Alpha", "Beta"],
        matchFunction=match,
    )
    control.SetSize(wx.Size(260, 28))
    control.Unbind(wx.EVT_KILL_FOCUS)
    control.Unbind(wx.EVT_MOVE)
    control.Unbind(wx.EVT_SIZE)
    pump_events()

    # When
    event = text_event(control, "ta")
    control.onEnteredText(event)

    # Then
    assert matches == [("ta", "Alpha"), ("ta", "Beta")]
    assert control.GetChoices() == ["Alpha", "Beta"]
    assert event.GetSkipped()


def test_keyboard_navigation_honors_first_and_last_row_boundaries(native_frame):
    # Given
    control = TextCtrlAutoComplete(
        panel(native_frame), choices=["Alpha", "Beta", "Gamma"]
    )

    # When
    send_key(control, wx.WXK_DOWN)
    first_index = control.dropdownlistbox.GetFirstSelected()
    control.dropdownlistbox.Select(2)
    send_key(control, wx.WXK_DOWN)
    last_index = control.dropdownlistbox.GetFirstSelected()
    send_key(control, wx.WXK_UP)

    # Then
    assert first_index == 0
    assert last_index == 2
    assert control.dropdownlistbox.GetFirstSelected() == 1


def test_single_column_horizontal_keys_leave_search_column_unchanged(native_frame):
    # Given
    control = TextCtrlAutoComplete(panel(native_frame), choices=["Alpha", "Beta"])

    # When
    send_key(control, wx.WXK_LEFT)
    send_key(control, wx.WXK_RIGHT)

    # Then
    assert control._colSearch == 0
    assert control.GetValue() == ""


def test_multicolumn_keys_and_tab_fetch_selected_column_once(native_frame):
    # Given
    selected: list[list[str]] = []
    control = TextCtrlAutoComplete(
        panel(native_frame),
        colNames=["Name", "Value"],
        multiChoices=[("Beta", "2"), ("Alpha", "1")],
        showHead=False,
        colFetch=1,
        selectCallback=selected.append,
    )
    control.dropdownlistbox.Select(0)
    control._showDropDown(True)

    # When
    send_key(control, wx.WXK_RIGHT)
    send_key(control, wx.WXK_RIGHT)
    send_key(control, wx.WXK_LEFT)
    send_key(control, wx.WXK_TAB)

    # Then
    assert control._colSearch == 0
    assert control.GetValue() == "1"
    assert selected == [["Alpha", "1"]]
    assert not control.dropdown.IsShown()


def test_deselected_commit_preserves_value_and_selected_commit_uses_search_column(
    native_frame,
):
    # Given
    control = TextCtrlAutoComplete(
        panel(native_frame), multiChoices=[("Alpha", "1"), ("Beta", "2")]
    )
    control.SetValue("before")

    # When
    control._setValueFromSelected()
    deselected_value = control.GetValue()
    control.dropdownlistbox.Select(1)
    control._setValueFromSelected()

    # Then
    assert deselected_value == "before"
    assert control.GetValue() == "Beta"
    assert control.GetSelection() == (0, len("Beta"))


def test_mouse_hit_testing_selects_only_rows_inside_real_list(native_frame):
    # Given
    control = TextCtrlAutoComplete(panel(native_frame), choices=["Alpha", "Beta"])
    outside = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
    outside.SetPosition(wx.Point(-10, -10))
    inside = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
    inside.SetPosition(control.dropdownlistbox.GetItemRect(1).GetPosition())

    # When
    control.onListClick(outside)
    outside_selection = control.dropdownlistbox.GetFirstSelected()
    control.onListClick(inside)

    # Then
    assert outside_selection == wx.NOT_FOUND
    assert control.dropdownlistbox.GetFirstSelected() == 1


def test_click_toggle_requires_unchanged_insertion_point(native_frame):
    # Given
    control = TextCtrlAutoComplete(panel(native_frame), choices=["Alpha", "Beta"])
    control.SetValue("A")
    control.SetInsertionPointEnd()
    control._showDropDown(False)
    up = wx.MouseEvent(wx.wxEVT_LEFT_UP)

    # When
    control._lastinsertionpoint = -1
    control.onClickToggleUp(up)
    unchanged_position_visible = control.dropdown.IsShown()
    control._lastinsertionpoint = control.GetInsertionPoint()
    control.onClickToggleUp(up)

    # Then
    assert not unchanged_position_visible
    assert control.dropdown.IsShown()


def test_popup_repositions_above_when_screen_space_is_exhausted(native_frame):
    # Given
    control = TextCtrlAutoComplete(panel(native_frame), choices=["Alpha", "Beta"])
    control.SetSize(wx.Size(240, 28))
    control._screenheight = 0

    # When
    control._showDropDown(True)

    # Then
    assert control.dropdown.IsShown()
    assert control.dropdown.GetSize().width == control.GetSize().width
    assert control.dropdown.GetPosition().y < control.ClientToScreen(0, 28)[1]


def test_choice_replacement_handles_empty_and_multicolumn_tuple_inputs(native_frame):
    # Given
    control = TextCtrlAutoComplete(panel(native_frame), choices=["Alpha", "Beta"])

    # When
    control.SetChoices(())
    empty_count = control.dropdownlistbox.GetItemCount()
    control.SetMultipleChoices((("Gamma", "3"), ("Delta", "4")))

    # Then
    assert empty_count == 0
    assert control.GetChoices() == [("Delta", "4"), ("Gamma", "3")]
    assert control.dropdownlistbox.GetColumnCount() == 2
    assert control.dropdownlistbox.GetItemText(0, 1) == "4"


def test_one_row_multicolumn_input_reports_invalid_range(native_frame):
    # Given
    control = TextCtrlAutoComplete(panel(native_frame), choices=["Alpha"])

    # When / Then
    with pytest.raises(ValueError, match="multi-dimension"):
        control.SetMultipleChoices([("Only", "1")])
