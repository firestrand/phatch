from __future__ import annotations

import sys

import pytest

pytest.importorskip("wx")
import wx

from phatch.lib.pyWx import popup

from .native_popup_support import CallbackLog, panel, pump_events

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def test_choice_delivers_deferred_change_while_editor_is_alive(native_frame) -> None:
    # Given
    callback = CallbackLog()
    editor = popup.EditPanel(
        panel(native_frame),
        "Choice",
        "one",
        {"choices": ["one", "two"], "on_change": callback},
    )
    assert isinstance(editor.edit, popup.ChoiceCtrl)
    editor.edit.SetSelection(1)

    # When
    editor.edit.OnChange()
    pump_events()

    # Then
    assert callback.values == ["two"]
    editor.Close()


def test_choice_close_returns_pending_selection_without_late_callback(
    native_frame, monkeypatch
) -> None:
    # Given
    callback = CallbackLog()
    unhandled: list[BaseException] = []
    monkeypatch.setattr(
        sys, "excepthook", lambda error_type, error, traceback: unhandled.append(error)
    )
    editor = popup.EditPanel(
        panel(native_frame),
        "Choice",
        "one",
        {"choices": ["one", "two"], "on_change": callback},
    )
    assert isinstance(editor.edit, popup.ChoiceCtrl)
    editor.edit.SetSelection(1)
    editor.edit.OnChange()

    # When
    value = editor.Close()
    pump_events()

    # Then
    assert value == "two"
    assert callback.values == []
    assert unhandled == []


def test_choice_rapid_close_and_reopen_only_delivers_live_editor_change(
    native_frame, monkeypatch
) -> None:
    # Given
    callback = CallbackLog()
    unhandled: list[BaseException] = []
    monkeypatch.setattr(
        sys, "excepthook", lambda error_type, error, traceback: unhandled.append(error)
    )
    first = popup.EditPanel(
        panel(native_frame),
        "Choice",
        "one",
        {"choices": ["one", "two"], "on_change": callback},
    )
    assert isinstance(first.edit, popup.ChoiceCtrl)
    first.edit.SetSelection(1)
    first.edit.OnChange()
    first.Close()
    second = popup.EditPanel(
        panel(native_frame),
        "Choice",
        "one",
        {"choices": ["one", "two"], "on_change": callback},
    )
    assert isinstance(second.edit, popup.ChoiceCtrl)
    second.edit.SetSelection(1)
    second.edit.OnChange()

    # When
    pump_events()

    # Then
    assert callback.values == ["two"]
    assert unhandled == []
    second.Close()


def test_editor_keys_without_callbacks_leave_editor_open(native_frame) -> None:
    # Given
    editor = popup.EditPanel(panel(native_frame), "Text", "value", {})

    # When
    for key_code in (wx.WXK_RETURN, wx.WXK_ESCAPE):
        event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        event.SetKeyCode(key_code)
        editor._OnKey(event)
    ordinary_event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    ordinary_event.SetKeyCode(ord("A"))
    editor._OnKey(ordinary_event)

    # Then
    assert editor
    assert ordinary_event.GetSkipped()
    editor.Close()
