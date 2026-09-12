from __future__ import annotations

import pytest
import wx

from phatch.other.pyWx import toasterbox

from .native_popup_support import pump_events

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def _configured_toaster(
    parent: wx.Window | None,
    *,
    style: int = toasterbox.TB_SIMPLE,
) -> toasterbox.ToasterBox:
    toaster = toasterbox.ToasterBox(
        parent,
        tbstyle=style,
    )
    toaster.SetPopupPosition(wx.Point(60, 60))
    toaster.SetPopupSize(wx.Size(80, 24))
    toaster.SetPopupPauseTime(60_000)
    toaster.SetPopupScrollSpeed(0)
    return toaster


def _close_toaster(toaster: toasterbox.ToasterBox) -> None:
    window = toaster.GetToasterBoxWindow()
    if hasattr(window, "showtime"):
        window.NotifyTimer(None)
    window.Destroy()
    toasterbox.winlist.clear()
    pump_events()


def test_toaster_defaults_and_caption_title_are_configurable(
    native_frame: wx.Frame,
) -> None:
    # Given
    toaster = toasterbox.ToasterBox(
        native_frame, windowstyle=toasterbox.TB_CAPTION
    )
    toaster.SetPopupPosition(wx.Point(60, 60))
    toaster.SetPopupSize(wx.Size(80, 24))

    # When
    toaster.SetPopupBackgroundColor()
    toaster.SetPopupTextColor()
    toaster.SetPopupTextFont()
    toaster.SetPopupBitmap()
    toaster.SetTitle("Notification")

    # Then
    assert toaster._backgroundcolour == wx.WHITE
    assert toaster._foregroundcolour == wx.BLACK
    assert toaster._bitmap is None
    assert toaster.GetToasterBoxWindow().GetTitle() == "Notification"

    _close_toaster(toaster)


def test_simple_toaster_rejects_complex_panel(native_frame: wx.Frame) -> None:
    # Given
    toaster = _configured_toaster(native_frame)
    panel = wx.Panel(toaster.GetToasterBoxWindow())

    # When / Then
    with pytest.raises(Exception, match="Panel Can Not Be Added"):
        toaster.AddPanel(panel)
    with pytest.raises(Exception, match="Panel Can Not Be Added"):
        toaster.GetToasterBoxWindow().AddPanel(panel)

    _close_toaster(toaster)


@pytest.mark.parametrize(
    ("position", "size"),
    [
        (wx.Point(-80, -24), wx.Size(80, 24)),
        (wx.Point(60, 60), wx.Size(49, 24)),
    ],
)
def test_invalid_toaster_geometry_never_leaves_a_window(
    native_frame: wx.Frame, position: wx.Point, size: wx.Size
) -> None:
    # Given
    toasterbox.winlist.clear()
    toaster = toasterbox.ToasterBox(native_frame)
    toaster.SetPopupPosition(position)
    toaster.SetPopupSize(size)
    window = toaster.GetToasterBoxWindow()

    # When
    toaster.Play()
    pump_events()

    # Then
    assert toasterbox.winlist == []
    assert not window


def test_toasters_stack_and_compact_after_first_closes(
    native_frame: wx.Frame,
) -> None:
    # Given
    toasterbox.winlist.clear()
    first = _configured_toaster(native_frame)
    second = _configured_toaster(native_frame)

    # When
    first.Play()
    second.Play()
    second_window = second.GetToasterBoxWindow()
    first.GetToasterBoxWindow().NotifyTimer(None)

    # Then
    assert second_window.IsShown()
    assert second_window._dialogtop == wx.Point(60, 64)
    assert toasterbox.winlist == [second_window]

    _close_toaster(second)


def test_upward_scroll_and_caption_close_share_timer_lifecycle(
    native_frame: wx.Frame,
) -> None:
    # Given
    toasterbox.winlist.clear()
    toaster = toasterbox.ToasterBox(
        native_frame,
        windowstyle=toasterbox.TB_CAPTION,
        scrollType=toasterbox.TB_SCR_TYPE_UD,
    )
    toaster.SetPopupPosition(wx.Point(60, 60))
    toaster.SetPopupSize(wx.Size(80, 24))
    toaster.SetPopupPauseTime(60_000)
    toaster.SetPopupScrollSpeed(0)

    # When
    toaster.Play()
    window = toaster.GetToasterBoxWindow()
    window.OnClose(wx.CloseEvent())

    # Then
    assert not window.IsShown()
    assert toasterbox.winlist == []

    window.Destroy()


def test_window_corner_positions_use_its_current_popup_size(
    native_frame: wx.Frame,
) -> None:
    # Given
    toaster = _configured_toaster(native_frame)
    window = toaster.GetToasterBoxWindow()
    window.SetPopupSize(wx.Size(80, 24))
    display_width, display_height = wx.GetDisplaySize()

    # When
    positions = []
    for corner in range(4):
        window.SetPopupPositionByInt(corner)
        positions.append(window._dialogtop)

    # Then
    assert positions == [
        wx.Point(0, 0),
        wx.Point(display_width - 80, 0),
        wx.Point(0, display_height - 24),
        wx.Point(display_width - 80, display_height - 24),
    ]

    _close_toaster(toaster)


@pytest.mark.parametrize("method_name", ["ScrollUp", "ScrollDown"])
def test_unsupported_scroll_type_is_rejected(
    native_frame: wx.Frame, method_name: str
) -> None:
    # Given
    toaster = toasterbox.ToasterBox(native_frame, scrollType=99)
    toaster.SetPopupPosition(wx.Point(60, 60))
    toaster.SetPopupSize(wx.Size(80, 24))
    toaster.SetPopupScrollSpeed(0)
    window = toaster.GetToasterBoxWindow()

    # When / Then
    with pytest.raises(ValueError, match="scrollType not supported"):
        getattr(window, method_name)()

    _close_toaster(toaster)


def test_parentless_toaster_can_be_constructed_and_cleaned(wx_app: wx.App) -> None:
    # Given / When
    toaster = toasterbox.ToasterBox(None)
    toaster.Notify()
    toaster.CleanList()

    # Then
    assert toaster.GetToasterBoxWindow().GetParent() is None

    _close_toaster(toaster)


def test_complex_toaster_without_panel_still_plays_and_closes(
    native_frame: wx.Frame,
) -> None:
    # Given
    toasterbox.winlist.clear()
    toaster = _configured_toaster(native_frame, style=toasterbox.TB_COMPLEX)

    # When
    toaster.Play()
    window = toaster.GetToasterBoxWindow()
    window.NotifyTimer(None)

    # Then
    assert not window.IsShown()
    assert toasterbox.winlist == []

    window.Destroy()


def test_notify_ignores_empty_window_slot(native_frame: wx.Frame) -> None:
    # Given
    toaster = _configured_toaster(native_frame)
    toasterbox.winlist[:] = [None]

    # When
    toaster.Notify()

    # Then
    assert toasterbox.winlist == [None]

    toasterbox.winlist.clear()
    _close_toaster(toaster)


def test_captioned_bitmap_does_not_bind_click_close(
    native_frame: wx.Frame,
) -> None:
    # Given
    toaster = toasterbox.ToasterBox(
        native_frame, windowstyle=toasterbox.TB_CAPTION
    )
    toaster.SetPopupPosition(wx.Point(60, 60))
    toaster.SetPopupSize(wx.Size(80, 24))
    window = toaster.GetToasterBoxWindow()

    # When
    window.SetPopupBitmap(wx.Bitmap(80, 24))

    # Then
    assert window._staticbitmap is not None
    assert window.GetTitle() == ""

    _close_toaster(toaster)
