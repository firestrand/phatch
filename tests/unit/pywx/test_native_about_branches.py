from __future__ import annotations

import builtins
import gettext
import importlib.util
import random
import runpy
import sys
from pathlib import Path

import pytest
import wx

from phatch.lib.pyWx import about

from .native_popup_support import pump_events

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


class ReturnCodeAboutDialog(about.Dialog):
    def __init__(self, parent: wx.Window) -> None:
        about.wxgAboutDialog.__init__(self, parent)
        self.return_codes: list[int] = []

    def EndModal(self, retCode: int) -> None:
        self.return_codes.append(retCode)


class ReturnCodeCreditsDialog(about.CreditsDialog):
    def __init__(self, parent: wx.Window) -> None:
        about.wxgCreditsDialog.__init__(self, parent)
        self.return_codes: list[int] = []

    def EndModal(self, retCode: int) -> None:
        self.return_codes.append(retCode)


@pytest.fixture
def translated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builtins, "_", lambda value: value, raising=False)


@pytest.mark.parametrize("handler_name", ["OnCredits", "OnLicense", "OnClose"])
def test_generated_about_handlers_propagate_event(
    native_frame: wx.Frame, translated: None, handler_name: str, capsys
) -> None:
    # Given
    dialog = about.wxgAboutDialog(native_frame)
    event = wx.CommandEvent()

    # When
    getattr(dialog, handler_name)(event)

    # Then
    assert event.GetSkipped()
    assert "not implemented" in capsys.readouterr().out

    dialog.Destroy()


def test_generated_credits_close_handler_propagates_event(
    native_frame: wx.Frame, translated: None, capsys
) -> None:
    # Given
    dialog = about.wxgCreditsDialog(native_frame)
    event = wx.CommandEvent()

    # When
    dialog.OnClose(event)

    # Then
    assert event.GetSkipped()
    assert "not implemented" in capsys.readouterr().out

    dialog.Destroy()


def test_concrete_close_handlers_return_close_identifier(
    native_frame: wx.Frame, translated: None
) -> None:
    # Given
    about_dialog = ReturnCodeAboutDialog(native_frame)
    credits_dialog = ReturnCodeCreditsDialog(native_frame)

    # When
    about.Dialog.OnClose(about_dialog, wx.CommandEvent())
    about.CreditsDialog.OnClose(credits_dialog, wx.CommandEvent())

    # Then
    assert about_dialog.return_codes == [wx.ID_CLOSE]
    assert credits_dialog.return_codes == [wx.ID_CLOSE]

    about_dialog.Destroy()
    credits_dialog.Destroy()


def test_example_builds_about_window_under_guarded_main_loop(
    wx_app: wx.App,
    native_interaction,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.setattr(builtins, "_", lambda value: value, raising=False)
    monkeypatch.setattr(gettext, "install", lambda domain: None)
    monkeypatch.setattr(random, "randint", lambda minimum, maximum: 2)
    monkeypatch.setattr(wx, "PySimpleApp", lambda flag=0: wx_app)
    native_interaction.expect_main_loop()

    # When
    namespace = runpy.run_path(about.__file__, run_name="__main__")
    dialog = wx_app.GetTopWindow()

    # Then
    assert isinstance(dialog, namespace["Dialog"])
    assert isinstance(dialog, wx.Dialog)
    labels = [
        child.GetLabel()
        for child in dialog.GetChildren()
        if isinstance(child, wx.StaticText)
    ]
    assert "title" in labels
    assert "description" in labels
    assert native_interaction.main_loop_apps == [wx_app]

    dialog.Destroy()
    pump_events()


def test_windows_transparent_bitmap_renders_and_tracks_bitmap_size(
    wx_app: wx.App,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.setattr(builtins, "_", lambda value: value, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    module_path = Path(about.__file__)
    spec = importlib.util.spec_from_file_location("about_windows_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    windows_about = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(windows_about)
    frame = wx.Frame(None, title="Transparent bitmap test")
    frame.SetBackgroundColour(wx.Colour(12, 34, 56))
    bitmap = wx.Bitmap(13, 9)

    # When
    control = windows_about.TransparentBitmap(frame, wx.ID_ANY, bitmap)
    initial_min_size = control.GetMinSize()
    frame.Show()
    control.Refresh()
    pump_events()
    control.SetBitmap(wx.Bitmap(17, 11))

    # Then
    assert isinstance(control, wx.Panel)
    assert initial_min_size == wx.Size(13, 9)
    assert control.GetMinSize() == wx.Size(17, 11)
    assert frame.IsShown()

    frame.Destroy()
    pump_events()
