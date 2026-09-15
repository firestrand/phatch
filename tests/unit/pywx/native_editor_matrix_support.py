from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import wx

from phatch.core import api
from phatch.lib.pyWx import treeEdit
from phatch.services.field_presentation_types import EditorFamily

from .native_popup_support import pump_events


@dataclass(frozen=True, slots=True)
class FamilyCase:
    family: EditorFamily
    action: str
    field: str
    value: str
    expected: str
    prerequisite: tuple[str, str] | None = None


FAMILY_CASES = (
    FamilyCase(EditorFamily.TEXT, "Write Tag", "Value", "Matrix", "Matrix"),
    FamilyCase(EditorFamily.NUMBER, "Canvas", "Resolution", "144", "144"),
    FamilyCase(EditorFamily.BOOLEAN, "Contour", "Include image", "no", "no"),
    FamilyCase(
        EditorFamily.CHOICE,
        "Border",
        "Method",
        "Different for each side",
        "Different for each side",
    ),
    FamilyCase(
        EditorFamily.FILE,
        "Geotag",
        "GPS Data (gpx)",
        "matrix.gpx",
        "matrix.gpx",
    ),
    FamilyCase(EditorFamily.FOLDER, "Save", "In", "<desktop>", "<desktop>"),
    FamilyCase(EditorFamily.FONT_FILE, "Text", "Font", "Andale Mono", "Andale Mono"),
    FamilyCase(EditorFamily.IMAGE_FILE, "Watermark", "Mark", "Phatch", "Phatch"),
    FamilyCase(
        EditorFamily.IMAGE_CATALOG,
        "Perspective",
        "Projection",
        "Right",
        "Right",
    ),
    FamilyCase(EditorFamily.COLOR, "Border", "Color", "#000000", "#000000"),
    FamilyCase(EditorFamily.PIXEL, "Crop", "All", "7 px", "7 px"),
    FamilyCase(
        EditorFamily.FILE_SIZE,
        "Save",
        "JPEG Size Maximum",
        "10 kb",
        "10 kb",
        ("Show Type Options", "yes"),
    ),
    FamilyCase(EditorFamily.SLIDER, "Border", "Opacity", "50", "50"),
    FamilyCase(EditorFamily.FLOAT_SLIDER, "Border", "Opacity", "50.5", "50.5"),
)


def append_case_field(frame, case: FamilyCase):
    form = api.ACTIONS[case.action]()
    if case.prerequisite is not None:
        label, value = case.prerequisite
        form._fields[label].set_as_string(value)
    if case.family is EditorFamily.FLOAT_SLIDER:
        vars(form)["_fields"][case.field] = treeEdit.formField.FloatSliderField(
            "25.5", 0, 100
        )
    transaction = frame.controller.begin_transaction()
    frame.tree.append_form(form)
    frame.controller.commit_transaction(transaction)
    frame.enable_actions(True)
    frame.Layout()
    pump_events()
    return find_case_field(frame, case)


def find_case_field(frame, case: FamilyCase):
    action = frame.tree.GetLastChild(frame.tree.GetRootItem())
    return next(
        item
        for item in frame.tree.GetItemChildren(action)
        if frame.tree.GetItemData(item)[0] == case.field
    )


def set_perspective_path(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    field = api.ACTIONS["Perspective"]()._fields["Projection"]
    initializer = vars(type(field))["init_dictionary"]
    paths = initializer.__globals__["PATHS"]
    get_path = paths.__class__.__getitem__
    monkeypatch.setattr(
        paths.__class__,
        "__getitem__",
        lambda values, key: (
            str(path) if key == "PHATCH_PERSPECTIVE_PATH" else get_path(values, key)
        ),
    )


def set_editor(panel, case: FamilyCase) -> None:
    editor = panel.edit
    match case.family:
        case EditorFamily.BOOLEAN:
            editor.SetValue(False)
        case EditorFamily.CHOICE | EditorFamily.FOLDER:
            editor.Set(case.value)
        case EditorFamily.PIXEL | EditorFamily.FILE_SIZE:
            size, unit = case.value.split()
            editor.size.SetValue(size)
            editor.unit.SetStringSelection(unit)
        case EditorFamily.SLIDER:
            editor.spin.SetValue(int(case.value))
            editor.OnSpin(None)
        case EditorFamily.FLOAT_SLIDER:
            editor.spin.SetValue(case.value)
        case _:
            editor.SetValue(case.value)


def post_key(panel, key_code: int) -> None:
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(key_code)
    wx.PostEvent(panel, event)
    pump_events()
