from __future__ import annotations

from pathlib import Path

import pytest
import wx
from PIL import Image

from phatch.lib.pyWx import popup
from phatch.services.field_presentation_types import EditorFamily
from tests.unit.pywx.native_editor_matrix_support import (
    FAMILY_CASES,
    FamilyCase,
    append_case_field,
    post_key,
    set_perspective_path,
)
from tests.unit.pywx.native_popup_support import wait_until

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


INVALID_CASES = tuple(
    case
    for case in FAMILY_CASES
    if case.family
    in {
        EditorFamily.NUMBER,
        EditorFamily.FILE,
        EditorFamily.FONT_FILE,
        EditorFamily.IMAGE_FILE,
        EditorFamily.IMAGE_CATALOG,
        EditorFamily.PIXEL,
        EditorFamily.FILE_SIZE,
        EditorFamily.FLOAT_SLIDER,
    }
)


def _set_invalid(panel, case: FamilyCase, missing: Path) -> None:
    match case.family:
        case EditorFamily.FILE | EditorFamily.FONT_FILE:
            panel.edit.SetValue(str(missing))
        case EditorFamily.IMAGE_FILE | EditorFamily.IMAGE_CATALOG:
            panel.edit.SetValue("Missing Catalog Entry")
        case EditorFamily.PIXEL | EditorFamily.FILE_SIZE:
            panel.edit.size.SetValue("invalid")
        case EditorFamily.FLOAT_SLIDER:
            panel.edit.spin.SetValue("invalid")
        case _:
            panel.edit.SetValue("invalid")


@pytest.mark.parametrize("case", INVALID_CASES, ids=lambda case: case.family.value)
def test_invalid_native_editor_value_retains_document_without_history(
    native_frame_harness,
    native_interaction,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: FamilyCase,
) -> None:
    frame = native_frame_harness.frame
    if case.family is EditorFamily.IMAGE_CATALOG:
        Image.new("RGB", (2, 2)).save(tmp_path / "Left.png")
        set_perspective_path(monkeypatch, tmp_path)
    item = append_case_field(frame, case)
    baseline = frame.controller.current_document
    frame.tree.SelectItem(item)
    wait_until(lambda: frame.tree.popup is not None)
    panel = frame.tree.popup
    assert panel is not None
    _set_invalid(panel, case, tmp_path / "missing")

    if case.family in {EditorFamily.IMAGE_FILE, EditorFamily.IMAGE_CATALOG}:
        event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        event.SetKeyCode(wx.WXK_RETURN)
        panel._OnKey(event)
    else:
        post_key(panel, wx.WXK_RETURN)

    wait_until(lambda: frame.tree.popup is None)
    assert frame.controller.current_document == baseline
    wait_until(lambda: bool(native_frame_harness.dialogs.errors))


def test_noneditable_native_families_reject_arbitrary_text_by_widget_shape(
    native_frame_harness,
) -> None:
    frame = native_frame_harness.frame
    strict = append_case_field(frame, FAMILY_CASES[5])
    frame.tree.SelectItem(strict)
    wait_until(lambda: frame.tree.popup is not None)
    assert isinstance(frame.tree.popup.edit, wx.Choice)
    assert not isinstance(frame.tree.popup.edit, wx.ComboBox)
    frame.tree.cancel_popup()

    boolean = append_case_field(frame, FAMILY_CASES[2])
    frame.tree.SelectItem(boolean)
    wait_until(lambda: frame.tree.popup is not None)
    assert isinstance(frame.tree.popup.edit, wx.CheckBox)
    frame.tree.cancel_popup()

    slider = append_case_field(frame, FAMILY_CASES[12])
    frame.tree.SelectItem(slider)
    wait_until(lambda: frame.tree.popup is not None)
    slider_editor = frame.tree.popup.edit
    assert isinstance(slider_editor, popup.SliderCtrl)
    assert slider_editor.spin.GetMin() == 1
    assert slider_editor.spin.GetMax() == 100
