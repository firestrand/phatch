from __future__ import annotations

import runpy
from pathlib import Path
from typing import ClassVar

import pytest
import wx
from PIL import Image

from .native_dialog_support import (
    ActionFixture,
    command_event,
    image_tree_data,
)
from .native_dialog_support import dialog_runtime as dialog_runtime

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


class ActiveEvent:
    def __init__(self, active: bool) -> None:
        self.active = active

    def GetActive(self) -> bool:
        return self.active


class TreeEvent:
    def __init__(self, item: wx.TreeItemId) -> None:
        self.item = item

    def GetItem(self) -> wx.TreeItemId:
        return self.item


class ListEvent:
    def GetIndex(self) -> int:
        return 0


def test_height_cache_and_browse_dispatch_cover_both_native_paths(
    dialog_runtime, monkeypatch
) -> None:
    # Given
    from phatch.pyWx import dialogs

    parent, _counter, _root = dialog_runtime
    monkeypatch.setattr(dialogs, "_MAX_HEIGHT", None)
    dialog = dialogs.ExecuteDialog(parent)
    calls: list[str] = []
    monkeypatch.setattr(dialog, "browse_folder", lambda: calls.append("folder"))
    monkeypatch.setattr(dialog, "browse_files", lambda: calls.append("files"))

    # When
    first = dialogs.get_max_height(300)
    second = dialogs.get_max_height(200)
    dialog.source.SetSelection(0)
    dialog.on_browse(command_event(dialog.browse))
    dialog.source.SetSelection(1)
    dialog.on_browse(command_event(dialog.browse))

    # Then
    assert first == second
    assert calls == ["folder", "files"]


def test_action_list_searches_attributes_context_menu_and_source(
    dialog_runtime, native_interaction, monkeypatch
) -> None:
    # Given
    from phatch.pyWx import dialogs

    class GeometryAction(ActionFixture):
        label = "Crop"
        __doc__ = "Trim margins"
        tags: ClassVar[tuple[str, ...]] = ("default", "geometry")
        tags_hidden: ClassVar[tuple[str, ...]] = ("edges",)
        __module__ = "phatch.actions.crop"

    parent, _counter, _root = dialog_runtime
    qb = ActionFixture()
    actions = {"resize": qb, "crop": GeometryAction()}
    dialog = dialogs.ActionDialog(parent, actions, size=(420, 360))
    list_box = dialog.GetListBox()
    assert isinstance(list_box, dialogs.ActionListBox)
    sent: list[tuple] = []
    monkeypatch.setattr(
        dialogs.send,
        "frame_show_scrolled_message",
        lambda *values, **options: sent.append((*values, options)),
    )

    # When
    for value in ("resize", "trim", "geometry", "edges", "unknown"):
        list_box.SetFilter(value)
    list_box.SetFilter("")
    list_box.SetTag("geometry")
    list_box.SetTag(dialogs.imageInspector.ALL)
    list_box.SetTag(dialogs.imageInspector.SELECT)
    list_box.SetSelection(0)
    list_box.RefreshList()
    native_interaction.expect_popup()
    list_box.OnContextMenu(wx.ContextMenuEvent())
    list_box.OnViewSource(wx.CommandEvent())
    dialog.OnActivate(ActiveEvent(False))
    dialog.OnActivate(ActiveEvent(True))
    wx.Yield()

    # Then
    assert list_box.GetItemCount() == 2
    assert sent
    assert "resize.py" in sent[0][1] or "crop.py" in sent[0][1]
    assert dialog.GetTagSelection() in {"Select", "All", "default"}


def test_plugin_dialog_toggles_template_and_help(dialog_runtime, monkeypatch) -> None:
    # Given
    from phatch.pyWx import dialogs

    parent, _counter, _root = dialog_runtime
    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", opened.append)
    dialog = dialogs.WritePluginDialog(parent, "Create an action")

    # When
    dialog.template.SetValue(True)
    event = wx.CommandEvent(wx.EVT_CHECKBOX.typeId)
    event.SetInt(1)
    dialog.on_template(event)
    dialog.on_help(wx.CommandEvent())

    # Then
    assert dialog.message.GetLabel() == "Create an action"
    assert dialog.code.IsShown()
    assert "class Action" in dialog.code.GetValue()
    assert opened == ["https://lists.launchpad.net/phatch-dev/"]

    dialog.template_show(False)
    assert not dialog.code.IsShown()


