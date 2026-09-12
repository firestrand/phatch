from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("wx")
import wx

from phatch.lib.pyWx import popup

from .native_popup_support import (
    CallbackLog,
    SelectionDialog,
    panel,
    pump_events,
)

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def test_choice_without_selection_uses_first_registered_value(native_frame):
    # Given
    control = popup.ChoiceCtrl(
        panel(native_frame), "second", (180, 28), ["first", "second"]
    )

    # When
    control.SetSelection(wx.NOT_FOUND)

    # Then
    assert control.Get() == "first"


@pytest.mark.parametrize(
    "method_name", ["_CreateCtrls", "_CreateEvents", "GetValue", "SetValue"]
)
def test_composed_control_abstract_methods_report_contract(native_frame, method_name):
    # Given
    control = popup._ComposedCtrl.__new__(popup._ComposedCtrl)
    method = getattr(control, method_name)

    # When / Then
    with pytest.raises(popup.NotImplementedError, match=method_name):
        method()


def test_composed_control_abstract_layout_reports_contract(native_frame):
    # Given
    control = popup._ComposedCtrl.__new__(popup._ComposedCtrl)

    # When / Then
    with pytest.raises(popup.NotImplementedError, match="_AddCtrls"):
        control._AddCtrls(wx.BoxSizer(wx.HORIZONTAL), 28)


def test_file_browse_updates_real_path_and_emits_text_event(
    native_frame, tmp_path: Path, native_interaction
):
    # Given
    selected = tmp_path / "selected.png"
    callback = CallbackLog()

    native_interaction.expect_dialog(
        wx.FileDialog, wx.ID_OK, path=str(selected)
    )
    control = popup.FileCtrl(
        panel(native_frame), str(tmp_path), (320, 28), on_change=callback
    )

    # When
    control.OnBrowse(wx.CommandEvent(wx.EVT_BUTTON.typeId, control.browse.GetId()))
    pump_events()

    # Then
    assert control.GetValue() == str(selected)
    assert callback.values[-1] == str(selected)
    assert control.GetWildcard() == "All files|*"


def test_folder_browse_updates_real_path(
    native_frame, tmp_path: Path, native_interaction
):
    # Given
    selected = tmp_path / "selected"
    selected.mkdir()

    native_interaction.expect_dialog(wx.DirDialog, wx.ID_OK, path=str(selected))
    control = popup.FolderCtrl(panel(native_frame), str(tmp_path), (320, 28))

    # When
    control.OnBrowse(wx.CommandEvent(wx.EVT_BUTTON.typeId, control.browse.GetId()))

    # Then
    assert control.GetValue() == str(selected)


def test_image_dictionary_constructor_finishes_loading_with_cached_real_dialog(
    native_frame, native_interaction
):
    # Given
    dialog = SelectionDialog(native_frame, "before")
    popup.ImageDictionaryFileCtrl.dialogs = {"Library": dialog}
    native_interaction.expect_dialog(SelectionDialog, wx.ID_OK, ("selected",))

    # When
    control = popup.ImageDictionaryFileCtrl(
        panel(native_frame),
        "before",
        (180, 28),
        ["png"],
        {"before": "before"},
        "Library",
        show_path=False,
    )
    pump_events()

    # Then
    assert control.IsEnabled()
    assert control.GetValue() == "selected"
    assert control.GetLabel() == "selected"

    dialog.Destroy()
    popup.ImageDictionaryFileCtrl.dialogs.clear()


def test_color_helpers_accept_string_and_tuple_and_paint(native_frame):
    # Given
    control = popup.ColorCtrl(panel(native_frame), "#FFFFFF", (180, 28))

    # When
    string_value = control.GetColorAsString("#123456")
    tuple_colour = control._coerce_colour((1, 2, 3))
    control.Refresh()
    pump_events()

    # Then
    assert string_value == "#123456"
    assert tuple_colour == wx.Colour(1, 2, 3)
    assert control._coerce_colour(tuple_colour) is tuple_colour


def test_color_focus_loss_without_prior_focus_keeps_native_colour(native_frame):
    # Given
    control = popup.ColorCtrl(panel(native_frame), "#FFFFFF", (180, 28))
    del control._base_text_colour
    before = control.GetForegroundColour()

    # When
    control._on_focus_lost(wx.FocusEvent(wx.wxEVT_KILL_FOCUS, control.GetId()))

    # Then
    assert control.GetForegroundColour() == before


def test_font_control_falls_back_to_configured_existing_directory(
    native_frame, tmp_path: Path, monkeypatch
):
    # Given
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    monkeypatch.setattr(popup, "FONT_PATHS", [str(fonts)])
    control = popup.FontFileCtrl(
        panel(native_frame),
        "missing-font",
        (320, 28),
        {"missing-font": str(tmp_path / "missing.ttf")},
    )

    # When
    default_path = control.GetDefaultPath()

    # Then
    assert default_path == str(fonts)

    control.Close()


