from __future__ import annotations

import pytest

pytest.importorskip("wx")
import wx

from phatch.lib.pyWx import popup

from .native_popup_support import (
    CallbackLog,
    panel,
    pump_events,
    replace_text,
    wait_until,
)

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def test_text_control_preserves_custom_value_and_emits_deferred_change(native_frame):
    # Given
    callback = CallbackLog()
    control = popup.TextCtrl(
        panel(native_frame), "custom", choices=["known"], on_change=callback
    )
    pump_events()
    callback.values.clear()

    # When
    replace_text(control, "entered")
    wait_until(lambda: "entered" in callback.values)

    # Then
    assert control.Get() == "entered"
    assert control.GetString(0) == "custom"
    assert callback.values[-1] == "entered"


def test_boolean_control_reports_translated_value_and_callback(native_frame):
    # Given
    callback = CallbackLog()
    control = popup.BooleanCtrl(panel(native_frame), False, (120, 28), callback)
    pump_events()
    callback.values.clear()

    # When
    control.SetValue(True)
    event = wx.CommandEvent(wx.EVT_CHECKBOX.typeId, control.GetId())
    event.SetEventObject(control)
    control.ProcessEvent(event)
    wait_until(lambda: bool(callback.values))

    # Then
    assert control.Get() == "yes"
    assert callback.values == ["yes"]


def test_choice_control_round_trips_registered_choice(native_frame):
    # Given
    callback = CallbackLog()
    control = popup.ChoiceCtrl(
        panel(native_frame), "second", (160, 28), ["first", "second"], callback
    )

    # When
    control.SetSelection(0)
    event = wx.CommandEvent(wx.EVT_CHOICE.typeId, control.GetId())
    event.SetEventObject(control)
    control.ProcessEvent(event)
    wait_until(lambda: callback.values == ["first"])

    # Then
    assert control.Get() == "first"


def test_readonly_combo_returns_choice_and_editable_combo_returns_text(native_frame):
    # Given
    readonly = popup.ComboCtrl(
        panel(native_frame), "second", (160, 28), ["first", "second"], ["READONLY"]
    )
    editable = popup.ComboCtrl(
        panel(native_frame), "custom", (160, 28), ["first"], ["DROPDOWN"]
    )

    # When
    editable.SetValue("entered")

    # Then
    assert readonly.Get() == "second"
    assert editable.Get() == "entered"


@pytest.mark.parametrize(
    ("initial", "expected_value", "expected_unit"),
    [("25%", "25", "%"), ("12", "12", "px"), ("", "", "px")],
)
def test_pixel_control_splits_and_round_trips_units(
    native_frame, initial, expected_value, expected_unit
):
    # Given
    control = popup.PixelCtrl(panel(native_frame), initial, (220, 28))

    # When
    value, unit = control.SplitValue(initial)

    # Then
    assert value == expected_value
    assert unit == expected_unit
    expected = f"{expected_value} {expected_unit}" if initial else ""
    assert control.GetValue() == expected


def test_slider_controls_synchronize_real_spin_and_slider_widgets(native_frame):
    # Given
    control = popup.SliderCtrl(
        panel(native_frame), "7", (240, 28), minValue=5, maxValue=10
    )

    # When
    control.spin.SetValue(9)
    control.OnSpin(wx.CommandEvent(wx.EVT_SPINCTRL.typeId, control.spin.GetId()))
    control.slider.SetValue(6)
    control.OnScroll(wx.ScrollEvent(wx.wxEVT_SCROLL_THUMBTRACK, control.slider.GetId()))

    # Then
    assert control.slider.GetValue() == 6
    assert control.spin.GetValue() == 6
    assert control.GetValue() == "6"


def test_float_slider_ignores_invalid_text_then_tracks_scroll(native_frame):
    # Given
    control = popup.FloatSliderCtrl(
        panel(native_frame), "0.5", (240, 28), minValue=0, maxValue=1
    )
    starting_slider_value = control.slider.GetValue()

    # When
    invalid = wx.CommandEvent(wx.EVT_TEXT.typeId, control.spin.GetId())
    invalid.SetString("invalid")
    control.OnSpin(invalid)
    control.slider.SetValue(75)
    control.OnScroll(wx.ScrollEvent(wx.wxEVT_SCROLL_THUMBTRACK, control.slider.GetId()))

    # Then
    assert starting_slider_value == 50
    assert control.GetValue() == "0.75"


def test_edit_panel_closes_to_current_value_and_destroys_widget(native_frame):
    # Given
    editor = popup.EditPanel(
        panel(native_frame), "Text", "before", {}, size=(300, 28), label="Name: "
    )
    editor.Show()
    replace_text(editor.edit, "after")

    # When
    value = editor.Close()
    pump_events()

    # Then
    assert value == "after"
    assert not editor
