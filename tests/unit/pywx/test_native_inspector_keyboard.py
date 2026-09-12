from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.pywx.native_inspector_support import jpeg_path as jpeg_path
from tests.unit.pywx.native_inspector_support import native_runtime as native_runtime
from tests.unit.pywx.native_inspector_support import show_frame, wx
from tests.unit.pywx.native_inspector_support import wx_app as wx_app

pytestmark = pytest.mark.requires_display


def _grid(jpeg_path: Path):
    from phatch.lib.pyWx import imageInspector

    frame = imageInspector.Frame(None, str(jpeg_path), size=(720, 520))
    show_frame(frame)
    grid = frame.GetGrid()
    assert isinstance(grid, imageInspector.GridTag)
    return grid


def test_process_key_dispatches_every_supported_shortcut(
    native_runtime, jpeg_path: Path, monkeypatch
) -> None:
    grid = _grid(jpeg_path)
    calls: list[tuple[str, tuple[int, ...]]] = []
    monkeypatch.setattr(
        grid.image_table, "is_cell_deletable", lambda _row, _col: True
    )
    monkeypatch.setattr(
        grid, "DeleteRows", lambda row: calls.append(("delete_rows", (row,)))
    )
    monkeypatch.setattr(
        grid,
        "DeleteCell",
        lambda row, col: calls.append(("delete_cell", (row, col))),
    )
    monkeypatch.setattr(
        grid,
        "CopyRowLabel",
        lambda row: calls.append(("copy_row", (row,))),
    )
    monkeypatch.setattr(
        grid,
        "CopyCellValue",
        lambda row, col: calls.append(("copy_cell", (row, col))),
    )
    monkeypatch.setattr(grid, "AddRow", lambda: calls.append(("add_row", ())))
    monkeypatch.setattr(
        grid, "AddColumnRow", lambda col: calls.append(("add_column", (col,)))
    )
    monkeypatch.setattr(
        grid, "RenameRowLabelValue", lambda row: calls.append(("rename", (row,)))
    )
    monkeypatch.setattr(
        grid, "ChangeRowValues", lambda row: calls.append(("change", (row,)))
    )

    grid.ProcessKey(127, 2, 3, True, False, False)
    grid.ProcessKey(127, 2, 3, False, False, False)
    grid.ProcessKey(67, 2, 3, True, True, False)
    grid.ProcessKey(67, 2, 3, False, True, False)
    grid.ProcessKey(78, 2, 3, True, True, False)
    grid.ProcessKey(78, 2, 3, False, True, False)
    grid.ProcessKey(82, 2, 3, True, True, False)
    grid.ProcessKey(77, 2, 3, True, True, False)
    unhandled = grid.ProcessKey(1, 2, 3, False, False, False)

    assert [name for name, _args in calls] == [
        "delete_rows",
        "delete_cell",
        "copy_row",
        "copy_cell",
        "add_row",
        "add_column",
        "rename",
        "change",
    ]
    assert unhandled is True


def test_show_log_and_invalid_open_use_guarded_messages(
    native_runtime, jpeg_path: Path, native_interaction
) -> None:
    grid = _grid(jpeg_path)
    grid.table.log = "write failed"
    native_interaction.expect_dialog(wx.MessageDialog, wx.ID_OK)
    native_interaction.expect_dialog(wx.MessageDialog, wx.ID_OK)

    grid.ShowLog()
    grid.OpenImage(str(jpeg_path.with_name("missing.jpg")))

    assert grid.table.log == ""
    assert grid.GetNumberCols() == 1


def test_cancelled_open_dialogs_do_not_add_images(
    native_runtime, jpeg_path: Path, native_interaction
) -> None:
    grid = _grid(jpeg_path)
    native_interaction.expect_dialog(wx.FileDialog, wx.ID_CANCEL)
    native_interaction.expect_dialog(wx.TextEntryDialog, wx.ID_CANCEL)

    grid.OnOpen(wx.CommandEvent())
    grid.OnOpenUrl(wx.CommandEvent())

    assert grid.GetNumberCols() == 1


class KeyEvent:
    def __init__(self) -> None:
        self.skipped = False

    def GetKeyCode(self) -> int:
        return 1

    def ShiftDown(self) -> bool:
        return False

    def ControlDown(self) -> bool:
        return False

    def AltDown(self) -> bool:
        return False

    def Skip(self) -> None:
        self.skipped = True


def test_native_corner_and_keyboard_handlers_paint_and_skip(
    native_runtime, jpeg_path: Path, monkeypatch
) -> None:
    from phatch.lib.pyWx import imageInspector

    grid = _grid(jpeg_path)
    monkeypatch.setattr(grid, "corner_logo", True)
    grid._corner_logo = imageInspector.getPencilBitmap()
    event = KeyEvent()
    dispatched: list[tuple[int, int, int, bool, bool, bool]] = []
    monkeypatch.setattr(
        grid,
        "ProcessKey",
        lambda key, row, col, shift, ctrl, alt: dispatched.append(
            (key, row, col, shift, ctrl, alt)
        )
        or True,
    )

    grid.OnCornerLabelPaint(None)
    grid.OnKeyDown(event)

    assert grid._corner_logo.IsOk()
    assert event.skipped
    assert dispatched[0][0] == 1


def test_child_frame_opens_isolated_folder_with_icon(
    native_runtime, jpeg_path: Path
) -> None:
    from phatch.lib.pyWx import imageInspector

    parent = wx.Frame(None, title="Parent")
    show_frame(parent)
    icon = wx.Icon(imageInspector.getPencilBitmap())

    frame = imageInspector.Frame(
        parent,
        str(jpeg_path.parent),
        icon=icon,
        size=(720, 520),
    )
    show_frame(frame)

    assert frame.GetWindowStyle() & wx.FRAME_FLOAT_ON_PARENT
    assert frame.GetIcon().IsOk()
    grid = frame.GetGrid()
    assert isinstance(grid, imageInspector.GridTag)
    assert grid.GetNumberCols() == 1
