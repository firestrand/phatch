from __future__ import annotations

from pathlib import Path

import pytest
import wx

from phatch.lib import listData
from phatch.lib.pyWx import folderFileBrowser
from tests.unit.pywx.native_browser_support import (
    attach_and_show,
    child_items,
    list_event,
    seed_browser_paths,
    tree_event,
)
from tests.unit.pywx.native_popup_support import panel, pump_events

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


class NativePreviewBrowser(folderFileBrowser.PreviewMixin, folderFileBrowser.Panel):
    pass


def browser_data(paths) -> tuple[list[dict[str, str]], dict]:
    files = [
        {"path": str(paths.first), "name": paths.first.name, "size": "1"},
        {"path": str(paths.second), "name": paths.second.name, "size": "2"},
    ]
    return files, listData.files_data_dict(files)


def make_browser(native_frame, tmp_path: Path, test_input_dir: Path):
    paths = seed_browser_paths(tmp_path, test_input_dir)
    files, tree_data = browser_data(paths)
    browser = NativePreviewBrowser(
        panel(native_frame),
        wx.ID_ANY,
        tree_data,
        listData.DataDict,
        ["name", "size"],
    )
    attach_and_show(native_frame, browser)
    return browser, paths, files


def test_folder_browser_lists_tree_rows_and_formats_virtual_cells(
    native_frame, tmp_path: Path, test_input_dir: Path
) -> None:
    # Given / When
    browser, paths, files = make_browser(native_frame, tmp_path, test_input_dir)
    root = browser.tree.GetRootItem()
    image_root = child_items(browser.tree, root)[0]
    nested = child_items(browser.tree, image_root)[0]
    labels = [browser.tree.GetItemText(image_root), browser.tree.GetItemText(nested)]

    # Then
    assert labels == [str(paths.root) + "/", "nested/"]
    assert browser.list.GetItemCount() == 2
    assert browser.list.OnGetItemText(0, 0) == "alpha.png"
    assert browser.list.OnGetItemText(0, 1) == "1"
    assert browser.list.OnGetItemAttr(0) is None
    assert browser.list.OnGetItemImage(0) == -1
    assert browser.GetTreeLabel("child", "parent") == "child"
    assert folderFileBrowser.Panel.GetTreeLabel(browser, "child", "parent") == "child"
    assert files[0]["path"] == str(paths.first)
    assert paths.source.read_bytes() == paths.source_bytes


def test_folder_browser_filters_updates_headers_and_navigates_tree(
    native_frame, tmp_path: Path, test_input_dir: Path
) -> None:
    # Given
    browser, paths, _files = make_browser(native_frame, tmp_path, test_input_dir)
    root = browser.tree.GetRootItem()
    image_root = child_items(browser.tree, root)[0]
    nested = child_items(browser.tree, image_root)[0]

    # When
    browser.filter.SetValue("bravo")
    browser.on_filter_text(wx.CommandEvent(wx.wxEVT_TEXT, browser.filter.GetId()))
    browser.on_tree_sel_changed(
        tree_event(browser.tree, wx.wxEVT_TREE_SEL_CHANGED, nested)
    )
    browser.UpdateHeaders(["size", "name"])
    browser.SetColumnWidths(91, 137)

    # Then
    assert browser.list.GetItemCount() == 1
    assert browser.list.data.get_by_header(0, "path") == str(paths.second)
    assert browser.list.GetColumn(0).GetText() == "size"
    assert browser.list.GetColumnWidth(0) == 91
    assert browser.list.GetColumnWidth(1) == 137


def test_folder_browser_activation_routes_exact_paths_without_process_launch(
    native_frame, tmp_path: Path, test_input_dir: Path, monkeypatch
) -> None:
    # Given
    browser, paths, _files = make_browser(native_frame, tmp_path, test_input_dir)
    launched: list[str] = []
    monkeypatch.setattr(folderFileBrowser, "start", launched.append)
    root = browser.tree.GetRootItem()
    first_folder = child_items(browser.tree, root)[0]

    # When
    browser.on_tree_item_activated(
        tree_event(browser.tree, wx.wxEVT_TREE_ITEM_ACTIVATED, first_folder)
    )
    browser.on_list_item_activated(
        list_event(browser.list, wx.wxEVT_LIST_ITEM_ACTIVATED, 0)
    )

    # Then
    assert launched == [str(paths.root), str(paths.first)]
    assert browser.get_tree_folder(first_folder) == str(paths.root)
    assert browser.get_list_file(0) == str(paths.first)
    assert browser.GetTreeLabel("root/child", "root/") == "child"


def test_folder_browser_selection_renders_real_thumbnail(
    native_frame, tmp_path: Path, test_input_dir: Path
) -> None:
    # Given
    browser, _paths, _files = make_browser(native_frame, tmp_path, test_input_dir)

    # When
    browser.on_list_item_selected(
        list_event(browser.list, wx.wxEVT_LIST_ITEM_SELECTED, 0)
    )
    pump_events()

    # Then
    bitmap = browser.preview.GetBitmap()
    assert browser.preview.IsShown()
    assert bitmap.GetWidth() == bitmap.GetHeight()
    assert bitmap.GetWidth() >= 128
    assert browser.preview.GetMinSize() == wx.Size(128, 128)


def test_folder_list_refreshes_only_for_changed_data(native_frame) -> None:
    # Given
    control = folderFileBrowser.ListCtrl(panel(native_frame))
    data = listData.DataDict(
        [{"path": "one", "name": None}], headers=["name"], id="path"
    )
    control.InitData(data)

    # When
    control.SetData(data.data)
    control.SetFilter("")
    control.SetData([{"path": "two", "name": "second"}], amount=1)

    # Then
    assert control.GetItemCount() == 1
    assert control.OnGetItemText(0, 0) == "second"


def test_folder_browser_accepts_empty_directory_data(native_frame) -> None:
    # Given / When
    browser = folderFileBrowser.Panel(
        panel(native_frame), wx.ID_ANY, {}, listData.DataDict, ["name"]
    )

    # Then
    assert browser.list.GetItemCount() == 0
    assert browser.data_tree == [[]]


def test_folder_browser_accepts_explicit_root_label(native_frame) -> None:
    # Given
    class LabelledBrowser(folderFileBrowser.Panel):
        def _tree(self, root_label=None, icon=wx.ART_FOLDER):
            label = "Pictures" if root_label is None else root_label
            super()._tree(label, icon)

    # When
    browser = LabelledBrowser(
        panel(native_frame), wx.ID_ANY, {}, listData.DataDict, ["name"]
    )

    # Then
    assert browser.tree.GetItemText(browser.tree.GetRootItem()) == "Pictures"
