from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("wx")
import wx

from phatch.lib.pyWx import imageFileBrowser, popup

from .native_popup_support import (
    CallbackLog,
    SelectionDialog,
    panel,
    pump_events,
)

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def test_image_dictionary_button_enables_selects_and_notifies(
    native_frame, native_interaction
):
    # Given
    callback = CallbackLog()
    control = popup.ImageDictionaryFileCtrl.__new__(popup.ImageDictionaryFileCtrl)
    wx.Button.__init__(control, panel(native_frame), label="loading")
    control.value = "before"
    control.title = "Library"
    control.show_path = False
    control.icon_size = (64, 64)
    dialog = SelectionDialog(native_frame, "before")
    popup.ImageDictionaryFileCtrl.dialogs = {"Library": dialog}
    control.SetRelevant(wx.EVT_BUTTON, callback)
    native_interaction.expect_dialog(SelectionDialog, wx.ID_OK, ("selected",))

    # When
    control.OnChange(None, "loaded")
    pump_events()

    # Then
    assert control.IsEnabled()
    assert control.GetValue() == "selected"
    assert control.GetLabel() == "selected"
    assert callback.values == ["selected"]

    dialog.Destroy()
    popup.ImageDictionaryFileCtrl.dialogs.clear()


def test_image_dictionary_cancel_preserves_current_value(
    native_frame, native_interaction
):
    # Given
    control = popup.ImageDictionaryFileCtrl.__new__(popup.ImageDictionaryFileCtrl)
    wx.Button.__init__(control, panel(native_frame), label="current")
    control.value = "current"
    control.title = "Library"
    control.show_path = True
    control.icon_size = (128, 128)
    dialog = SelectionDialog(native_frame, "current")
    popup.ImageDictionaryFileCtrl.dialogs = {"Library": dialog}
    native_interaction.expect_dialog(SelectionDialog, wx.ID_CANCEL)

    # When
    control.OnChange(None)

    # Then
    assert control.GetValue() == "current"
    assert dialog.path_shown

    dialog.Destroy()
    popup.ImageDictionaryFileCtrl.dialogs.clear()


def test_image_dictionary_creates_real_dialog_when_cache_is_empty(
    native_frame, monkeypatch, native_interaction
):
    # Given
    class GeneratedSelectionDialog(SelectionDialog):
        def __init__(self, parent, files, title, size, icon_size):
            super().__init__(parent, next(iter(files)))
            self.SetTitle(title)
            self.SetSize(wx.Size(*size))

    popup.ImageDictionaryFileCtrl.dialogs.clear()
    monkeypatch.setattr(imageFileBrowser, "Dialog", GeneratedSelectionDialog)
    monkeypatch.setattr(popup, "imageFileBrowser", imageFileBrowser, raising=False)
    control = popup.ImageDictionaryFileCtrl.__new__(popup.ImageDictionaryFileCtrl)
    wx.Button.__init__(control, panel(native_frame), label="before")
    control.value = "before"
    control.title = "Generated Library"
    control.show_path = False
    control.icon_size = (64, 64)
    control.dictionary = {"before": "before"}
    native_interaction.expect_dialog(
        GeneratedSelectionDialog, wx.ID_OK, ("selected",)
    )

    # When
    control.OnChange(None)

    # Then
    dialog = popup.ImageDictionaryFileCtrl.dialogs["Generated Library"]
    assert dialog.GetTitle() == "Generated Library"
    assert dialog.GetSize().height == 400
    assert control.GetValue() == "selected"
    assert not dialog.path_shown

    dialog.Destroy()
    popup.ImageDictionaryFileCtrl.dialogs.clear()


def test_font_default_path_falls_back_to_nearest_parent_when_no_font_dir_exists(
    native_frame, tmp_path: Path, monkeypatch
):
    # Given
    monkeypatch.setattr(popup, "FONT_PATHS", [str(tmp_path / "absent")])
    control = popup.FontFileCtrl(
        panel(native_frame),
        "missing-font",
        (320, 28),
        {"missing-font": str(tmp_path / "nested" / "missing.ttf")},
    )

    # When
    default_path = control.GetDefaultPath(str(tmp_path / "nested" / "missing.ttf"))

    # Then
    assert default_path == str(tmp_path)

    control.Close()


def test_autocomplete_dictionary_and_folder_controls_close_event_bindings(
    native_frame, tmp_path: Path
):
    # Given
    folder = popup.AutoCompleteFolderCtrl(
        panel(native_frame),
        str(tmp_path),
        (320, 28),
        choices=[str(tmp_path), str(tmp_path / "other")],
    )
    dictionary = popup.AutoCompleteDictionaryFileCtrl(
        panel(native_frame),
        "first",
        (320, 28),
        {"first": str(tmp_path / "first.png")},
    )

    # When
    folder.Close()
    dictionary.Close()

    # Then
    assert folder.GetValue() == str(tmp_path)
    assert dictionary.GetValue() == "first"



def test_font_control_uses_existing_font_directory(native_frame, tmp_path: Path):
    # Given
    font_dir = tmp_path / "fonts"
    font_dir.mkdir()
    font_path = font_dir / "font.ttf"
    control = popup.FontFileCtrl(
        panel(native_frame),
        str(font_path),
        (320, 28),
        {str(font_path): str(font_path)},
    )

    # When
    default_path = control.GetDefaultPath(str(font_path))

    # Then
    assert default_path == str(font_dir)

    control.Close()


@pytest.mark.parametrize(
    ("minimum", "maximum", "value", "expected"),
    [
        (None, None, "bad", (0, 100)),
        (None, 10, "12", (9, 10)),
        (5, None, "4", (5, 6)),
        (7, 7, "7", (7, 8)),
    ],
)
def test_slider_bounds_resolve_missing_and_invalid_metadata(
    minimum, maximum, value, expected
):
    # Given / When
    resolved = popup.SliderCtrl._resolve_bounds(minimum, maximum, value)

    # Then
    assert resolved == expected


def test_edit_panels_render_choice_boolean_and_slider_values(native_frame):
    # Given
    choice = popup.EditPanel(
        panel(native_frame),
        "Choice",
        "one",
        {"choices": ["one", "two"]},
        size=(300, 28),
    )
    boolean = popup.EditPanel(
        panel(native_frame), "Boolean", "yes", {}, size=(300, 28), border=1
    )
    slider = popup.EditPanel(
        panel(native_frame),
        "Slider",
        "5",
        {"minValue": 0, "maxValue": 10},
        size=(300, 28),
        offset=8,
        label="Amount: ",
    )

    # When
    values = [choice.Close(), boolean.Close(), slider.Close()]
    pump_events()

    # Then
    assert values == ["one", "yes", "5"]
