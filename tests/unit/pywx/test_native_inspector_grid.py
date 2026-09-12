from __future__ import annotations

import runpy

import pytest

from tests.unit.pywx.native_inspector_support import native_runtime as native_runtime
from tests.unit.pywx.native_inspector_support import show_frame, wx
from tests.unit.pywx.native_inspector_support import wx_app as wx_app

pytestmark = pytest.mark.requires_display


def test_grid_cells_render_read_only_when_displayed(native_runtime) -> None:
    from phatch.lib.pyWx import inspector

    # Given
    frame = wx.Frame(None, title="Inspector grid")
    grid = inspector.Grid(frame, [["name", "value", "source"]])

    # When
    show_frame(frame)
    attr = grid.table.GetAttr(0, 1, wx.grid.GridCellAttr.Any)

    # Then
    assert grid.IsShownOnScreen()
    assert grid.GetCellValue(0, 1) == "value"
    assert attr.IsReadOnly()


def test_grid_table_edit_and_row_notifications_update_native_view(
    native_runtime,
) -> None:
    from phatch.lib.pyWx import inspector

    # Given
    frame = wx.Frame(None, title="Mutable inspector grid")
    data = [["first", "one", "source"]]
    grid = inspector.Grid(frame, data)
    show_frame(frame)

    # When
    grid.table.SetValue(0, 1, "changed")
    data.append(["second", "two", "source"])
    grid.RefreshAll()

    # Then
    assert grid.table.GetGrid() is grid
    assert grid.table.GetNumberCols() == 3
    assert grid.table.GetNumberRows() == 2
    assert grid.table.GetValue(0, 1) == "changed"
    assert not grid.table.IsEmptyCell(0, 0)
    assert grid.GetNumberRows() == 2


def test_grid_row_deletion_shrinks_displayed_table(native_runtime) -> None:
    from phatch.lib.pyWx import inspector

    # Given
    frame = wx.Frame(None, title="Delete inspector row")
    data = [["first", "one", "source"], ["second", "two", "source"]]
    grid = inspector.Grid(frame, data)
    show_frame(frame)

    # When
    del data[1]
    grid.RefreshAll()

    # Then
    assert grid.GetNumberRows() == 1
    assert grid.GetTableValue(0, 0) == "first"
    assert grid.IsTableEmptyCell() is False


def test_test_frame_constructs_visible_native_grid(native_runtime) -> None:
    from phatch.lib.pyWx import inspector

    # Given
    frame = inspector.TestFrame(None)

    # When
    show_frame(frame)
    grids = [child for child in frame.GetChildren() if isinstance(child, wx.grid.Grid)]

    # Then
    assert frame.GetTitle() == "inspector"
    assert len(grids) == 1
    assert grids[0].GetNumberRows() == 100


def test_inspector_demo_runs_guarded_main_loop_with_populated_grid(
    native_runtime, native_interaction, wx_app, monkeypatch
) -> None:
    from phatch.lib.pyWx import inspector

    native_interaction.expect_main_loop()
    monkeypatch.setattr(wx, "PySimpleApp", lambda: wx_app)

    runpy.run_path(inspector.__file__, run_name="__main__")

    frame = wx_app.GetTopWindow()
    assert isinstance(frame, wx.Frame)
    grids = [child for child in frame.GetChildren() if isinstance(child, wx.grid.Grid)]
    assert frame.IsShown()
    assert len(grids) == 1
    assert grids[0].GetNumberRows() == len(inspector.TEST_DATA)
