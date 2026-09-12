from __future__ import annotations

import os
import zlib
from pathlib import Path

import pytest

from tests.unit.pywx.native_inspector_support import jpeg_path as jpeg_path
from tests.unit.pywx.native_inspector_support import (
    metadata_provider as metadata_provider,
)
from tests.unit.pywx.native_inspector_support import native_runtime as native_runtime
from tests.unit.pywx.native_inspector_support import show_frame, wx
from tests.unit.pywx.native_inspector_support import wx_app as wx_app

pytestmark = pytest.mark.requires_display


def _frame(filename: str = ""):
    from phatch.lib.pyWx import imageInspector

    frame = imageInspector.Frame(None, filename, size=(720, 520))
    show_frame(frame)
    grid = frame.GetGrid()
    assert isinstance(grid, imageInspector.GridTag)
    return frame, grid


class SkipEvent:
    def __init__(self) -> None:
        self.skipped = False

    def Skip(self) -> None:
        self.skipped = True


class GridEvent(SkipEvent):
    def __init__(self, row: int, col: int) -> None:
        super().__init__()
        self._row = row
        self._col = col

    def GetRow(self) -> int:
        return self._row

    def GetCol(self) -> int:
        return self._col


class PositionEvent:
    def GetPosition(self) -> tuple[int, int]:
        return 0, 0


def test_empty_grid_actions_leave_native_empty_state(
    native_runtime, native_interaction
) -> None:
    _frame_window, grid = _frame()
    corner_event = SkipEvent()

    grid.ShowLog()
    grid.OnCornerLabelPaint(corner_event)
    grid.CopyCellValue(0, 0)
    grid.SetTag(None)
    grid.SetFilter("")
    unhandled = grid.ProcessKey(77, 0, 0, False, True, False)
    position = grid.GetCellRowCol(PositionEvent())

    assert corner_event.skipped
    assert grid.GetNumberCols() == 0
    assert grid.GetNumberRows() == 0
    assert unhandled is None
    assert position == (grid.XToCol(0), grid.YToRow(0))


def test_cancelled_add_actions_and_declined_row_delete_preserve_metadata(
    native_runtime, jpeg_path: Path, metadata_provider, native_interaction
) -> None:
    from phatch.lib.pyWx import imageInspector

    _frame_window, grid = _frame(str(jpeg_path))
    image = grid.image_table.images[0]
    image.info["Exif_Image_ImageDescription"] = "before"
    grid.image_table._update_keys(imageInspector.ALL, "")
    grid.RefreshAll()
    row = grid.image_table.keys.index("Exif_Image_ImageDescription")
    native_interaction.expect_dialog(imageInspector.AddTagDialog, wx.ID_CANCEL)
    native_interaction.expect_dialog(imageInspector.AddTagDialog, wx.ID_CANCEL)
    native_interaction.expect_dialog(wx.MessageDialog, wx.ID_NO)

    grid.AddRow()
    grid.AddColumnRow(0)
    grid.DeleteRows(row)

    assert grid.image_table.images[0].info["Exif_Image_ImageDescription"] == "before"


def test_real_noneditable_menus_and_row_double_click_take_no_action(
    native_runtime,
    jpeg_path: Path,
    metadata_provider,
    native_interaction,
    monkeypatch,
) -> None:
    from phatch.lib.pyWx import imageInspector

    _frame_window, grid = _frame(str(jpeg_path))
    row, col = next(
        (row, col)
        for row in range(grid.GetNumberRows())
        for col in range(grid.GetNumberCols())
        if not grid.image_table.is_cell_deletable(row, col)
    )
    monkeypatch.setattr(imageInspector, "pyexiv2", None)
    native_interaction.expect_popup()
    native_interaction.expect_popup()
    cell_event = GridEvent(row, col)
    row_event = GridEvent(row, -1)

    grid.OnGridCellRightClicked(cell_event)
    grid.OnGridRowLabelRightClicked(row)
    grid.OnGridLabelLeftDclicked(row_event)

    assert cell_event.skipped
    assert row_event.skipped
    assert grid.GetNumberCols() == 1


def test_all_invalid_batch_then_drop_recovers_with_real_image(
    native_runtime, jpeg_path: Path, native_interaction
) -> None:
    _frame_window, grid = _frame()
    missing = jpeg_path.with_name("missing.jpg")
    native_interaction.expect_dialog(wx.MessageDialog, wx.ID_OK)

    grid.OpenImages([str(missing)])
    grid.OnDrop([str(jpeg_path)], 0, 0)
    wx.Yield()

    assert grid.GetNumberCols() == 1
    assert grid.image_table.images[0].filename == str(jpeg_path)
    assert not wx.IsBusy()


def test_missing_metadata_cell_and_rename_use_real_multi_image_table(
    native_runtime,
    jpeg_path: Path,
    tmp_path: Path,
    metadata_provider,
) -> None:
    from PIL import Image

    from phatch.lib.pyWx import imageInspector

    blank_path = tmp_path / "blank.jpg"
    Image.new("RGB", (32, 24), (1, 2, 3)).save(blank_path)
    _frame_window, grid = _frame()
    grid.OpenImages([str(jpeg_path), str(blank_path)])
    old_key = "Exif_Image_ImageDescription"
    new_key = "Exif_Image_Copyright"
    grid.image_table.images[0].info[old_key] = "fixture description"
    grid.image_table.images[1].info.pop(old_key, None)
    grid.image_table._update_keys(imageInspector.ALL, "")
    grid.RefreshAll()
    row = grid.image_table.keys.index(old_key)

    attr = grid.table.GetAttr(row, 1, wx.grid.GridCellAttr.Any)
    result = grid.table.SetRowLabelValue(row, new_key)

    assert attr.GetBackgroundColour() == imageInspector.RED
    assert result == ""
    assert grid.image_table.images[0].info[new_key] == "fixture description"
    assert old_key not in grid.image_table.images[0].info


def test_corner_logo_loads_bitmap_through_native_paint(
    native_runtime, jpeg_path: Path, monkeypatch
) -> None:
    from phatch.lib.pyWx import imageInspector

    _frame_window, grid = _frame(str(jpeg_path))
    monkeypatch.setattr(
        grid, "corner_logo", zlib.compress(imageInspector.getPencilData())
    )
    grid._corner_logo = None

    grid.OnCornerLabelPaint(None)

    corner_logo = grid._corner_logo
    assert corner_logo is not None
    assert corner_logo.IsOk()


def test_modified_image_activation_focuses_filter_control(
    native_runtime, jpeg_path: Path
) -> None:
    frame, grid = _frame(str(jpeg_path))
    old_time = grid.image_table.images[0].time
    os.utime(jpeg_path, (old_time + 10, old_time + 10))

    frame.UpdateIfNeeded()
    wx.Yield()

    assert grid.image_table.images[0].time > old_time
    assert frame.browser.filter.HasFocus()
