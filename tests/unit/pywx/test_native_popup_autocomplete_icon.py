from __future__ import annotations

import pytest

pytest.importorskip("wx")
import wx

from phatch.lib.pyWx.autoCompleteCtrls import AutoCompleteIconCtrl

from .native_popup_support import panel, pump_events, replace_text

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def make_icon_control(native_frame: wx.Frame) -> AutoCompleteIconCtrl:
    control = AutoCompleteIconCtrl(
        panel(native_frame),
        wx.ID_ANY,
        "",
        wx.TE_PROCESS_ENTER,
        ["Gamma", "Alpha", "Beta"],
        size=wx.Size(260, 28),
    )
    pump_events()
    return control


def test_icon_control_renders_sorted_choices_with_native_images(native_frame):
    # Given
    control = make_icon_control(native_frame)

    # When
    control.SetChoices(["Zulu", "Alpha"])

    # Then
    assert control.GetChoices() == ["Alpha", "Zulu"]
    assert control.dropdownlistbox.GetItemCount() == 2
    assert control.dropdownlistbox.GetImageList(wx.IMAGE_LIST_NORMAL) is control.il

    control._showDropDown(False)


def test_icon_control_filters_contains_match_and_commits_selection(native_frame):
    # Given
    control = make_icon_control(native_frame)

    # When
    replace_text(control, "amm")
    control.setDynamicChoices()
    control.dropdownlistbox.Select(0)
    control._setValueFromSelected()

    # Then
    assert control.GetChoices() == ["Gamma"]
    assert control.GetValue() == "Gamma"
    assert not control.dropdown.IsShown()


def test_icon_list_click_commits_real_selected_item(native_frame):
    # Given
    control = make_icon_control(native_frame)
    control.dropdownlistbox.Select(1)
    event = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
    event.SetPosition(control.dropdownlistbox.GetItemRect(1).GetPosition())

    # When
    control.onListClick(event)

    # Then
    assert control.GetValue() == "Beta"
    assert not control.dropdown.IsShown()


def test_icon_control_change_hides_popup_and_skips_event(native_frame):
    # Given
    control = make_icon_control(native_frame)
    control._showDropDown(True)
    event = wx.MoveEvent(native_frame.GetPosition(), native_frame.GetId())

    # When
    control.onControlChanged(event)

    # Then
    assert not control.dropdown.IsShown()


def test_icon_click_toggle_reopens_hidden_popup(native_frame):
    # Given
    control = make_icon_control(native_frame)
    control._showDropDown(False)


def test_icon_control_requires_choices(native_frame):
    # Given
    parent = panel(native_frame)

    # When / Then
    with pytest.raises(ValueError, match="at least one"):
        AutoCompleteIconCtrl(
            parent,
            wx.ID_ANY,
            "",
            wx.TE_PROCESS_ENTER,
            [],
            size=wx.Size(260, 28),
        )


def test_icon_control_accepts_tuple_choices_and_disabled_click_toggle(native_frame):
    # Given
    control = AutoCompleteIconCtrl(
        panel(native_frame),
        wx.ID_ANY,
        "",
        wx.TE_PROCESS_ENTER,
        ("Beta", "Alpha"),
        dropDownClick=False,
        size=wx.Size(260, 28),
    )

    # When
    control.SetChoices(("Delta", "Charlie"))

    # Then
    assert control.GetChoices() == ["Charlie", "Delta"]
    assert control.dropdownlistbox.GetItemText(0) == "Charlie"

    control._showDropDown(False)


def test_icon_control_supports_multiple_columns_and_selection_callback(native_frame):
    # Given
    selected: list[list[str]] = []
    control = AutoCompleteIconCtrl(
        panel(native_frame),
        wx.ID_ANY,
        "",
        wx.TE_PROCESS_ENTER,
        [],
        colNames=["Name", "Value"],
        multiChoices=[("Beta", "2"), ("Alpha", "1")],
        colFetch=1,
        selectCallback=selected.append,
        size=wx.Size(260, 28),
    )
    control.dropdownlistbox.Select(0)

    # When
    control._setValueFromSelected()

    # Then
    assert control.GetValue() == "1"
    assert selected == [["Alpha", "1"]]
    assert control.dropdownlistbox.GetColumnCount() == 2


def test_activate_event_reopens_then_closes_popup(native_frame):
    # Given
    control = make_icon_control(native_frame)
    control._showDropDown(False)

    # When
    control.onActivate(wx.ActivateEvent(wx.wxEVT_ACTIVATE, True, control.GetId()))

    # Then
    assert control.dropdown.IsShown()

    control.onActivate(wx.ActivateEvent(wx.wxEVT_ACTIVATE, False, control.GetId()))
    assert not control.dropdown.IsShown()
    event = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)

    # When
    control.onClickToggleDown(event)

    # Then
    assert control.dropdown.IsShown()

    control._showDropDown(False)


def test_linux_icon_list_uses_native_information_background(native_frame, monkeypatch):
    # Given
    monkeypatch.setattr("phatch.lib.pyWx.autoCompleteCtrls.sys.platform", "linux")

    # When
    control = make_icon_control(native_frame)

    # Then
    expected = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK)
    assert control.dropdownlistbox.GetBackgroundColour() == expected
    assert control.dropdownlistbox.GetItemCount() == 3

    control._showDropDown(False)