def test_image_tree_menus_inspect_and_status_empty_report(
    dialog_runtime, tmp_path: Path, native_interaction
) -> None:
    # Given
    from phatch.pyWx import dialogs

    parent, _counter, _root = dialog_runtime
    image_path = tmp_path / "image.png"
    Image.new("RGB", (8, 8), "red").save(image_path)
    data, data_type = image_tree_data(image_path)
    dialog = dialogs.ImageTreeDialog(
        data,
        data_type,
        ["filename", "width", "height"],
        parent,
        size=(520, 340),
    )
    root = dialog.browser.tree.GetRootItem()
    dialog._AppendMenuItem(wx.Menu(), "Item", lambda event: None, id=wx.ID_OPEN)

    # When
    native_interaction.expect_popup()
    native_interaction.expect_popup()
    dialog.on_tree_item_right_click(TreeEvent(root))
    dialog.on_list_item_right_click(ListEvent())
    dialog.inspect_list_item(0)
    dialog.inspect_tree_item(root)
    inspector = next(
        window
        for window in vars(wx)["GetTopLevelWindows"]()
        if window.__class__.__name__ == "ImageInspectorFrame"
    )
    assert isinstance(inspector, dialogs.ImageInspectorFrame)
    grid = inspector.GetGrid()
    assert isinstance(grid, dialogs.ImageInspectorGrid)

    class TreeRecorder:
        value = ""

        def set_form_field_value_selected(self, value: str) -> None:
            self.value = value

    parent.tree = TreeRecorder()
    assert grid.HasActionList()
    grid.InsertTagInActionList(0)
    grid.ProcessKey(73, 0, 0, True, True, False)
    grid.ProcessKey(65, 0, 0, False, False, False)
    status = dialogs.StatusDialog(parent)
    status.SetMessage("No report", report=None)

    # Then
    assert len(
        [
            w
            for w in vars(wx)["GetTopLevelWindows"]()
            if w.GetClassName() == "wxFrame"
        ]
    ) >= 3
    assert not status.report.IsShown()


def test_example_initializes_hidden_frame_without_native_main_loop(
    dialog_runtime, native_interaction, monkeypatch
) -> None:
    # Given
    from phatch.pyWx import dialogs

    parent, _counter, _root = dialog_runtime

    class ExampleApp:
        def __init__(self, redirect: bool) -> None:
            self.top_window = parent

        def SetTopWindow(self, window: wx.Window) -> None:
            self.top_window = window

        def GetTopWindow(self) -> wx.Window:
            return self.top_window

        def OnInit(self) -> bool:
            raise AssertionError("example subclass must provide OnInit")

        def show_error_dialog(self) -> None:
            raise AssertionError("example subclass must provide dialog methods")

        def show_execute_dialog(self) -> None:
            raise AssertionError("example subclass must provide dialog methods")

        def show_files_dialog(self) -> None:
            raise AssertionError("example subclass must provide dialog methods")

        def show_progress_dialog(self) -> None:
            raise AssertionError("example subclass must provide dialog methods")

        def MainLoop(self) -> None:
            assert self.OnInit()
            self.show_error_dialog()
            self.show_execute_dialog()
            self.show_files_dialog()
            self.show_progress_dialog()
            native_interaction.main_loop(self)

    monkeypatch.setattr(dialogs.wx, "App", ExampleApp)
    monkeypatch.setattr(dialogs.wx, "CallAfter", lambda callback: None)
    monkeypatch.setattr(dialogs.time, "sleep", lambda seconds: None)
    native_interaction.expect_dialog(dialogs.ErrorDialog, wx.ID_OK)
    native_interaction.expect_dialog(dialogs.ExecuteDialog, wx.ID_CANCEL)
    native_interaction.expect_dialog(dialogs.FilesDialog, wx.ID_OK)
    native_interaction.expect_main_loop()

    # When
    dialogs.example()

    # Then
    assert native_interaction.main_loop_apps


def test_controller_module_entrypoint_uses_guarded_example_loop(
    dialog_runtime, native_interaction, monkeypatch
) -> None:
    # Given
    parent, _counter, _root = dialog_runtime

    class ExampleApp:
        def __init__(self, redirect: bool) -> None:
            self.top_window = parent

        def SetTopWindow(self, window: wx.Window) -> None:
            self.top_window = window

        def GetTopWindow(self) -> wx.Window:
            return self.top_window

        def MainLoop(self) -> None:
            assert self.OnInit()
            native_interaction.main_loop(self)

        def OnInit(self) -> bool:
            raise AssertionError("example subclass must provide OnInit")

    monkeypatch.setattr(wx, "App", ExampleApp)
    monkeypatch.setattr(wx, "CallAfter", lambda callback: None)
    native_interaction.expect_main_loop()

    # When
    with pytest.warns(RuntimeWarning, match="found in sys.modules"):
        runpy.run_module("phatch.pyWx.dialogs", run_name="__main__")

    # Then
    assert native_interaction.main_loop_apps


def test_controller_import_covers_alternate_native_icon_platform(
    dialog_runtime, monkeypatch
) -> None:
    # Given
    monkeypatch.setattr(wx, "Platform", "__WXGTK__")

    # When
    with pytest.warns(RuntimeWarning, match="found in sys.modules"):
        namespace = runpy.run_module(
            "phatch.pyWx.dialogs", run_name="dialog_platform"
        )

    # Then
    assert namespace["IconMixin"]._icon_size == (32, 32)
