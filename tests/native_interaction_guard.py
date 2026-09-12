from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

import pytest
import wx

_REAL_MAIN_LOOP = wx.App.MainLoop


@dataclass(frozen=True, slots=True)
class DialogExpectation:
    dialog_type: type[wx.Dialog]
    result: int
    values: tuple[str, ...] = ()
    path: str | None = None


class NativeInteractionGuard:
    def __init__(self) -> None:
        self._dialogs: deque[DialogExpectation] = deque()
        self._popups: deque[bool] = deque()
        self._main_loops = 0
        self.main_loop_apps: list[wx.App] = []

    def expect_dialog(
        self,
        dialog_type: type[wx.Dialog],
        result: int,
        values: tuple[str, ...] = (),
        path: str | None = None,
    ) -> None:
        self._dialogs.append(DialogExpectation(dialog_type, result, values, path))

    def expect_popup(self, result: bool = False) -> None:
        self._popups.append(result)

    def expect_main_loop(self) -> None:
        self._main_loops += 1

    def show_modal(self, dialog: wx.Dialog) -> int:
        if not self._dialogs:
            raise AssertionError(
                f"Unexpected {type(dialog).__name__}.ShowModal(); "
                "script it with native_interaction.expect_dialog()"
            )
        expected = self._dialogs.popleft()
        if not isinstance(dialog, expected.dialog_type):
            raise AssertionError(
                f"Expected {expected.dialog_type.__name__}.ShowModal(), got "
                f"{type(dialog).__name__}.ShowModal()"
            )
        if expected.path is not None:
            match dialog:
                case wx.FileDialog() | wx.DirDialog():
                    dialog.SetPath(expected.path)
                case _:
                    raise AssertionError(
                        f"Cannot set a path on {type(dialog).__name__}"
                    )
        match dialog:
            case wx.TextEntryDialog():
                if len(expected.values) > 1:
                    raise AssertionError(
                        "TextEntryDialog accepts at most one scripted value"
                    )
                if expected.values:
                    dialog.SetValue(expected.values[0])
            case _:
                controls = [
                    child
                    for child in dialog.GetChildren()
                    if isinstance(child, (wx.ComboBox, wx.TextCtrl))
                ]
                if len(controls) < len(expected.values):
                    raise AssertionError(
                        f"{type(dialog).__name__} has {len(controls)} editable "
                        f"controls, but {len(expected.values)} values were scripted"
                    )
                for control, value in zip(controls, expected.values, strict=False):
                    control.SetValue(value)
        return expected.result

    def popup_menu(self, window: wx.Window, menu: wx.Menu, *args, **kwargs) -> bool:
        del window, menu, args, kwargs
        if not self._popups:
            raise AssertionError(
                "Unexpected wx.Window.PopupMenu(); script it with "
                "native_interaction.expect_popup()"
            )
        return self._popups.popleft()

    def main_loop(self, app: wx.App) -> None:
        if self._main_loops == 0:
            raise AssertionError(
                "Unexpected wx.App.MainLoop(); script it with "
                "native_interaction.expect_main_loop()"
            )
        self._main_loops -= 1
        self.main_loop_apps.append(app)

    def assert_consumed(self) -> None:
        pending = len(self._dialogs) + len(self._popups) + self._main_loops
        if pending:
            raise AssertionError(
                f"{pending} scripted native interaction(s) were not consumed"
            )


def _unexpected_interaction(kind: str) -> AssertionError:
    return AssertionError(f"Unexpected native {kind}; script it at the caller boundary")


def install_native_interaction_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_modal(dialog: wx.Dialog) -> int:
        raise _unexpected_interaction(f"{type(dialog).__name__}.ShowModal()")

    def unexpected_popup(window: wx.Window, menu: wx.Menu, *args, **kwargs) -> bool:
        del window, menu, args, kwargs
        raise _unexpected_interaction("wx.Window.PopupMenu()")

    def unexpected_main_loop(app: wx.App) -> None:
        del app
        raise _unexpected_interaction("nested wx.App.MainLoop()")

    def unexpected_prompt(*args, **kwargs):
        del args, kwargs
        raise _unexpected_interaction("prompt")

    for dialog_type in (
        wx.Dialog,
        wx.MessageDialog,
        wx.FileDialog,
        wx.DirDialog,
        wx.TextEntryDialog,
    ):
        monkeypatch.setattr(dialog_type, "ShowModal", unexpected_modal)
    monkeypatch.setattr(wx.Window, "PopupMenu", unexpected_popup)
    monkeypatch.setattr(wx.App, "MainLoop", unexpected_main_loop)
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


def run_bounded_main_loop(
    app: wx.App, callback: Callable[[], object], *, timeout_ms: int
) -> None:
    failures: list[BaseException] = []

    def invoke() -> None:
        try:
            callback()
        except BaseException as error:
            failures.append(error)
        finally:
            app.ExitMainLoop()

    def expire() -> None:
        failures.append(
            AssertionError(f"native GUI callback timed out after {timeout_ms} ms")
        )
        app.ExitMainLoop()

    wx.CallAfter(invoke)
    timeout = wx.CallLater(timeout_ms, expire)
    try:
        _REAL_MAIN_LOOP(app)
    finally:
        timeout.Stop()
    if failures:
        raise failures[0]
