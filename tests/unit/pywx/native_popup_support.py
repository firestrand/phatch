from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Protocol

import pytest

pytest.importorskip("wx")
import wx


@dataclass(slots=True)
class CallbackLog:
    values: list[str] = field(default_factory=list)

    def __call__(self, value: str) -> None:
        self.values.append(value)


class KeyHandler(Protocol):
    def onKeyDown(self, event: wx.KeyEvent) -> None: ...


class TextValueControl(Protocol):
    def SetFocus(self) -> None: ...

    def SetSelection(self, from_: int, to_: int) -> None: ...

    def Replace(self, from_: int, to_: int, value: str) -> None: ...

    def GetLastPosition(self) -> int: ...


class SelectionDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, value: str):
        super().__init__(parent)
        self.image_path = wx.TextCtrl(self, value=value)
        self.path_shown = True

    def ShowPath(self, state: bool) -> None:
        self.path_shown = state

    def SetValue(self, value: str) -> None:
        self.image_path.SetValue(value)

def pump_events() -> None:
    app = wx.GetApp()
    if app is None:
        return
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()


def wait_until(predicate: Callable[[], bool], timeout_ms: int = 1000) -> None:
    deadline = time.monotonic() + timeout_ms / 1000
    while not predicate():
        pump_events()
        if time.monotonic() >= deadline:
            pytest.fail("native wx condition did not become true before timeout")


@pytest.fixture
def wx_app() -> Iterator[wx.AppConsole]:
    existing_app = wx.GetApp()
    if existing_app is not None:
        yield existing_app
        return
    app = wx.App(False)
    destroy_app = app.Destroy
    try:
        yield app
    finally:
        pump_events()
        if wx.GetApp() is app:
            destroy_app()


@pytest.fixture
def native_frame(wx_app: wx.App, initialized_runtime) -> Iterator[wx.Frame]:
    frame = wx.Frame(None, title="Native popup test", size=wx.Size(480, 240))
    panel = wx.Panel(frame)
    panel.SetName("test-panel")
    frame.Show()
    wx_app.SetTopWindow(frame)
    wait_until(frame.IsShownOnScreen)
    yield frame
    for child in list(frame.GetChildren()):
        if hasattr(child, "Close") and child.__class__.__name__ == "EditPanel":
            child.Close()
    frame.Destroy()
    pump_events()


def panel(frame: wx.Frame) -> wx.Panel:
    child = frame.FindWindowByName("test-panel")
    assert isinstance(child, wx.Panel)
    return child


def send_key(control: KeyHandler, key_code: int) -> None:
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(key_code)
    control.onKeyDown(event)
    pump_events()


def replace_text(control: TextValueControl, value: str) -> None:
    control.SetFocus()
    control.SetSelection(-1, -1)
    control.Replace(0, control.GetLastPosition(), value)
    pump_events()
