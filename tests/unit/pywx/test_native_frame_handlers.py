from __future__ import annotations

import pytest

from phatch.core import config
from phatch.lib import formField
from phatch.services.action_list import ActionListService

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


class ActionServiceRecorder(ActionListService):
    def __init__(self) -> None:
        self.executions: list[tuple] = []

    def execute(
        self, actions, settings, update_callback=None, recovery=None, **options
    ) -> None:
        self.executions.append(
            (tuple(actions), settings, update_callback, recovery, options)
        )


class FileMenuRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    def new_actionlist(self) -> None:
        self.calls.append(("new", ()))

    def open_actionlist(self) -> None:
        self.calls.append(("open", ()))

    def save_current(self) -> bool:
        self.calls.append(("save", ()))
        return True

    def save_as(self) -> bool:
        self.calls.append(("save_as", ()))
        return True

    def export_actionlist_to_clipboard(self) -> None:
        self.calls.append(("export_actionlist", ()))

    def export_recent_to_clipboard(self) -> None:
        self.calls.append(("export_recent", ()))

    def export_inspector_to_clipboard(self) -> None:
        self.calls.append(("export_inspector", ()))

    def open_recent(self, index: int) -> None:
        self.calls.append(("recent", (index,)))

    def confirm_proceed(self) -> bool:
        self.calls.append(("confirm", ()))
        return True


@pytest.mark.parametrize(
    ("method", "arguments", "expected"),
    [
        ("show_execute_dialog", ({}, {}), "execute"),
        ("show_files_message", ({}, "message", "title", ["file"]), "files"),
        ("show_status", ("working", False), "status"),
        ("show_image_tree", ({}, [], [], []), "image_tree"),
        ("show_report", (), "report"),
        ("show_log", (), "log"),
        ("show_progress", ("work", 2, 3, "step"), "progress"),
        ("show_progress_error", ({}, "failed", False), "progress_error"),
        ("show_scrolled_message", ("body", "title"), "scrolled"),
        ("show_notification", ("finished", True, []), "notification"),
    ],
)
def test_dialog_methods_delegate_from_real_frame(
    native_frame_harness, method: str, arguments: tuple, expected: str
) -> None:
    # Given: a real frame with a non-modal dialog interaction boundary
    frame = native_frame_harness.frame

    # When: one frame dialog API is invoked
    getattr(frame, method)(*arguments)

    # Then: the interaction crosses the dialog service boundary once
    assert native_frame_harness.dialogs.calls[-1][0] == expected


def test_basic_message_methods_return_boundary_answers(native_frame_harness) -> None:
    # Given: a real frame whose interaction boundary has native wx answers
    frame = native_frame_harness.frame

    # When: each basic message API is invoked
    answers = (
        frame.show_error("error"),
        frame.show_message("message", "title"),
        frame.show_info("info", "title"),
        frame.show_question("question"),
    )

    # Then: answers and recorded user-facing state are preserved
    assert answers == (wx.ID_OK, wx.ID_OK, wx.ID_OK, wx.ID_YES)
    assert native_frame_harness.dialogs.errors == ["error"]
    assert native_frame_harness.dialogs.messages == [("message", "title")]
    assert native_frame_harness.dialogs.infos == [("info", "title")]
    assert native_frame_harness.dialogs.questions == ["question"]


def test_file_menu_handlers_route_native_events(native_frame_harness) -> None:
    # Given: a real frame with the file workflow boundary observed
    frame = native_frame_harness.frame
    recorder = FileMenuRecorder()
    frame.file_menu = recorder
    history_event = wx.CommandEvent(wx.EVT_MENU.typeId, wx.ID_FILE1 + 2)

    # When: frame file handlers receive their native menu events
    frame.on_menu_file_new()
    frame.on_menu_file_open(None)
    assert frame.on_menu_file_save(None)
    assert frame.on_menu_file_save_as()
    frame.on_menu_file_export_actionlist_to_clipboard(None)
    frame.on_menu_file_export_recent_to_clipboard(None)
    frame.on_menu_file_export_inspector_to_clipboard(None)
    frame.on_menu_file_history(history_event)

    # Then: every handler routes to the coordinator with the event payload
    assert [name for name, _arguments in recorder.calls] == [
        "new",
        "open",
        "save",
        "save_as",
        "export_actionlist",
        "export_recent",
        "export_inspector",
        "recent",
    ]
    assert recorder.calls[-1][1] == (2,)


