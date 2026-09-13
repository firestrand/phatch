from __future__ import annotations

import sys

import pytest

try:
    import wx
except ImportError:
    pytest.skip("wxPython runtime unavailable", allow_module_level=True)

from phatch.lib.pyWx import popup

from .native_popup_support import replace_text
from .native_tree_support import (
    NativeTreeHarness,
    requires_native_display,
    save_and_load,
)
from .native_tree_support import (
    native_tree as native_tree,
)
from .native_tree_support import (
    wx_app as wx_app,
)

pytestmark = [pytest.mark.unit, pytest.mark.requires_display, requires_native_display]


def append_crop(native_tree: NativeTreeHarness) -> wx.TreeItemId:
    from phatch.core import api

    return native_tree.tree.append_form(api.ACTIONS["Crop"]())


def field_by_label(
    native_tree: NativeTreeHarness, action: wx.TreeItemId, label: str
) -> wx.TreeItemId:
    return next(
        item
        for item in native_tree.fields(action)
        if native_tree.tree.GetItemData(item)[0] == label
    )


def test_crop_all_popup_keeps_editable_pixel_control_with_presets(
    native_tree: NativeTreeHarness,
) -> None:
    # Given
    action = append_crop(native_tree)
    amount = field_by_label(native_tree, action, "All")

    # When
    native_tree.tree.create_popup(amount)

    # Then
    edit_panel = native_tree.tree.popup
    assert edit_panel is not None
    editor = edit_panel.edit
    assert isinstance(editor, popup.PixelCtrl)
    assert editor.size.IsEditable()
    assert set(editor.size.GetItems()) >= {"0", "1", "2", "5", "10", "20"}


def test_crop_mode_popup_remains_selection_only(
    native_tree: NativeTreeHarness,
) -> None:
    # Given
    action = append_crop(native_tree)
    mode = field_by_label(native_tree, action, "Mode")

    # When
    native_tree.tree.create_popup(mode)

    # Then
    edit_panel = native_tree.tree.popup
    assert edit_panel is not None
    assert isinstance(edit_panel.edit, popup.ChoiceCtrl)
    assert isinstance(edit_panel.edit, wx.Choice)


def test_crop_mode_pending_choice_commits_when_editor_closes(
    native_tree: NativeTreeHarness, monkeypatch
) -> None:
    # Given
    unhandled: list[BaseException] = []
    monkeypatch.setattr(
        sys, "excepthook", lambda error_type, error, traceback: unhandled.append(error)
    )
    action = append_crop(native_tree)
    mode = field_by_label(native_tree, action, "Mode")
    native_tree.tree.create_popup(mode)
    edit_panel = native_tree.tree.popup
    assert edit_panel is not None
    assert isinstance(edit_panel.edit, popup.ChoiceCtrl)
    edit_panel.edit.SetStringSelection("Custom")
    edit_panel.edit.OnChange()

    # When
    native_tree.tree.close_popup()
    wx.Yield()

    # Then
    crop = native_tree.tree.GetItemData(action)
    assert crop.get_field_string("Mode") == "Custom"
    assert unhandled == []


@pytest.mark.parametrize(
    ("mode", "field_label", "typed_value", "unit", "stored_value"),
    [
        ("All", "All", "7", "px", "7 px"),
        ("Custom", "Left", "13", "%", "13 %"),
    ],
)
def test_typed_crop_amount_commits_and_persists_when_popup_closes(
    native_tree: NativeTreeHarness,
    tmp_path,
    mode: str,
    field_label: str,
    typed_value: str,
    unit: str,
    stored_value: str,
) -> None:
    # Given
    action = append_crop(native_tree)
    mode_item = field_by_label(native_tree, action, "Mode")
    native_tree.tree.set_form_field_value(mode_item, mode)
    native_tree.tree.update_form_relevance(mode_item)
    amount = field_by_label(native_tree, action, field_label)
    native_tree.tree.create_popup(amount)

    # When
    edit_panel = native_tree.tree.popup
    assert edit_panel is not None
    editor = edit_panel.edit
    assert isinstance(editor, popup.PixelCtrl)
    native_tree.frame.Unbind(wx.EVT_LEAVE_WINDOW)
    native_tree.tree.evt_leave_window = False
    replace_text(editor.size, typed_value)
    editor.unit.SetStringSelection(unit)
    native_tree.tree.close_popup()

    # Then
    crop = native_tree.tree.GetItemData(action)
    assert crop.get_field_string(field_label) == stored_value
    loaded = save_and_load(tmp_path / "typed-crop.phatch", [crop])
    assert loaded[0].get_field_string(field_label) == stored_value


def test_invalid_typed_crop_amount_is_rejected_on_popup_close(
    native_tree: NativeTreeHarness,
) -> None:
    # Given
    action = append_crop(native_tree)
    amount = field_by_label(native_tree, action, "All")
    native_tree.tree.create_popup(amount)

    # When
    edit_panel = native_tree.tree.popup
    assert edit_panel is not None
    editor = edit_panel.edit
    assert isinstance(editor, popup.PixelCtrl)
    native_tree.frame.Unbind(wx.EVT_LEAVE_WINDOW)
    native_tree.tree.evt_leave_window = False
    replace_text(editor.size, "not-a-size")
    native_tree.tree.close_popup()

    # Then
    crop = native_tree.tree.GetItemData(action)
    assert crop.get_field_string("All") == "30%"
    assert native_tree.signals.errors
    assert native_tree.signals.dirty == []
