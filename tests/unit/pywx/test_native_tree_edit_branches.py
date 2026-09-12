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


def append_action(native_tree: NativeTreeHarness, label: str) -> wx.TreeItemId:
    from phatch.core import api

    return native_tree.tree.append_form(api.ACTIONS[label]())


def field_by_label(
    native_tree: NativeTreeHarness, action: wx.TreeItemId, label: str
) -> wx.TreeItemId:
    return next(
        item
        for item in native_tree.fields(action)
        if native_tree.tree.GetItemData(item)[0] == label
    )


def test_small_helpers_cover_defaults_and_image_scaling(
    native_tree: NativeTreeHarness,
) -> None:
    from phatch.lib.pyWx import treeEdit

    image = wx.Image(4, 4)
    treeEdit.rescale(image, 2, 3)

    assert image.GetSize() == wx.Size(2, 3)
    assert treeEdit.get_index([("item", "label", "value")], 0) == (
        "item",
        "label",
        "value",
    )
    assert treeEdit.get_index([], 0) == (None, None, None)
    assert treeEdit._do_nothing() is None


def test_append_by_label_at_position_and_last(native_tree: NativeTreeHarness) -> None:
    first = append_action(native_tree, "Border")
    native_tree.tree.append_form_by_label(first, "Scale")
    native_tree.tree.append_form_by_label_to_last("Save")

    assert native_tree.labels() == ["Border", "Scale", "Save"]
    assert native_tree.tree.has_forms() == native_tree.tree.GetCount()


def test_many_actions_collapse_all_but_last(native_tree: NativeTreeHarness) -> None:
    from phatch.core import api

    forms = [
        api.ACTIONS[label]()
        for label in ["Border", "Scale", "Rename", "Save", "Rotate"]
    ]
    result = native_tree.tree.append_forms(forms)

    assert result is forms
    assert all(
        not native_tree.tree.IsExpanded(item)
        for item in native_tree.action_items()[:-1]
    )
    assert native_tree.tree.IsExpanded(native_tree.action_items()[-1])


def test_selected_pixel_field_edit(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_action(native_tree, "Border")
    width = field_by_label(native_tree, action, "Border Width")
    native_tree.tree.Unbind(wx.EVT_TREE_SEL_CHANGED)

    native_tree.tree.SelectItem(width)
    native_tree.tree.set_form_field_value_selected("12px")

    assert (
        native_tree.tree.GetItemData(action).get_field_string("Border Width") == "12px"
    )


def test_selected_choice_field_ignores_direct_text_edit(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_action(native_tree, "Border")
    choice = field_by_label(native_tree, action, "Method")
    native_tree.tree.Unbind(wx.EVT_TREE_SEL_CHANGED)

    native_tree.tree.SelectItem(choice)
    native_tree.tree.set_form_field_value_selected("Different for each side")

    assert (
        native_tree.tree.GetItemData(action).get_field_string("Method")
        == "Equal for all sides"
    )


def test_selected_helpers_on_empty_tree_are_safe(
    native_tree: NativeTreeHarness,
) -> None:
    assert native_tree.tree.get_form_selected() == -1
    assert not native_tree.tree.remove_selected_form()


def test_relevance_switch_replaces_native_field_items(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_action(native_tree, "Border")
    method = field_by_label(native_tree, action, "Method")
    native_tree.tree.set_form_field_value(method, "Different for each side")

    assert native_tree.tree.update_form_relevance(method)
    labels = [
        native_tree.tree.GetItemData(item)[0] for item in native_tree.fields(action)
    ]
    assert "Left" in labels
    assert "Border Width" not in labels

    method = field_by_label(native_tree, action, "Method")
    native_tree.tree.set_form_field_value(method, "Equal for all sides")
    native_tree.tree.update_form_relevance(method)
    labels = [
        native_tree.tree.GetItemData(item)[0] for item in native_tree.fields(action)
    ]
    assert "Border Width" in labels
    assert "Left" not in labels


@pytest.mark.parametrize(
    ("action_label", "field_label"),
    [
        ("Border", "Method"),
        ("Border", "Opacity"),
        ("Border", "Color"),
        ("Save", "In"),
        ("Watermark", "Mark"),
        ("Tamogen", "Fill Image"),
        ("Write Tag", "Value"),
    ],
)
def test_actual_field_types_create_and_close_native_popup(
    native_tree: NativeTreeHarness, action_label: str, field_label: str
) -> None:
    action = append_action(native_tree, action_label)
    field = field_by_label(native_tree, action, field_label)
    native_tree.tree.SelectItem(field)

    native_tree.tree.create_popup(field)
    assert native_tree.tree.popup.IsShown()
    native_tree.tree.resize_popup()
    native_tree.tree.close_popup()

    assert native_tree.tree.popup is None


def test_event_callbacks_update_selection_and_close_popup(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_action(native_tree, "Border")
    field = field_by_label(native_tree, action, "Opacity")
    native_tree.tree.SelectItem(field)
    native_tree.tree.create_popup(field)

    changing = native_tree.event(wx.wxEVT_TREE_SEL_CHANGING, action)
    native_tree.tree.on_sel_changing(changing)
    assert native_tree.tree.popup is None

    right_click = native_tree.event(wx.wxEVT_TREE_ITEM_RIGHT_CLICK, action)
    native_tree.tree.on_select(right_click)
    assert native_tree.tree.GetSelection() == action
    assert right_click.GetSkipped()


def test_left_click_and_field_activation_use_bound_callbacks(
    native_tree: NativeTreeHarness,
) -> None:
    action = append_action(native_tree, "Border")
    field = field_by_label(native_tree, action, "Opacity")
    mouse = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)

    native_tree.tree.on_left_down(mouse)
    assert mouse.GetSkipped()

    activated = native_tree.event(wx.wxEVT_TREE_ITEM_ACTIVATED, field)
    native_tree.tree.on_item_activated(activated)
    assert native_tree.tree.popup is not None


def test_automatic_expand_collapses_other_action(
    native_tree: NativeTreeHarness,
) -> None:
    first = append_action(native_tree, "Border")
    second = append_action(native_tree, "Scale")
    native_tree.tree.Expand(first)
    native_tree.tree.Expand(second)

    native_tree.tree.on_item_expanding(
        native_tree.event(wx.wxEVT_TREE_ITEM_EXPANDING, second)
    )

    assert not native_tree.tree.IsExpanded(first)


def test_enable_and_selection_state_helpers(native_tree: NativeTreeHarness) -> None:
    action = append_action(native_tree, "Border")

    native_tree.tree.enable_form(action, False)
    assert not native_tree.tree.is_form_enabled(action)
    native_tree.tree.enable_selected_form(True)
    assert native_tree.tree.is_form_enabled(action)
    assert native_tree.tree.is_form_selected()