def test_execute_and_drop_handlers_forward_real_tree_actions(
    native_frame_harness,
) -> None:
    # Given: a native tree and a recording execution boundary
    frame = native_frame_harness.frame
    service = ActionServiceRecorder()
    frame._action_service = service
    frame.controller.add_action_by_label("Border")

    # When: execute and file-drop handlers run
    frame.on_menu_tools_execute(None)
    frame.on_drop(["one.png"], 4, 5)

    # Then: both executions contain the exported real action
    assert len(service.executions) == 2
    assert service.executions[0][0][0].label == "Border"
    assert service.executions[1][4] == {"paths": ["one.png"], "drop": True}


def test_tree_view_and_size_handlers_operate_on_native_controls(
    native_frame_harness,
) -> None:
    # Given: a populated real tree and native size event
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    frame.enable_actions(True)
    size_event = wx.SizeEvent(frame.GetSize(), frame.GetId())

    # When: expand, collapse, drag-end, and size handlers execute
    frame.on_menu_view_expand_all(None)
    frame.on_menu_view_collapse_all(None)
    frame.on_tree_end_drag(size_event)
    wx.Yield()
    frame.on_size(size_event)

    # Then: event flow marks the action list dirty without invalidating controls
    assert frame.controller.state.dirty
    assert frame.tree.IsShown()


def test_safe_mode_rejection_restores_checked_native_menu(native_frame_harness) -> None:
    # Given: safe mode and a dialog boundary rejecting unsafe mode
    frame = native_frame_harness.frame
    formField.set_safe(True)
    native_frame_harness.dialogs.question_answer = wx.ID_NO

    # When: unsafe mode is requested
    frame.set_safe_mode(False)

    # Then: safe mode and the native check item remain enabled
    assert formField.get_safe()
    assert frame.menu_tools.IsChecked(frame.menu_tools_safe.GetId())


def test_safe_mode_acceptance_updates_runtime(native_frame_harness) -> None:
    # Given: safe mode and a dialog boundary accepting unsafe mode
    formField.set_safe(True)

    # When: unsafe mode is confirmed
    native_frame_harness.frame.set_safe_mode(False)

    # Then: the shared runtime mode changes
    assert not formField.get_safe()
    formField.set_safe(True)


def test_dynamic_menu_item_dispatches_on_real_frame(native_frame_harness) -> None:
    # Given: a native menu and a callback installed through the plugin seam
    calls: list[int] = []

    def on_dynamic(frame, event) -> None:
        calls.append(event.GetId())

    item_id = native_frame_harness.frame.install_menu_item(
        native_frame_harness.frame.menu_tools,
        "menu_tools_dynamic",
        "Dynamic",
        on_dynamic,
    )

    # When: wx dispatches the installed item
    native_frame_harness.dispatch_menu(native_frame_harness.frame.menu_tools_dynamic)

    # Then: the bound callback receives the generated native ID
    assert calls == [item_id]


def test_update_fonts_handler_invokes_config_boundary(
    native_frame_harness, monkeypatch
) -> None:
    # Given: the real frame and an observed font-scan boundary
    calls: list[bool] = []
    monkeypatch.setattr(config, "check_fonts", calls.append)

    # When: the update-fonts handler runs
    native_frame_harness.frame.on_menu_tools_update_fonts(None)

    # Then: a forced scan is requested exactly once
    assert calls == [True]
