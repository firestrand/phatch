from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass

import pytest
import wx

from phatch.lib.pyWx import clipboard
from phatch.pyWx import gui
from phatch.pyWx.frame_dependencies import FrameDependencies

from .native_frame_support import DialogRecorder, NativeWxApp

_REAL_MAIN_LOOP = wx.App.MainLoop

pytestmark = [
    pytest.mark.unit,
    pytest.mark.requires_display,
    pytest.mark.skipif(
        not sys.platform.startswith("linux"),
        reason="foreground wxGTK clipboard regression",
    ),
]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


@dataclass(frozen=True, slots=True)
class PasteObservation:
    clipboard_before_paste: str
    committed: str
    previous: str
    edit_history_delta: int
    document_history_entries: int


class ForegroundPasteDriver:
    def __init__(self) -> None:
        self.app = NativeWxApp()
        self.dialogs = DialogRecorder(self.app)
        self.frame = gui.Frame(
            "",
            None,
            wx.ID_ANY,
            "Task 7 native clipboard test",
            dependencies=FrameDependencies(
                dialog_service_factory=lambda _parent: self.dialogs
            ),
        )
        self.frame.SetName("task-7-native-clipboard-test")
        self.app.SetTopWindow(self.frame)
        self.observation: PasteObservation | None = None
        self.error: Exception | None = None
        self._clipboard_before_paste = ""
        self.finished = False

    def run(self) -> PasteObservation:
        self.frame.Show()
        self.frame.Raise()
        self._schedule(self._open_editor, 250)
        self._schedule(self._timeout, 5000)
        _REAL_MAIN_LOOP(self.app)
        try:
            if self.error is not None:
                raise self.error
            assert self.observation is not None
            return self.observation
        finally:
            self.frame.Destroy()
            wx.Yield()
            self.app.Destroy()

    def _schedule(self, callback: Callable[[], None], delay_ms: int) -> None:
        wx.CallLater(delay_ms, self._run_callback, callback)

    def _run_callback(self, callback: Callable[[], None]) -> None:
        try:
            callback()
        except Exception as error:
            self.error = error
            self._stop()

    def _open_editor(self) -> None:
        self.frame.controller.add_action_by_label("Write Tag")
        action = self.frame.tree.GetSelection()
        item = next(
            child
            for child in self.frame.tree.GetItemChildren(action)
            if self.frame.tree.GetItemData(child)[0] == "Value"
        )
        self.frame.tree.SelectItem(item)
        self._schedule(self._paste, 250)

    def _paste(self) -> None:
        panel = self.frame.tree.popup
        assert panel is not None
        control = panel.edit
        control.SetFocusFromKbd()
        control.SetTextSelection(0, len(control.GetValue()))
        assert clipboard.copy_text("<filename>")
        clipboard_before_paste = clipboard.get_text()
        assert clipboard_before_paste == "<filename>"
        assert control.CanPaste()
        control.Paste()
        self._clipboard_before_paste = clipboard_before_paste
        self._schedule(self._commit, 500)

    def _commit(self) -> None:
        panel = self.frame.tree.popup
        if panel is not None:
            event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
            event.SetKeyCode(wx.WXK_RETURN)
            wx.PostEvent(panel, event)
        self._schedule(self._verify, 250)

    def _verify(self) -> None:
        committed = next(
            field.value
            for field in self.frame.controller.current_document.actions[0].fields
            if field.field_id == "value"
        )
        assert committed == "<filename>"
        assert self.frame.controller.undo()
        previous = next(
            field.value
            for field in self.frame.controller.current_document.actions[0].fields
            if field.field_id == "value"
        )
        assert previous == "Phatch"
        assert self.frame.controller.undo()
        assert self.frame.IsEmpty()
        assert not self.frame.controller.undo()
        self.observation = PasteObservation(
            clipboard_before_paste=self._clipboard_before_paste,
            committed=committed,
            previous=previous,
            edit_history_delta=1,
            document_history_entries=2,
        )
        self.finished = True
        self._stop()

    def _timeout(self) -> None:
        if not self.finished:
            raise TimeoutError("native paste QA did not complete within 5 seconds")

    def _stop(self) -> None:
        self.frame.Close()
        self.app.ExitMainLoop()


def test_focused_native_paste_commits_exactly_one_history_entry(
    native_runtime,
) -> None:
    observation = ForegroundPasteDriver().run()

    print(json.dumps(asdict(observation), sort_keys=True))
    assert observation == PasteObservation(
        clipboard_before_paste="<filename>",
        committed="<filename>",
        previous="Phatch",
        edit_history_delta=1,
        document_history_entries=2,
    )
