from __future__ import annotations

from phatch.core import ct
from phatch.pyWx.file_menu import wx as file_wx
from phatch.services.file_dialogs import DialogSelection
from tests.unit.app.test_file_menu_coordinator import (
    StubFileDialogs,
    StubFileHistory,
    StubFrame,
    build_coordinator,
)


def test_dirty_no_response_proceeds_without_saving() -> None:
    frame = StubFrame()
    frame.controller.state.dirty = True
    frame.message_response = file_wx.ID_NO
    coordinator, *_ = build_coordinator(frame)

    assert coordinator.confirm_proceed() is True
    assert frame.saved_paths == []


def test_guarded_actions_stop_when_confirmation_fails(monkeypatch) -> None:
    frame = StubFrame()
    coordinator, *_ = build_coordinator(frame)
    monkeypatch.setattr(coordinator, "confirm_proceed", lambda: False)

    coordinator.new_actionlist()
    coordinator.open_actionlist()
    coordinator.export_actionlist_to_clipboard()
    coordinator.export_recent_to_clipboard()
    coordinator.export_inspector_to_clipboard()
    coordinator.open_recent(0)

    assert frame.opened_paths == []
    assert frame.info_messages == []


def test_cancelled_dialogs_do_not_open_or_save() -> None:
    frame = StubFrame()
    coordinator, *_ = build_coordinator(frame)

    coordinator.open_actionlist()

    assert frame.opened_paths == []
    assert coordinator.save_as() is False


def test_save_as_overwrites_after_confirmation(tmp_path) -> None:
    path = tmp_path / "existing.phatch"
    path.write_text("old")
    frame = StubFrame()
    frame.filename = str(path)
    dialogs = StubFileDialogs()
    dialogs.save_selection = DialogSelection(str(path))
    coordinator, *_ = build_coordinator(frame, file_dialogs=dialogs)

    assert coordinator.save_as() is True
    assert frame.saved_paths == [str(path)]
    assert dialogs.save_kwargs is not None
    assert dialogs.save_kwargs["default_dir"] == str(tmp_path)


def test_clipboard_exports_and_recent_open() -> None:
    frame = StubFrame()
    frame.filename = "workflow.phatch"
    history = StubFileHistory()
    history.entries = ["recent.phatch"]
    coordinator, _, _, copied = build_coordinator(frame, file_history=history)

    coordinator.export_recent_to_clipboard()
    coordinator.export_inspector_to_clipboard()
    coordinator.open_recent(0)

    assert copied == [ct.COMMAND["RECENT"], ct.COMMAND["INSPECTOR"]]
    assert frame.opened_paths == ["recent.phatch"]


def test_history_filters_blank_and_missing_files(tmp_path) -> None:
    existing = tmp_path / "present.phatch"
    existing.write_text("data")
    history = StubFileHistory()
    history.entries = ["", "  ", str(existing)]
    coordinator, *_ = build_coordinator(StubFrame(), file_history=history)

    assert coordinator.get_file_history() == [str(existing)]
    coordinator.load_file_history(None)
    coordinator.load_file_history(["missing.phatch", str(existing)])

    assert history.entries[-1] == str(existing)
