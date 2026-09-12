from __future__ import annotations

import pytest
import wx

from phatch.lib.pyWx import vlist, vlistTag
from tests.unit.pywx.native_browser_support import attach_and_show
from tests.unit.pywx.native_popup_support import panel, pump_events

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


class RecordingTagDialog(vlistTag.Dialog):
    def __init__(self, parent: wx.Window) -> None:
        self.modal_results: list[int] = []
        super().__init__(parent, ["vertical", "horizontal"], title="Tags")

    def EndModal(self, retCode: int) -> None:
        self.modal_results.append(retCode)


def memory_dc(size: tuple[int, int] = (240, 90)) -> tuple[wx.MemoryDC, wx.Bitmap]:
    bitmap = wx.Bitmap(*size)
    dc = wx.MemoryDC()
    dc.SelectObject(bitmap)
    return dc, bitmap


def test_vlist_initializes_geometry_theme_and_selection(native_frame) -> None:
    # Given
    control = vlist.Box(panel(native_frame))
    attach_and_show(native_frame, control)
    control.SetItemCount(2)

    # When
    control._safe_set_initial_selection()

    # Then
    assert control.GetIconSize() == (48, 48)
    assert control.OnMeasureItem(0) == 72
    assert control.GetSelection() == 0
    assert control._theme == "light_blue"
    assert control.GetItem(1)[0:2] == ("label 1", "summary 1")


def test_vlist_uses_native_theme_on_gtk(native_frame, monkeypatch) -> None:
    # Given
    monkeypatch.setattr(vlist.wx, "Platform", "__WXGTK__")

    # When
    control = vlist.Box(panel(native_frame))

    # Then
    assert control._theme == "default"


def test_vlist_gradient_colour_handles_greys_and_primary_channels(native_frame) -> None:
    # Given
    control = vlist.Box(panel(native_frame))

    # When
    grey = control.GradientColour(wx.Colour(40, 40, 40))
    accent = control.GradientColour(wx.Colour(200, 100, 50))
    control.SetTheme("default")

    # Then
    assert grey == wx.Colour(128, 128, 128)
    assert accent == wx.Colour(200, 50, 6)
    assert control._theme == "default"


def test_vlist_draws_item_separator_and_both_gradient_directions(native_frame) -> None:
    # Given
    control = vlist.Box(panel(native_frame))
    control.SetItemCount(1)
    control.SetSelection(0)
    dc, bitmap = memory_dc()
    rect = wx.Rect(0, 0, 240, 72)

    # When
    control.OnDrawSeparator(dc, rect, 0)
    control.OnDrawBackground(dc, rect, 0)
    control.OnDrawItem(dc, rect, 0)
    control.SetTheme("default")
    control.OnDrawItem(dc, rect, 0)
    control.SetVerticalGradient(False)
    control.OnDrawBackground(dc, wx.Rect(0, 0, 8, 8), 0)
    control.OnDrawBackground(dc, wx.Rect(0, 0, 0, 0), 0)
    control.SetSelection(wx.NOT_FOUND)
    control.OnDrawBackground(dc, rect, 0)

    # Then
    assert not control._is_vertical
    assert bitmap.ConvertToImage().GetRed(1, 1) >= 0
    dc.SelectObject(wx.NullBitmap)
    assert bitmap.IsOk()


def test_vlist_refresh_selects_first_item_only_when_nonempty(native_frame) -> None:
    # Given
    control = vlist.Box(panel(native_frame))

    # When
    control.RefreshAll()
    empty_selection = control.GetSelection()
    control.SetItemCount(1)
    control.RefreshAll()

    # Then
    assert empty_selection == wx.NOT_FOUND
    assert control.GetSelection() == 0


def test_tag_browser_filters_items_switches_orientation_and_empty_surface(
    native_frame,
) -> None:
    # Given
    browser = vlistTag.TestBrowser(
        panel(native_frame), ["vertical", "horizontal"], {}
    )
    attach_and_show(native_frame, browser)
    content = browser.content
    assert isinstance(content, vlistTag.TestContentBox)

    # When
    content.SetFilter("3")
    content.SetTag("horizontal")
    content.SetFilter("bad")
    pump_events()

    # Then
    assert content.GetItemCount() == 0
    assert content.IsEmpty()
    assert browser.CheckEmpty()
    assert browser.empty.IsShown()
    assert not browser.content.IsShown()
    assert content.GetFilter() is browser.filter
    assert content.GetTag() is browser.tag


def test_tag_content_skips_refresh_when_empty_state_handler_consumes_update(
    native_frame, monkeypatch
) -> None:
    # Given
    browser = vlistTag.TestBrowser(panel(native_frame), ["vertical"], {})
    content = browser.content
    assert isinstance(content, vlistTag.TestContentBox)
    monkeypatch.setattr(content, "CheckEmpty", lambda: True)

    # When
    content.SetFilter("1")

    # Then
    assert content.GetItemCount() == 1


def test_tag_dialog_accepts_nonempty_ok_and_double_click(native_frame) -> None:
    # Given
    dialog = RecordingTagDialog(native_frame)
    content = dialog.browser.content
    assert isinstance(content, vlistTag.TestContentBox)
    skip_event = wx.CommandEvent(wx.wxEVT_BUTTON, dialog.ok.GetId())
    blocked_event = wx.CommandEvent(wx.wxEVT_BUTTON, dialog.ok.GetId())

    # When
    content.SetFilter("2")
    dialog.OnOk(skip_event)
    content.SetFilter("0")
    dialog.OnOk(blocked_event)
    dialog.OnDoubleClick(wx.CommandEvent(wx.wxEVT_LISTBOX_DCLICK))

    # Then
    assert skip_event.GetSkipped()
    assert not blocked_event.GetSkipped()
    assert dialog.modal_results == [wx.ID_OK]
    assert dialog.GetDefaultItem() is dialog.ok
    dialog.Destroy()


def test_vlist_test_frames_construct_real_native_controls(native_frame) -> None:
    # Given / When
    basic = vlist.TestFrame(native_frame)
    tags = vlistTag.TestFrame(native_frame)
    dialog = vlistTag.TestDialog(native_frame, ["vertical", "horizontal"])

    # Then
    assert isinstance(basic.GetChildren()[0], vlist.Box)
    assert isinstance(tags.GetChildren()[0], vlistTag.TestBrowser)
    assert isinstance(dialog.browser, vlistTag.TestBrowser)
    basic.Destroy()
    tags.Destroy()
    dialog.Destroy()
    pump_events()
