from __future__ import annotations

import json

import pytest

try:
    import wx
except ImportError:
    pytest.skip("wxPython runtime unavailable", allow_module_level=True)

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


def append_border(native_tree: NativeTreeHarness) -> wx.TreeItemId:
    from phatch.core import api

    return native_tree.tree.append_form(api.ACTIONS["Border"]())


def field_by_label(
    native_tree: NativeTreeHarness, action: wx.TreeItemId, label: str
) -> wx.TreeItemId:
    return next(
        item
        for item in native_tree.fields(action)
        if native_tree.tree.GetItemData(item)[0] == label
    )


def test_append_actual_action_populates_native_items_and_selection(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_border(native_tree)

    assert native_tree.labels() == ["Border"]
    assert native_tree.tree.GetSelection() == action
    assert native_tree.tree.GetItemData(action).label == "Border"
    assert len(native_tree.fields(action)) > 1


def test_edit_valid_field_updates_tree_action_and_dirty_callback(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_border(native_tree)
    field = field_by_label(native_tree, action, "Border Width")

    native_tree.tree.set_form_field_value(field, "42px")

    assert native_tree.tree.GetItemData(field) == ("Border Width", "42px")
    assert (
        native_tree.tree.GetItemData(action).get_field_string("Border Width") == "42px"
    )
    assert native_tree.signals.dirty == [True]


def test_invalid_safe_field_reports_error_without_mutation(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_border(native_tree)
    field = field_by_label(native_tree, action, "Border Width")
    before = native_tree.tree.GetItemData(field)

    native_tree.tree.set_form_field_value(field, "not-a-size")

    assert native_tree.tree.GetItemData(field) == before
    assert native_tree.signals.errors
    assert native_tree.signals.dirty == []


def test_empty_edit_is_stored_as_visible_space(native_tree: NativeTreeHarness) -> None:
    from lib import formField

    action = append_border(native_tree)
    field = field_by_label(native_tree, action, "Border Width")
    formField.set_safe(False)
    try:
        native_tree.tree.set_form_field_value(field, "")
    finally:
        formField.set_safe(True)

    assert native_tree.tree.GetItemData(field) == ("Border Width", " ")
    assert native_tree.signals.errors


def test_toggle_enable_updates_action_and_dirty_callback(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_border(native_tree)
    event = native_tree.event(wx.wxEVT_TREE_ITEM_ACTIVATED, action)

    native_tree.tree.on_item_activated(event)

    assert not native_tree.tree.is_form_enabled(action)
    assert not native_tree.tree.export_form(action).is_enabled()
    assert native_tree.signals.dirty == [True]


def test_field_selection_callback_opens_and_closes_real_popup(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_border(native_tree)
    field = field_by_label(native_tree, action, "Opacity")
    native_tree.tree.SelectItem(field)
    event = native_tree.event(wx.wxEVT_TREE_SEL_CHANGED, field)

    native_tree.tree.on_sel_changed(event)
    assert native_tree.tree.popup is not None
    assert native_tree.tree.is_field_selected()

    native_tree.tree.close_popup()
    assert native_tree.tree.popup is None


def test_remove_selected_action_and_empty_tree_boundary(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_border(native_tree)
    native_tree.tree.SelectItem(action)

    assert native_tree.tree.remove_selected_form()
    assert native_tree.labels() == []
    assert not native_tree.tree.remove_selected_form()


def test_collapse_expand_and_automatic_expansion(
    native_tree: NativeTreeHarness,
) -> None:
    from phatch.core import api

    native_tree.tree.append_forms(
        [api.ACTIONS["Border"](), api.ACTIONS["Scale"](), api.ACTIONS["Save"]()]
    )
    native_tree.tree.collapse_forms()
    assert all(
        not native_tree.tree.IsExpanded(item) for item in native_tree.action_items()
    )

    native_tree.tree.expand_forms()
    assert all(native_tree.tree.IsExpanded(item) for item in native_tree.action_items())

    native_tree.tree.enable_collapse_automatic(True)
    assert native_tree.tree.collapse_automatic
    native_tree.tree.enable_collapse_automatic(False)
    assert not native_tree.tree.collapse_automatic


def test_actual_actions_round_trip_through_temp_file_and_new_tree(
    native_tree: NativeTreeHarness, tmp_path
) -> None:
    from phatch.core import api

    actions = [api.ACTIONS["Border"](), api.ACTIONS["Save"]()]
    actions[0].set_field_as_string("Border Width", "17 px")
    path = tmp_path / "native-tree.phatch"

    loaded = save_and_load(path, actions)
    serialized = json.loads(path.read_text(encoding="utf-8"))
    native_tree.tree.append_forms(loaded)

    assert serialized["actions"][0]["fields"]["border_width"] == "17 px"
    assert native_tree.labels() == ["Border", "Save"]
    assert (
        native_tree.tree.export_forms()[0].get_field_string("Border Width") == "17 px"
    )


def test_selection_helpers_distinguish_action_and_field(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_border(native_tree)
    field = native_tree.fields(action)[0]

    assert native_tree.tree.is_form(action)
    assert native_tree.tree.is_field(field)
    assert native_tree.tree.get_form_item(field) == action
    assert native_tree.tree.get_last_form() == action
