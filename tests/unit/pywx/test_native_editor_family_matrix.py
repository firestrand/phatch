from __future__ import annotations

import builtins
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
    set_editor,
    set_perspective_path,
)
from tests.unit.pywx.native_popup_support import (
    SelectionDialog,
    pump_events,
    wait_until,
)
from tests.unit.pywx.native_tree_support import save_and_load

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


@pytest.mark.parametrize("case", FAMILY_CASES, ids=lambda case: case.family.value)
@pytest.mark.parametrize("commit_route", ["enter", "focus"])
def test_every_native_editor_family_commits_history_and_schema_round_trip(
    native_frame_harness,
    native_interaction,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: FamilyCase,
    commit_route: str,
) -> None:
    frame = native_frame_harness.frame
    if case.family is EditorFamily.FILE:
        file_path = tmp_path / "matrix.gpx"
        file_path.touch()
        case = FamilyCase(
            case.family,
            case.action,
            case.field,
            str(file_path),
            str(file_path),
        )
    if case.family is EditorFamily.IMAGE_CATALOG:
        for name in ("Left", "Right"):
            Image.new("RGB", (2, 2)).save(tmp_path / f"{name}.png")
        set_perspective_path(monkeypatch, tmp_path)
    item = append_case_field(frame, case)
    baseline = frame.controller.current_document
    monkeypatch.setattr(builtins, "_", lambda text: f"xx:{text}")
    frame.tree.SelectItem(item)
    wait_until(lambda: frame.tree.popup is not None)
    panel = frame.tree.popup
    assert panel is not None
    assert panel.GetToolTipText().startswith("xx:")
    assert panel.labelCtrl.GetLabel().startswith("xx:")
    if case.family in {EditorFamily.FONT_FILE, EditorFamily.IMAGE_FILE}:
        current = panel.edit.GetValue()
        selected = next(
            value for value in sorted(panel.edit.dictionary) if value != current
        )
        case = FamilyCase(case.family, case.action, case.field, selected, selected)
    if case.family in {EditorFamily.IMAGE_FILE, EditorFamily.IMAGE_CATALOG}:
        title = panel.edit.title
        dialog = SelectionDialog(frame, panel.edit.GetValue())
        popup.ImageDictionaryFileCtrl.dialogs[title] = dialog
        native_interaction.expect_dialog(SelectionDialog, wx.ID_OK, (case.value,))
        pump_events()
        if frame.tree.popup is not None:
            if commit_route == "enter":
                post_key(panel, wx.WXK_RETURN)
            else:
                frame.tree.SelectItem(frame.tree.GetItemParent(item))
        wait_until(lambda: frame.tree.popup is None)
        popup.ImageDictionaryFileCtrl.dialogs.pop(title).Destroy()
    else:
        set_editor(panel, case)
        if commit_route == "enter":
            post_key(panel, wx.WXK_RETURN)
        else:
            frame.tree.SelectItem(frame.tree.GetItemParent(item))
        wait_until(lambda: frame.tree.popup is None)

    form = next(iter(frame.controller.export_actions()))
    assert form.get_field_string(case.field) == case.expected
    committed = frame.controller.current_document
    assert frame.controller.undo()
    assert frame.controller.current_document == baseline
    assert frame.controller.redo()
    assert frame.controller.current_document == committed
    loaded = save_and_load(
        tmp_path / f"{case.family.value}-{commit_route}.phatch",
        [form],
    )
    assert loaded[0].get_field_string(case.field) == case.expected


@pytest.mark.parametrize("case", FAMILY_CASES, ids=lambda case: case.family.value)
def test_every_native_editor_family_escape_restores_exact_document(
    native_frame_harness,
    native_interaction,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: FamilyCase,
) -> None:
    frame = native_frame_harness.frame
    if case.family is EditorFamily.IMAGE_CATALOG:
        for name in ("Left", "Right"):
            Image.new("RGB", (2, 2)).save(tmp_path / f"{name}.png")
        set_perspective_path(monkeypatch, tmp_path)
    item = append_case_field(frame, case)
    baseline = frame.controller.current_document
    frame.tree.SelectItem(item)
    wait_until(lambda: frame.tree.popup is not None)
    panel = frame.tree.popup
    assert panel is not None
    if case.family in {EditorFamily.IMAGE_FILE, EditorFamily.IMAGE_CATALOG}:
        title = panel.edit.title
        dialog = SelectionDialog(frame, panel.edit.GetValue())
        popup.ImageDictionaryFileCtrl.dialogs[title] = dialog
        native_interaction.expect_dialog(SelectionDialog, wx.ID_CANCEL)
        pump_events()
        popup.ImageDictionaryFileCtrl.dialogs.pop(title).Destroy()
    if frame.tree.popup is not None:
        panel = frame.tree.popup
        assert panel is not None
        set_editor(panel, case)
        post_key(panel, wx.WXK_ESCAPE)

    wait_until(lambda: frame.tree.popup is None)
    assert frame.controller.current_document == baseline


def test_strict_choice_and_editable_preset_are_distinct_native_widgets(
    native_frame_harness,
) -> None:
    frame = native_frame_harness.frame
    strict = append_case_field(frame, FAMILY_CASES[5])
    frame.tree.SelectItem(strict)
    wait_until(lambda: frame.tree.popup is not None)
    assert isinstance(frame.tree.popup.edit, wx.Choice)
    assert not isinstance(frame.tree.popup.edit, wx.ComboBox)
    frame.tree.cancel_popup()

    editable = append_case_field(frame, FAMILY_CASES[10])
    frame.tree.SelectItem(editable)
    wait_until(lambda: frame.tree.popup is not None)
    editor = frame.tree.popup.edit
    assert isinstance(editor, popup.PixelCtrl)
    assert editor.size.IsEditable()
    assert set(editor.size.GetItems()) >= {"0", "1", "2", "5", "10", "20"}


def test_invalid_editable_native_value_retains_document_and_history(
    native_frame_harness,
) -> None:
    frame = native_frame_harness.frame
    case = FAMILY_CASES[10]
    item = append_case_field(frame, case)
    baseline = frame.controller.current_document
    frame.tree.SelectItem(item)
    wait_until(lambda: frame.tree.popup is not None)
    panel = frame.tree.popup
    panel.edit.size.SetValue("invalid")

    post_key(panel, wx.WXK_RETURN)

    wait_until(lambda: frame.tree.popup is None)
    assert frame.controller.current_document == baseline
    assert native_frame_harness.dialogs.errors
