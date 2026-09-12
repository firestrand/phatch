from __future__ import annotations

import pytest

try:
    import wx
except ImportError:
    pytest.skip("wxPython runtime unavailable", allow_module_level=True)

from .native_tree_support import (
    NativeTreeHarness,
    requires_native_display,
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


def test_dirty_model_field_refreshes_native_item(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_border(native_tree)
    width = field_by_label(native_tree, action, "Border Width")
    form = native_tree.tree.GetItemData(action)
    form._get_field("Border Width").set_as_string_dirty("23px")

    visible = native_tree.tree.get_form_fields_visible(action, form)

    assert native_tree.tree.GetItemData(width) == ("Border Width", "23px")
    assert any(entry[0] == width for entry in visible)


def test_selected_action_boundaries_and_append(native_tree: NativeTreeHarness) -> None:
    action = append_border(native_tree)
    native_tree.tree.SelectItem(action)

    native_tree.tree.create_popup_selected()
    native_tree.tree.set_form_field_value_selected("ignored")
    inserted = native_tree.tree.append_form_by_label_to_selected("Scale")

    assert native_tree.tree.popup is None
    assert native_tree.tree.GetItemText(inserted) == "Scale"

    native_tree.tree.Unbind(wx.EVT_TREE_SEL_CHANGED)
    empty_field = native_tree.tree.AppendItem(action, "No data")
    native_tree.tree.SelectItem(empty_field)
    native_tree.tree.set_form_field_value_selected("ignored")
    assert native_tree.tree.GetItemData(empty_field) is None


def test_root_toggle_and_action_selection_callbacks(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_border(native_tree)
    root_event = native_tree.event(
        wx.wxEVT_TREE_ITEM_ACTIVATED, native_tree.tree.GetRootItem()
    )
    native_tree.tree.toggle_form_item(native_tree.tree.GetRootItem(), root_event)
    native_tree.tree.enable_collapse_automatic(True)
    native_tree.tree.Collapse(action)

    native_tree.tree.on_sel_changed(
        native_tree.event(wx.wxEVT_TREE_SEL_CHANGED, action)
    )

    assert root_event.GetSkipped()
    assert native_tree.tree.IsExpanded(action)


def test_toggle_disabled_action_and_missing_image_branches(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_border(native_tree)
    event = native_tree.event(wx.wxEVT_TREE_ITEM_ACTIVATED, action)
    native_tree.tree.toggle_form_item(action, event)
    native_tree.tree.toggle_form_item(action, event)
    image_free = native_tree.tree.AppendItem(native_tree.tree.GetRootItem(), "No image")

    native_tree.tree.toggle_form_item(
        image_free,
        native_tree.event(wx.wxEVT_TREE_ITEM_ACTIVATED, image_free),
    )

    assert native_tree.tree.is_form_enabled(action) is True


def test_popup_and_collapse_idempotent_branches(native_tree: NativeTreeHarness) -> None:
    action = append_border(native_tree)
    field = field_by_label(native_tree, action, "Method")

    native_tree.tree.resize_popup()
    native_tree.tree.enable_collapse_automatic(False)
    native_tree.tree.enable_collapse_automatic(True)
    native_tree.tree.enable_collapse_automatic(True)
    native_tree.tree.SelectItem(field)
    native_tree.tree.create_popup_selected()
    native_tree.tree.popup.edit.OnAfterChange()
    native_tree.tree.close_popup()

    assert native_tree.tree.popup is None
