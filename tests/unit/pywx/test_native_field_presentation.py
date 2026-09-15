from __future__ import annotations

from dataclasses import dataclass

import pytest

from phatch.lib import formField
from phatch.lib.pyWx import popup
from phatch.services.action_schema import normalize_identifier
from phatch.services.field_presentation import describe_field
from phatch.services.field_presentation_audit import (
    audit_builtin_presentations,
)
from phatch.services.field_presentation_types import EditorFamily

from .native_popup_support import pump_events
from .native_tree_support import (
    NativeTreeHarness,
    requires_native_display,
)
from .native_tree_support import native_tree as native_tree
from .native_tree_support import wx_app as wx_app

pytestmark = [pytest.mark.unit, pytest.mark.requires_display, requires_native_display]


@dataclass(frozen=True, slots=True)
class EditorCase:
    family: EditorFamily
    action_label: str
    field_label: str
    control_type: type
    initial_values: tuple[tuple[str, str], ...] = ()


EDITOR_CASES = (
    EditorCase(EditorFamily.TEXT, "Write Tag", "Value", popup.TextCtrl),
    EditorCase(EditorFamily.NUMBER, "Canvas", "Resolution", popup.TextCtrl),
    EditorCase(EditorFamily.BOOLEAN, "Contour", "Include image", popup.BooleanCtrl),
    EditorCase(EditorFamily.CHOICE, "Border", "Method", popup.ChoiceCtrl),
    EditorCase(EditorFamily.FILE, "Geotag", "GPS Data (gpx)", popup.LabelFileCtrl),
    EditorCase(EditorFamily.FOLDER, "Save", "In", popup.ChoiceCtrl),
    EditorCase(EditorFamily.FONT_FILE, "Text", "Font", popup.FontFileCtrl),
    EditorCase(
        EditorFamily.IMAGE_FILE,
        "Watermark",
        "Mark",
        popup.ImageDictionaryFileCtrl,
    ),
    EditorCase(
        EditorFamily.IMAGE_CATALOG,
        "Perspective",
        "Projection",
        popup.ImageDictionaryFileCtrl,
    ),
    EditorCase(EditorFamily.COLOR, "Border", "Color", popup.ColorCtrl),
    EditorCase(EditorFamily.PIXEL, "Crop", "All", popup.PixelCtrl),
    EditorCase(
        EditorFamily.FILE_SIZE,
        "Save",
        "JPEG Size Maximum",
        popup.FileSizeCtrl,
        (("Show Type Options", "yes"),),
    ),
    EditorCase(EditorFamily.SLIDER, "Border", "Opacity", popup.SliderCtrl),
)


def _append_field(native_tree: NativeTreeHarness, editor_case: EditorCase):
    from phatch.core import api

    actions = api.ACTIONS
    if actions is None:
        pytest.fail("action registry was not initialized")
    form = actions[editor_case.action_label]()
    for field_label, value in editor_case.initial_values:
        form._fields[field_label].set_as_string(value)
    action = native_tree.tree.append_form(form)
    return next(
        item
        for item in native_tree.fields(action)
        if native_tree.tree.GetItemData(item)[0] == editor_case.field_label
    )


@pytest.mark.parametrize(
    "editor_case",
    EDITOR_CASES,
)
def test_descriptor_routes_native_editor_family_and_translated_help(
    native_tree: NativeTreeHarness,
    editor_case: EditorCase,
) -> None:
    # Given
    field = _append_field(native_tree, editor_case)

    # When
    native_tree.tree.create_popup(field)
    panel = native_tree.tree.popup
    form = native_tree.tree.GetItemData(native_tree.tree.GetItemParent(field))
    descriptor = describe_field(
        normalize_identifier(form.label),
        normalize_identifier(editor_case.field_label),
        editor_case.field_label,
        native_tree.tree.get_form_field(field),
    )

    # Then
    assert panel is not None
    assert isinstance(panel.edit, editor_case.control_type)
    assert panel.GetToolTipText()
    assert descriptor.editor is editor_case.family
    native_tree.tree.close_popup()


def test_runtime_inventory_exercises_every_builtin_editor_family(project_root) -> None:
    # Given
    audit = audit_builtin_presentations(project_root / "phatch" / "actions")

    # When
    runtime_families = {descriptor.editor for descriptor in audit.descriptors.values()}

    # Then
    assert runtime_families == {case.family for case in EDITOR_CASES}
    assert runtime_families == set(EditorFamily) - {EditorFamily.FLOAT_SLIDER}


def test_supported_float_slider_family_constructs_native_control(
    native_tree: NativeTreeHarness,
) -> None:
    from phatch.actions.border import Action

    # Given
    form = Action()
    form._fields["Opacity"] = formField.FloatSliderField("50", 0, 100)
    action = native_tree.tree.append_form(form)
    field = next(
        item
        for item in native_tree.fields(action)
        if native_tree.tree.GetItemData(item)[0] == "Opacity"
    )

    # When
    native_tree.tree.create_popup(field)

    # Then
    panel = native_tree.tree.popup
    assert panel is not None
    assert isinstance(panel.edit, popup.FloatSliderCtrl)
    assert {case.family for case in EDITOR_CASES} | {EditorFamily.FLOAT_SLIDER} == set(
        EditorFamily
    )
    native_tree.tree.close_popup()


def test_control_factory_rejects_unknown_family_instead_of_text_fallback(
    native_frame,
) -> None:
    # Given / When / Then
    with pytest.raises(popup.UnsupportedEditorError, match="UnknownNative"):
        popup.ctrl_factory("UnknownNative", None)


def test_unknown_plugin_field_fails_visibly_without_constructing_editor(
    native_tree: NativeTreeHarness,
) -> None:
    from phatch.core import api

    # Given
    actions = api.ACTIONS
    if actions is None:
        pytest.fail("action registry was not initialized")
    action = native_tree.tree.append_form(actions["Border"]())
    field = native_tree.fields(action)[0]
    native_tree.tree.GetItemData(action).label = "User Plugin"

    # When
    native_tree.tree.create_popup(field)
    pump_events()

    # Then
    assert native_tree.tree.popup is None
    assert "user_plugin" in native_tree.signals.errors[-1]
