from __future__ import annotations

import pytest

from tests.unit.pywx.native_inspector_support import native_runtime as native_runtime
from tests.unit.pywx.native_inspector_support import show_frame, wx
from tests.unit.pywx.native_inspector_support import wx_app as wx_app

pytestmark = pytest.mark.requires_display


def _choice(browser, value: str) -> None:
    browser.tag.SetStringSelection(value)
    event = wx.CommandEvent(wx.EVT_CHOICE.typeId, browser.tag.GetId())
    event.SetString(value)
    browser.tag.ProcessEvent(event)
    wx.Yield()


def _filter(browser, value: str) -> None:
    browser.filter.ChangeValue(value)
    event = wx.CommandEvent(wx.EVT_TEXT.typeId, browser.filter.GetId())
    event.SetString(value)
    browser.filter.ProcessEvent(event)
    wx.Yield()


def test_tag_browser_filters_rows_through_real_controls(native_runtime) -> None:
    from phatch.lib.pyWx import inspectorTag

    # Given
    frame = inspectorTag.TestFrame(None)
    show_frame(frame)
    browser = frame.GetChildren()[0]

    # When
    _choice(browser, "hexadecimal")
    _filter(browser, "0xf")

    # Then
    grid = browser.GetContent()
    assert browser.tag.GetStringSelection() == "hexadecimal"
    assert browser.filter.GetValue() == "0xf"
    assert grid.GetNumberRows() > 0
    assert all("0xf" in str(row) for row in grid.data)


def test_tag_browser_switches_between_empty_and_content_views(native_runtime) -> None:
    from phatch.lib.pyWx import inspectorTag

    # Given
    frame = inspectorTag.TestFrame(None)
    show_frame(frame)
    browser = frame.GetChildren()[0]

    # When
    _filter(browser, "not present in any row")

    # Then
    assert browser.IsEmpty()
    assert browser.empty.IsShown()
    assert not browser.content.IsShown()

    # When
    _filter(browser, "")

    # Then
    assert not browser.IsEmpty()
    assert browser.content.IsShown()
    assert not browser.empty.IsShown()


def test_tag_grid_set_data_selects_requested_view(native_runtime) -> None:
    from phatch.lib.pyWx import inspectorTag

    # Given
    frame = wx.Frame(None, title="Tag data")
    browser = inspectorTag.TestBrowser(frame, ["decimal", "hexadecimal"], {
        "data": inspectorTag.TEST_DATA,
    })
    show_frame(frame)
    grid = browser.GetContent()
    assert isinstance(grid, inspectorTag.TestContentGrid)

    # When
    grid.SetData(inspectorTag.TEST_DATA)

    # Then
    assert grid.all_data is inspectorTag.TEST_DATA
    assert grid.tag_data is inspectorTag.TEST_DATA["decimal"]
    assert grid.GetNumberRows() == 100


def test_frame_close_button_destroys_native_window(native_runtime) -> None:
    from phatch.lib.pyWx import inspectorTag

    # Given
    frame = inspectorTag.Frame(
        None,
        inspectorTag.TEST_DATA,
        list(inspectorTag.TEST_DATA),
        title="Metadata tags",
    )
    show_frame(frame)
    button = frame.CreateBitmapButton(wx.ART_INFORMATION, "Information")
    assert button.GetToolTipText() == "Information"
    frame_id = frame.GetId()

    # When
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, frame.close.GetId())
    frame.close.ProcessEvent(event)
    wx.Yield()

    # Then
    assert frame_id not in {window.GetId() for window in wx.GetTopLevelWindows()}


def test_base_tag_grid_selects_tag_when_data_changes(native_runtime) -> None:
    from phatch.lib.pyWx import inspectorTag

    class GridBrowser(inspectorTag.Browser):
        ContentCtrl = inspectorTag.Grid

    # Given
    frame = wx.Frame(None, title="Base tag grid")
    browser = GridBrowser(frame, ["first", "second"], {
        "data": [["old", "value", "source"]],
    })
    show_frame(frame)
    grid = browser.GetContent()
    assert isinstance(grid, inspectorTag.Grid)
    new_data = [["new", "value", "source"]]

    # When
    grid.SetData(new_data, "second")

    # Then
    assert grid.all_data is new_data
    assert browser.tag.GetStringSelection() == "second"
    assert not grid.IsEmpty()


def test_child_frame_applies_floating_style_and_icon(native_runtime) -> None:
    from phatch.lib.pyWx import imageInspector, inspectorTag

    # Given
    parent = wx.Frame(None, title="Parent")
    icon = wx.Icon(imageInspector.getPencilBitmap())

    # When
    frame = inspectorTag.Frame(
        parent,
        inspectorTag.TEST_DATA,
        list(inspectorTag.TEST_DATA),
        icon=icon,
        style=wx.DEFAULT_FRAME_STYLE,
        title="Child metadata",
    )
    show_frame(parent)
    show_frame(frame)

    # Then
    assert frame.GetWindowStyle() & wx.FRAME_FLOAT_ON_PARENT
    assert frame.GetWindowStyle() & wx.FRAME_NO_TASKBAR
    assert frame.GetIcon().IsOk()
    grid = frame.GetGrid()
    assert isinstance(grid, inspectorTag.TestContentGrid)
    assert grid.GetNumberRows() == 100
