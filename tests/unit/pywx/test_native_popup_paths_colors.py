from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("wx")
import wx
import wx.lib.colourselect as colourselect

from phatch.lib.pyWx import popup

from .native_popup_support import CallbackLog, panel, pump_events

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def test_forced_sizer_applies_requested_native_control_height(native_frame):
    # Given
    button = wx.Button(panel(native_frame), label="Browse")
    sizer = popup.ForcedBoxSizer(wx.HORIZONTAL, 28, border=2)

    # When
    sizer.AddForced(button, 1)

    # Then
    assert button.GetMinSize().height == 20


def test_abstract_composed_control_reports_missing_widget_contract(native_frame):
    # Given
    control = popup._ComposedCtrl.__new__(popup._ComposedCtrl)

    # When
    error = popup.NotImplementedError(control, "GetValue")

    # Then
    assert str(error) == 'Class "_ComposedCtrl" did not implement method "GetValue".'


def test_path_control_walks_to_existing_parent_and_round_trips_value(
    native_frame, tmp_path: Path
):
    # Given
    missing = tmp_path / "missing" / "photo.png"
    control = popup.FileCtrl(panel(native_frame), str(missing), (320, 28))

    # When
    default_path = control.GetDefaultPath()
    control.SetValue(str(tmp_path / "next.png"))
    control.SetFocus()

    # Then
    assert default_path == str(tmp_path)
    assert control.GetValue() == str(tmp_path / "next.png")
    assert control.browse.IsEnabled()


@pytest.mark.parametrize(
    ("extensions", "expected"),
    [
        (
            ("png", "jpg"),
            "Selection (png,jpg)|*.png;*.PNG;*.Png;*.jpg;*.JPG;*.Jpg|All files|*",
        ),
        ((), "All files|*"),
    ],
)
def test_label_file_control_builds_native_dialog_wildcard(
    native_frame, extensions, expected
):
    # Given
    control = popup.LabelFileCtrl(
        panel(native_frame), "photo.png", (320, 28), extensions=extensions
    )

    # When
    wildcard = control.GetWildcard()

    # Then
    assert wildcard == expected


def test_dictionary_file_uses_mapped_path_for_default(native_frame, tmp_path: Path):
    # Given
    target = tmp_path / "library" / "photo.png"
    target.parent.mkdir()
    control = popup.DictionaryFileCtrl(
        panel(native_frame),
        "library photo",
        (320, 28),
        {"library photo": str(target)},
    )

    # When
    default_path = control.GetDefaultPath()

    # Then
    assert default_path == str(target.parent)

    control.Close()


def test_color_control_updates_label_contrast_and_focus_state(native_frame):
    # Given
    control = popup.ColorCtrl(panel(native_frame), "#FFFFFF", (160, 28))
    focus = wx.FocusEvent(wx.wxEVT_SET_FOCUS, control.GetId())
    blur = wx.FocusEvent(wx.wxEVT_KILL_FOCUS, control.GetId())

    # When
    control.SetValue((0, 0, 0))
    control._on_focus(focus)
    control._on_focus_lost(blur)
    pump_events()

    # Then
    assert control.GetValue() == "#000000"
    assert control.GetLabel() == "#000000"
    assert control.GetBackgroundColour() == wx.Colour(0, 0, 0)
    assert control.GetForegroundColour() == wx.Colour(255, 255, 255)


def test_color_selection_event_changes_rendered_value(native_frame):
    # Given
    control = popup.ColorCtrl(panel(native_frame), "#000000", (160, 28))
    event = colourselect.ColourSelectEvent(control.GetId(), wx.Colour(12, 34, 56))

    # When
    control.OnSelectColor(event)

    # Then
    assert control.GetValue() == "#0c2238"
    assert control.GetLabel() == "#0c2238"


def test_control_factory_caches_dynamic_mixin_and_falls_back_to_text(native_frame):
    # Given
    class TranslationMixin:
        _to_local = staticmethod(lambda value: f"local:{value}")
        _to_english = staticmethod(lambda value: value.removeprefix("local:"))

    # When
    generated = popup.ctrl_factory("UnknownNative", TranslationMixin)
    cached = popup.ctrl_factory("UnknownNative", TranslationMixin)
    control = generated(panel(native_frame), "value")

    # Then
    assert generated is cached
    assert control.GetValue() == "local:value"
    assert control.Get() == "value"


def test_image_dictionary_control_starts_disabled_until_loaded(native_frame):
    # Given
    callback = CallbackLog()
    control = popup.ImageDictionaryFileCtrl.__new__(popup.ImageDictionaryFileCtrl)
    wx.Button.__init__(control, panel(native_frame), label="loading")
    control.value = "before"
    control.SetRelevant(wx.EVT_BUTTON, callback)

    # When
    control.Disable()
    control.SetValue("after")

    # Then
    assert control.GetValue() == "after"
    assert control.GetLabel() == "after"
    assert not control.IsEnabled()


def test_path_control_supports_native_text_input(native_frame):
    # Given
    class NativeTextFileCtrl(popup.FileCtrl):
        InputCtrl = wx.TextCtrl

    # When
    control = NativeTextFileCtrl(panel(native_frame), "photo.png", (320, 28))

    # Then
    assert control.GetValue() == "photo.png"


def test_gtk_layout_adjusts_path_border_and_pixel_unit_width(native_frame, monkeypatch):
    # Given
    monkeypatch.setattr(popup.wx, "Platform", "__WXGTK__")

    # When
    path_control = popup.FileCtrl(panel(native_frame), "photo.png", (320, 28))
    pixel_control = popup.PixelCtrl(panel(native_frame), "25%", (180, 28))

    # Then
    assert path_control.GetValue() == "photo.png"
    assert pixel_control.GetValue() == "25 %"


def test_windows_slider_applies_background_to_spin_control(native_frame, monkeypatch):
    # Given
    monkeypatch.setattr(popup.wx, "Platform", "__WXMSW__")
    control = popup.SliderCtrl(panel(native_frame), "5", (240, 28))
    colour = wx.Colour(220, 220, 220)

    # When
    control.SetBackgroundColour(colour)

    # Then
    assert control.slider.GetBackgroundColour() == colour


def test_color_label_accepts_html_string(native_frame):
    # Given
    control = popup.ColorCtrl(panel(native_frame), "#FFFFFF", (160, 28))

    # When
    control._apply_label("#010203")

    # Then
    assert control.GetLabel() == "#010203"
    assert control.GetBackgroundColour() == wx.Colour(1, 2, 3)
