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


def populate(harness: NativeTreeHarness) -> list[wx.TreeItemId]:
    from phatch.core import api

    harness.tree.append_forms(
        [api.ACTIONS["Border"](), api.ACTIONS["Scale"](), api.ACTIONS["Save"]()]
    )
    return harness.action_items()


def test_move_selected_actions_when_within_bounds(
    native_tree: NativeTreeHarness,
) -> None:
    items = populate(native_tree)
    native_tree.tree.SelectItem(items[1])

    native_tree.tree.move_form_selected_up()
    assert native_tree.labels() == ["Scale", "Border", "Save"]

    native_tree.tree.move_form_selected_down()
    assert native_tree.labels() == ["Border", "Scale", "Save"]


def test_move_actions_ignores_root_and_outer_boundaries(
    native_tree: NativeTreeHarness,
) -> None:
    items = populate(native_tree)

    native_tree.tree.MoveChildUp(native_tree.tree.GetRootItem())
    native_tree.tree.MoveChildDown(native_tree.tree.GetRootItem())
    native_tree.tree.MoveChildUp(items[0])
    native_tree.tree.MoveChildDown(items[-1])

    assert native_tree.labels() == ["Border", "Scale", "Save"]


def test_begin_drag_allows_only_valid_non_root_item(
    native_tree: NativeTreeHarness,
) -> None:
    item = populate(native_tree)[0]
    valid = native_tree.event(wx.wxEVT_TREE_BEGIN_DRAG, item)
    root = native_tree.event(wx.wxEVT_TREE_BEGIN_DRAG, native_tree.tree.GetRootItem())

    native_tree.tree.OnBeginDrag(valid)
    assert valid.IsAllowed()
    assert native_tree.tree._dragItem == item

    native_tree.tree._dragItem = None
    native_tree.tree.OnBeginDrag(root)
    assert native_tree.tree._dragItem is None
    native_tree.tree.OnBeginDrag(
        native_tree.event(wx.wxEVT_TREE_BEGIN_DRAG, wx.TreeItemId())
    )
    assert native_tree.tree._dragItem is None


def test_drop_swaps_sibling_actions_and_exports_new_order(
    native_tree: NativeTreeHarness,
) -> None:
    first, _middle, last = populate(native_tree)
    native_tree.tree.OnBeginDrag(native_tree.event(wx.wxEVT_TREE_BEGIN_DRAG, first))

    native_tree.tree.OnEndDrag(native_tree.event(wx.wxEVT_TREE_END_DRAG, last))

    assert native_tree.labels() == ["Save", "Scale", "Border"]
    assert [form.label for form in native_tree.tree.export_forms()] == [
        "Save",
        "Scale",
        "Border",
    ]


@pytest.mark.parametrize("target_kind", ["root", "invalid", "same"])
def test_drop_rejects_invalid_targets(
    native_tree: NativeTreeHarness, target_kind: str
) -> None:
    first, _middle, _last = populate(native_tree)
    native_tree.tree.OnBeginDrag(native_tree.event(wx.wxEVT_TREE_BEGIN_DRAG, first))
    if target_kind == "root":
        target = native_tree.tree.GetRootItem()
    elif target_kind == "invalid":
        target = wx.TreeItemId()
    else:
        target = first

    native_tree.tree.OnEndDrag(native_tree.event(wx.wxEVT_TREE_END_DRAG, target))

    assert native_tree.labels() == ["Border", "Scale", "Save"]


def test_drop_between_fields_reorders_their_parent_actions(
    native_tree: NativeTreeHarness,
) -> None:
    first, second, _last = populate(native_tree)
    source_field = native_tree.fields(first)[0]
    target_field = native_tree.fields(second)[0]
    native_tree.tree._dragItem = source_field

    native_tree.tree.OnEndDrag(native_tree.event(wx.wxEVT_TREE_END_DRAG, target_field))

    assert native_tree.labels() == ["Scale", "Border", "Save"]


def test_drag_can_be_disabled_and_reenabled(native_tree: NativeTreeHarness) -> None:
    native_tree.tree.DisableDrag()
    native_tree.tree.EnableDrag()

    assert native_tree.tree._dragTo == native_tree.tree.GetRootChild


def test_root_lookup_and_compare_error_boundaries(
    native_tree: NativeTreeHarness,
) -> None:
    item = populate(native_tree)[0]

    assert native_tree.tree.GetRootChild(native_tree.tree.GetRootItem()) == -1
    assert native_tree.tree.GetRootChild(item) == item
    with pytest.raises(ValueError, match="no order"):
        native_tree.tree.OnCompareItems(item, item)
    native_tree.tree._order = [item]
    assert native_tree.tree.OnCompareItems(item, item) == 0
    second = native_tree.action_items()[1]
    native_tree.tree._order = [item, second]
    assert native_tree.tree.OnCompareItems(item, second) == -1
    assert native_tree.tree.OnCompareItems(second, item) == 1


def test_drop_without_mapping_swaps_direct_siblings(
    native_tree: NativeTreeHarness,
) -> None:
    first, second, _last = populate(native_tree)
    native_tree.tree._dragItem = first
    native_tree.tree._dragTo = None

    native_tree.tree.OnEndDrag(native_tree.event(wx.wxEVT_TREE_END_DRAG, second))

    assert native_tree.labels() == ["Scale", "Border", "Save"]


def test_unmapped_drop_rejects_items_with_different_parents(
    native_tree: NativeTreeHarness,
) -> None:
    first, second, _last = populate(native_tree)
    native_tree.tree._dragItem = native_tree.fields(first)[0]
    native_tree.tree._dragTo = None

    native_tree.tree.OnEndDrag(
        native_tree.event(wx.wxEVT_TREE_END_DRAG, native_tree.fields(second)[0])
    )

    assert native_tree.labels() == ["Border", "Scale", "Save"]


def test_end_drag_without_started_drag_is_ignored(
    native_tree: NativeTreeHarness,
) -> None:
    item = populate(native_tree)[0]

    native_tree.tree.OnEndDrag(native_tree.event(wx.wxEVT_TREE_END_DRAG, item))

    assert native_tree.labels() == ["Border", "Scale", "Save"]