def test_slider_and_path_controls_apply_background_and_focus(native_frame):
    # Given
    colour = wx.Colour(230, 230, 230)
    slider = popup.SliderCtrl(panel(native_frame), "5", (240, 28))
    path = popup.FileCtrl(panel(native_frame), "file.png", (320, 28))

    # When
    slider.SetBackgroundColour(colour)
    slider.SetFocus()
    path.SetBackgroundColour(colour)
    path.SetFocus()

    # Then
    assert slider.slider.GetBackgroundColour() == colour
    assert path.browse.GetBackgroundColour() == colour


def test_factory_handles_known_control_and_mixin_list(native_frame):
    # Given
    class FirstMixin:
        marker = "first"

    class SecondMixin:
        marker_two = "second"

    # When
    generated = popup.ctrl_factory("Boolean", [FirstMixin, SecondMixin])
    known = popup.ctrl_factory("Boolean", None)
    control = generated(panel(native_frame), True, (180, 28))

    # Then
    assert known is popup.BooleanCtrl
    assert control.marker == "first"
    assert control.marker_two == "second"
    assert control.Get() == "yes"


def test_text_control_explicit_style_and_change_without_callback(native_frame):
    # Given
    control = popup.TextCtrl(
        panel(native_frame),
        "",
        choices=[],
        on_change=None,
        style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
    )

    # When
    event = wx.CommandEvent(wx.EVT_TEXT.typeId, control.GetId())
    event.SetEventObject(control)
    control.OnChange(event)
    control.OnAfterChange()

    # Then
    assert control.GetWindowStyleFlag() & wx.TE_PROCESS_ENTER


def test_long_extension_list_uses_compact_wildcard_label(native_frame):
    # Given
    extensions = ["a", "b", "c", "d", "e"]
    control = popup.LabelFileCtrl(
        panel(native_frame), "file.a", (320, 28), extensions=extensions
    )

    # When
    wildcard = control.GetWildcard()

    # Then
    assert wildcard.startswith("Selection|")
    assert "Selection (" not in wildcard


def test_cancelled_file_and_folder_dialogs_preserve_values(
    native_frame, tmp_path: Path, native_interaction
):
    # Given
    native_interaction.expect_dialog(wx.FileDialog, wx.ID_CANCEL)
    native_interaction.expect_dialog(wx.DirDialog, wx.ID_CANCEL)
    file_control = popup.FileCtrl(panel(native_frame), "before.png", (320, 28))
    folder_control = popup.FolderCtrl(panel(native_frame), str(tmp_path), (320, 28))

    # When
    file_control.OnBrowse(wx.CommandEvent())
    folder_control.OnBrowse(wx.CommandEvent())

    # Then
    assert file_control.GetValue() == "before.png"
    assert folder_control.GetValue() == str(tmp_path)


def test_edit_panel_closes_nested_autocomplete_control(native_frame, tmp_path: Path):
    # Given
    editor = popup.EditPanel(
        panel(native_frame),
        "FontFile",
        str(tmp_path / "font.ttf"),
        {"dictionary": {"font": str(tmp_path / "font.ttf")}},
        size=(320, 28),
    )

    # When
    value = editor.Close()
    pump_events()

    # Then
    assert value == str(tmp_path / "font.ttf")


def test_plain_path_variants_cover_controls_without_autocomplete_events(native_frame):
    # Given
    class CompatibleTextCtrl(wx.TextCtrl):
        def __init__(self, parent, id, value, choices=None, **options):
            super().__init__(parent, id, value, **options)

    class PlainFolder(popup.AutoCompleteFolderCtrl):
        InputCtrl = CompatibleTextCtrl

    class PlainDictionary(popup.AutoCompleteDictionaryFileCtrl):
        InputCtrl = CompatibleTextCtrl

    # When
    folder = PlainFolder(panel(native_frame), "folder", (320, 28))
    dictionary = PlainDictionary(
        panel(native_frame), "entry", (320, 28), {"entry": "entry"}
    )

    # Then
    assert folder.GetValue() == "folder"
    assert dictionary.GetValue() == "entry"


def test_font_existing_default_and_destroyed_editor_cover_teardown_branches(
    native_frame, tmp_path: Path
):
    # Given
    control = popup.FontFileCtrl(
        panel(native_frame),
        "font",
        (320, 28),
        {"font": str(tmp_path / "font.ttf")},
    )
    editor = popup.EditPanel(
        panel(native_frame), "Text", "value", {}, size=(300, 28)
    )

    # When
    default_path = control.GetDefaultPath(str(tmp_path))
    editor.Destroy()
    pump_events()
    closed_again = editor.Close()

    # Then
    assert default_path == str(tmp_path)
    assert closed_again is None

    control.Close()


def test_color_paint_without_overlay_text_uses_native_swatch_only(native_frame):
    # Given
    control = popup.ColorCtrl(panel(native_frame), "#FFFFFF", (180, 28))
    del control._hex_text

    # When
    control.Refresh()
    pump_events()

    # Then
    assert control.GetBackgroundColour() == wx.Colour(255, 255, 255)
