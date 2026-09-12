from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.pywx.native_inspector_support import jpeg_path as jpeg_path
from tests.unit.pywx.native_inspector_support import native_runtime as native_runtime
from tests.unit.pywx.native_inspector_support import show_frame, wx
from tests.unit.pywx.native_inspector_support import wx_app as wx_app

pytestmark = pytest.mark.requires_display


def test_image_frame_displays_real_pillow_file_and_metadata(
    native_runtime, jpeg_path: Path
) -> None:
    from phatch.lib.pyWx import imageInspector

    # Given
    frame = imageInspector.Frame(None, str(jpeg_path), size=(720, 520))

    # When
    show_frame(frame)
    grid = frame.GetGrid()
    assert isinstance(grid, imageInspector.GridTag)

    # Then
    assert grid.IsShownOnScreen()
    assert grid.GetNumberCols() == 1
    assert grid.image_table.images[0].filename == str(jpeg_path)
    assert grid.image_table.images[0].thumb.size == (96, 48)
    assert grid.GetNumberRows() > 10
    assert jpeg_path.name in frame.GetTitle()


def test_image_browser_tag_and_filter_controls_change_visible_rows(
    native_runtime, jpeg_path: Path
) -> None:
    from phatch.lib.pyWx import imageInspector

    # Given
    frame = imageInspector.Frame(None, str(jpeg_path), size=(720, 520))
    show_frame(frame)
    browser = frame.browser
    grid = frame.GetGrid()
    assert isinstance(grid, imageInspector.GridTag)

    # When
    browser.tag.SetStringSelection("Pil")
    tag_event = wx.CommandEvent(wx.EVT_CHOICE.typeId, browser.tag.GetId())
    tag_event.SetString("Pil")
    browser.tag.ProcessEvent(tag_event)
    browser.filter.ChangeValue("jfif")
    filter_event = wx.CommandEvent(wx.EVT_TEXT.typeId, browser.filter.GetId())
    browser.filter.ProcessEvent(filter_event)
    wx.Yield()

    # Then
    assert browser.tag.GetStringSelection() == "Pil"
    assert browser.filter.GetValue() == "jfif"
    assert grid.GetNumberRows() > 0
    assert all("jfif" in grid.GetRowLabelValue(row).lower()
               for row in range(grid.GetNumberRows()))


def test_image_table_adapter_reflects_real_metadata(
    native_runtime, jpeg_path: Path
) -> None:
    from phatch.lib.pyWx import imageInspector

    # Given
    table = imageInspector.Table((64, 64))

    # When
    table.table.set_tag(imageInspector.SELECT)
    table.table.set_filter("")
    table.table.open_image(str(jpeg_path))

    # Then
    assert table.GetNumberCols() == 1
    assert table.GetNumberRows() > 10
    assert table.GetColLabelValue(0) == jpeg_path.name
    row = table.table.keys.index("format")
    assert table.GetValue(row, 0) == "JPEG"
    assert not table.IsEmptyCell(row, 0)
    assert table.IsEditableCell(row, 0)
    attr = table.GetAttr(row, 0, wx.grid.GridCellAttr.Any)
    assert attr.IsReadOnly()


def test_embedded_pencil_asset_constructs_native_bitmap(native_runtime) -> None:
    from phatch.lib.pyWx import imageInspector

    # Given
    data = imageInspector.getPencilData()

    # When
    image = imageInspector.getPencilImage()
    bitmap = imageInspector.getPencilBitmap()
    empty = imageInspector.empty_bitmap(7, 9)

    # Then
    assert data.startswith(b"\x89PNG")
    assert image.GetSize() == (16, 16)
    assert bitmap.IsOk()
    assert empty.GetSize() == (7, 9)


def test_thumbnail_label_paints_at_native_integer_coordinates(
    native_runtime, jpeg_path: Path
) -> None:
    from phatch.lib.pyWx import imageInspector

    # Given
    frame = imageInspector.Frame(None, str(jpeg_path), size=(720, 520))
    show_frame(frame)
    grid = frame.GetGrid()
    assert isinstance(grid, imageInspector.GridTag)
    window = grid.GetGridColLabelWindow()
    dc = wx.ClientDC(window)

    # When
    grid._LabelPaint(
        dc,
        co=0,
        amount=grid.GetNumberCols(),
        label_rect=lambda position, col: (
            position,
            0,
            grid.GetColSize(col),
            grid.GetColLabelSize(),
        ),
        get_size=grid.GetColSize,
        get_label=None,
        get_bitmap=lambda index: grid.image_table.images[index].thumb_wx,
        border=False,
        center_bitmap=True,
        pen=dc.GetPen(),
    )

    # Then
    assert grid.image_table.images[0].thumb_wx.IsOk()
