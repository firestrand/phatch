from __future__ import annotations

import builtins
from collections.abc import Callable
from pathlib import Path

import pytest
import wx
import wx.adv
import wx.lib.dialogs

from phatch.lib.pyWx import about
from phatch.other.pyWx import toasterbox

from .native_popup_support import pump_events

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def _about_dialog(parent: wx.Window, monkeypatch: pytest.MonkeyPatch) -> about.Dialog:
    monkeypatch.setattr(builtins, "_", lambda value: value, raising=False)
    credits = {
        name: [{"name": name.title(), "email": f"{name}@example.test"}]
        for name in (
            "code",
            "documentation",
            "translation",
            "graphics",
            "libraries",
            "sponsors",
        )
    }
    return about.Dialog(
        parent,
        "Phatch 0.3",
        wx.Bitmap(16, 16),
        "Photos & batches",
        "https://example.test/phatch",
        credits,
        "GPL test license",
    )


def test_about_dialog_exposes_identity_and_dispatches_link_without_network(
    native_frame: wx.Frame, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    dialog = _about_dialog(native_frame, monkeypatch)
    opened: list[str] = []
    dialog.website.Bind(
        wx.adv.EVT_HYPERLINK, lambda event: opened.append(event.GetURL())
    )
    event = wx.adv.HyperlinkEvent(
        dialog.website, dialog.website.GetId(), dialog.website.GetURL()
    )

    # When
    dialog.website.ProcessEvent(event)

    # Then
    assert dialog.title.GetLabel() == "Phatch 0.3"
    assert dialog.description.GetLabel() == "Photos && batches"
    assert dialog.website.GetURL() == "https://example.test/phatch"
    assert opened == ["https://example.test/phatch"]

    dialog.Destroy()


def test_credits_dialog_populates_all_notebook_pages(
    native_frame: wx.Frame, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    dialog = _about_dialog(native_frame, monkeypatch)

    # When
    credits = about.CreditsDialog(dialog, dialog.credits)

    # Then
    assert credits.notebook.GetPageCount() == 6
    assert credits.credits_code.GetValue() == "Code - code@example.test"
    assert credits.credits_sponsors.GetValue() == "Sponsors - sponsors@example.test"
    assert all(
        credits.notebook.GetPage(index).GetSizer() is not None
        for index in range(credits.notebook.GetPageCount())
    )

    credits.Destroy()
    dialog.Destroy()


def test_about_child_dialogs_are_modal_guarded_and_destroyed(
    native_frame: wx.Frame,
    native_interaction,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    dialog = _about_dialog(native_frame, monkeypatch)
    native_interaction.expect_dialog(about.CreditsDialog, wx.ID_CLOSE)
    native_interaction.expect_dialog(wx.lib.dialogs.ScrolledMessageDialog, wx.ID_OK)

    # When
    dialog.OnCredits(wx.CommandEvent())
    dialog.OnLicense(wx.CommandEvent())
    pump_events()

    # Then
    remaining = [
        window
        for window in vars(wx)["GetTopLevelWindows"]()
        if window is not native_frame and window is not dialog
    ]
    assert remaining == []

    dialog.Destroy()


@pytest.mark.parametrize(
    ("corner", "expected"),
    [
        (0, lambda width, height, size: wx.Point(0, 0)),
        (1, lambda width, height, size: wx.Point(width - size.width, 0)),
        (2, lambda width, height, size: wx.Point(0, height - size.height)),
        (
            3,
            lambda width, height, size: wx.Point(
                width - size.width, height - size.height
            ),
        ),
    ],
)
def test_toaster_positions_each_screen_corner(
    native_frame: wx.Frame,
    corner: int,
    expected: Callable[[int, int, wx.Size], wx.Point],
) -> None:
    # Given
    toaster = toasterbox.ToasterBox(native_frame)
    popup_size = wx.Size(120, 60)
    toaster.SetPopupSize(popup_size)
    display_width, display_height = wx.GetDisplaySize()

    # When
    toaster.SetPopupPositionByInt(corner)

    # Then
    assert toaster._popupposition == expected(
        display_width, display_height, popup_size
    )

    toaster.GetToasterBoxWindow().Destroy()


def test_toaster_manual_timer_tick_closes_without_sleep_or_persistent_window(
    native_frame: wx.Frame
) -> None:
    # Given
    toasterbox.winlist.clear()
    toaster = toasterbox.ToasterBox(
        native_frame,
        closingstyle=toasterbox.TB_ONCLICK,
        scrollType=toasterbox.TB_SCR_TYPE_DU,
    )
    toaster.SetPopupPosition(wx.Point(40, 40))
    toaster.SetPopupSize(wx.Size(80, 24))
    toaster.SetPopupPauseTime(60_000)
    toaster.SetPopupScrollSpeed(0)
    toaster.SetPopupText("A deterministic notification")

    # When
    toaster.Play()
    window = toaster.GetToasterBoxWindow()
    assert window.showtime.IsRunning()
    window.NotifyTimer(None)
    pump_events()

    # Then
    assert not window.IsShown()
    assert toasterbox.winlist == []
    assert not hasattr(window, "showtime")

    window.Destroy()


def test_complex_toaster_owns_panel_and_click_closes(
    native_frame: wx.Frame
) -> None:
    # Given
    toasterbox.winlist.clear()
    toaster = toasterbox.ToasterBox(
        native_frame,
        tbstyle=toasterbox.TB_COMPLEX,
        closingstyle=toasterbox.TB_ONCLICK,
    )
    toaster.SetPopupPosition(wx.Point(40, 40))
    toaster.SetPopupSize(wx.Size(80, 24))
    toaster.SetPopupScrollSpeed(0)
    panel = wx.Panel(toaster.GetToasterBoxWindow())
    toaster.AddPanel(panel)

    # When
    toaster.Play()
    window = toaster.GetToasterBoxWindow()
    window.OnMouseDown(wx.MouseEvent(wx.wxEVT_LEFT_DOWN))
    pump_events()

    # Then
    assert window.GetSizer().GetItemCount() == 1
    assert not window.IsShown()
    assert toasterbox.winlist == []

    window.Destroy()


def test_simple_toaster_draws_bitmap_backdrop(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    # Given
    bitmap_path = tmp_path / "background.bmp"
    assert wx.Bitmap(80, 24).SaveFile(str(bitmap_path), wx.BITMAP_TYPE_BMP)
    toaster = toasterbox.ToasterBox(native_frame)
    toaster.SetPopupSize(wx.Size(80, 24))
    toaster.SetPopupPosition(wx.Point(40, 40))
    toaster.SetPopupBitmap(str(bitmap_path))
    toaster.SetPopupTextColor(wx.Colour(1, 2, 3))
    toaster.SetPopupBackgroundColor(wx.Colour(4, 5, 6))
    toaster.SetPopupTextFont(wx.Font(wx.FontInfo(9)))
    toaster.SetPopupScrollSpeed(0)

    # When
    toaster.Play()
    window = toaster.GetToasterBoxWindow()
    window.NotifyTimer(None)

    # Then
    assert window._staticbitmap is not None
    assert window.GetBackgroundColour() == wx.Colour(4, 5, 6)
    assert window._textcolour == wx.Colour(1, 2, 3)

    window.Destroy()
    toasterbox.winlist.clear()
