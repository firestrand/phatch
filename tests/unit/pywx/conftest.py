from collections.abc import Iterator

import pytest

pytest.importorskip("wx")
import wx

from .native_interaction_guard import NativeInteractionGuard
from .native_popup_support import native_frame, wx_app


def pytest_runtest_makereport(item, call) -> None:
    if call.when == "call":
        item.native_call_passed = call.excinfo is None


@pytest.fixture(autouse=True)
def native_interaction(monkeypatch, request) -> Iterator[NativeInteractionGuard]:
    guard = NativeInteractionGuard()

    def show_modal(dialog: wx.Dialog) -> int:
        return guard.show_modal(dialog)

    def popup_menu(window: wx.Window, menu: wx.Menu, *args, **kwargs) -> bool:
        return guard.popup_menu(window, menu, *args, **kwargs)

    def main_loop(app: wx.App) -> None:
        guard.main_loop(app)

    def unexpected_prompt(*args, **kwargs):
        raise AssertionError(
            "Unexpected native prompt; inject its result at the caller boundary"
        )

    for dialog_type in (
        wx.Dialog,
        wx.MessageDialog,
        wx.FileDialog,
        wx.DirDialog,
        wx.TextEntryDialog,
    ):
        monkeypatch.setattr(dialog_type, "ShowModal", show_modal)
    monkeypatch.setattr(wx.Window, "PopupMenu", popup_menu)
    monkeypatch.setattr(wx.App, "MainLoop", main_loop)
    for name in (
        "MessageBox",
        "GetTextFromUser",
        "GetPasswordFromUser",
        "GetSingleChoice",
        "GetSingleChoiceIndex",
        "GetNumberFromUser",
        "FileSelector",
        "DirSelector",
    ):
        if hasattr(wx, name):
            monkeypatch.setattr(wx, name, unexpected_prompt)

    yield guard

    try:
        if getattr(request.node, "native_call_passed", False):
            guard.assert_consumed()
    finally:
        get_top_level_windows = vars(wx)["GetTopLevelWindows"]
        for window in list(get_top_level_windows()):
            window.Destroy()
        if wx.GetApp() is not None:
            wx.Yield()

__all__ = ["native_frame", "native_interaction", "wx_app"]
