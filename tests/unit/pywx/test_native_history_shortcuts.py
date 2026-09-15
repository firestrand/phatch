from __future__ import annotations

import pytest
import wx

from phatch.pyWx import gui
from phatch.pyWx.frame_dependencies import FrameDependencies
from phatch.pyWx.ui_descriptors import HistoryAccelerator
from phatch.pyWx.wxGlade import frame as generated_frame

from .native_popup_support import pump_events

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


def test_text_entry_native_undo_does_not_traverse_document_history(
    native_frame_harness,
) -> None:
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    frame.description.SetFocus()
    frame.description.SetValue("first")
    frame.description.SetValue("second")
    document_before = frame.controller.current_document

    frame.on_menu_edit_undo(None)
    pump_events()

    assert frame.controller.current_document.actions == document_before.actions
    assert frame.controller.current_document.description == "first"
    assert not frame.IsEmpty()


def test_document_redo_runs_when_focused_text_entry_has_no_local_redo(
    native_frame_harness,
    monkeypatch,
) -> None:
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    frame.controller.undo()
    frame.description.SetFocus()
    pump_events()
    assert not frame.description.CanRedo()
    monkeypatch.setattr(
        gui.wx.Window,
        "FindFocus",
        staticmethod(lambda: frame.description),
    )

    frame.on_menu_edit_redo(None)

    assert not frame.IsEmpty()


def test_text_entry_native_redo_does_not_traverse_document_history(
    native_frame_harness,
    monkeypatch,
) -> None:
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    document_before = frame.controller.current_document

    class Focus:
        redone = False

        def CanRedo(self) -> bool:
            return True

        def Redo(self) -> None:
            self.redone = True

    focus = Focus()
    monkeypatch.setattr(gui.wx.Window, "FindFocus", staticmethod(lambda: focus))

    frame.on_menu_edit_redo(None)

    assert focus.redone
    assert frame.controller.current_document.actions == document_before.actions


def test_text_entry_native_undo_does_not_traverse_document_history_when_available(
    native_frame_harness,
    monkeypatch,
) -> None:
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    document_before = frame.controller.current_document

    class Focus:
        undone = False

        def CanUndo(self) -> bool:
            return True

        def Undo(self) -> None:
            self.undone = True

    focus = Focus()
    monkeypatch.setattr(gui.wx.Window, "FindFocus", staticmethod(lambda: focus))

    frame.on_menu_edit_undo(None)

    assert focus.undone
    assert frame.controller.current_document.actions == document_before.actions


def test_history_menu_items_expose_platform_native_accelerators(
    native_frame_harness,
) -> None:
    frame = native_frame_harness.frame
    expected_modifier = wx.ACCEL_CMD if wx.Platform == "__WXMAC__" else wx.ACCEL_CTRL

    undo = frame.menu_edit_undo.GetAccel()
    redo = frame.menu_edit_redo.GetAccel()

    assert undo.GetFlags() == expected_modifier
    assert undo.GetKeyCode() == ord("Z")
    assert redo.GetFlags() == expected_modifier | wx.ACCEL_SHIFT
    assert redo.GetKeyCode() == ord("Z")


def test_history_menu_keeps_primary_accelerator_when_command_has_alternative(
    native_frame_harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accelerators = (
        HistoryAccelerator("undo", "ctrl", "Z"),
        HistoryAccelerator("redo", "ctrl", "Z", shifted=True),
        HistoryAccelerator("redo", "ctrl", "Y"),
    )
    monkeypatch.setattr(
        generated_frame,
        "history_accelerators",
        lambda _platform: accelerators,
    )
    dependencies = FrameDependencies(
        dialog_service_factory=lambda _parent: native_frame_harness.dialogs,
    )
    frame = gui.Frame(
        "",
        None,
        wx.ID_ANY,
        "history shortcuts",
        dependencies=dependencies,
    )
    try:
        redo = frame.menu_edit_redo.GetAccel()

        assert redo.GetFlags() == wx.ACCEL_CTRL | wx.ACCEL_SHIFT
        assert redo.GetKeyCode() == ord("Z")
    finally:
        frame.unsubscribe_all()
        frame.Destroy()
        wx.Yield()


def test_destroyed_frame_receives_no_history_callback(native_frame_harness) -> None:
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")

    frame.on_close()
    frame.controller.undo()
    pump_events()

    assert not frame
    assert frame._listeners == []
