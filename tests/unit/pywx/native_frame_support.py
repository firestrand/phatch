from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import wx

if sys.platform.startswith("linux") and not (
    os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
):
    pytest.skip("native wxPython tests require a display", allow_module_level=True)

from phatch import phatch
from phatch.core import api, config, settings
from phatch.core.user_paths import (
    PathResolution,
    current_platform,
    initialize_user_paths,
    resolve_user_paths,
)
from phatch.pyWx import gui
from phatch.pyWx.dialog_service import DialogService
from phatch.pyWx.frame_dependencies import FrameDependencies


class DialogRecorder(DialogService):
    def __init__(self, app: NativeWxApp) -> None:
        self.app = app
        self.errors: list[str] = []
        self.messages: list[tuple[str, str]] = []
        self.infos: list[tuple[str, str]] = []
        self.questions: list[str] = []
        self.calls: list[tuple[str, tuple]] = []
        self.question_answer = wx.ID_YES
        self.message_answer = wx.ID_OK
        self.report: list[tuple[str, ...]] | None = None

    def get_setting(self, name: str):
        return self.app.settings[name]

    def set_setting(self, name: str, value) -> None:
        self.app.settings[name] = value

    def show_error(self, message: str):
        self.errors.append(message)
        return wx.ID_OK

    def show_message(self, message: str, title: str = "", style=None):
        self.messages.append((message, title))
        return self.message_answer

    def show_info(self, message: str, title: str = ""):
        self.infos.append((message, title))
        return wx.ID_OK

    def show_question(self, message: str, style=None):
        self.questions.append(message)
        return self.question_answer

    def set_report(self, report: list[tuple[str, ...]] | None) -> None:
        self.report = report
        self.app.report = report

    def show_execute_dialog(self, result, settings, files=None) -> None:
        self.calls.append(("execute", (result, settings, files)))

    def show_files_message(self, result, message, title, files) -> None:
        self.calls.append(("files", (result, message, title, files)))

    def show_status(self, message: str, log: bool = True) -> None:
        self.calls.append(("status", (message, log)))

    def show_image_tree(
        self, result, image_infos, widths, headers, ok_label="&OK", buttons=False,
        modal=False,
    ) -> None:
        self.calls.append(
            (
                "image_tree",
                (result, image_infos, widths, headers, ok_label, buttons, modal),
            )
        )

    def show_report(self) -> None:
        self.calls.append(("report", ()))

    def show_log(self) -> None:
        self.calls.append(("log", ()))

    def show_progress(
        self, title: str, parent_max: int, child_max: int = 1, message: str = ""
    ) -> None:
        self.calls.append(("progress", (title, parent_max, child_max, message)))

    def show_progress_error(self, result, message: str, ignore: bool = True) -> None:
        self.calls.append(("progress_error", (result, message, ignore)))

    def show_scrolled_message(self, message: str, title: str, **options) -> None:
        self.calls.append(("scrolled", (message, title, options)))

    def show_notification(self, message: str, force: bool = False, report=None) -> None:
        self.calls.append(("notification", (message, force, report)))


class NativeWxApp(wx.App):
    def __init__(self) -> None:
        self.settings = settings.create_settings(config.PATHS)
        self.report: list[tuple[str, ...]] | None = []
        self.save_settings_calls = 0
        super().__init__(False)

    def _saveSettings(self) -> None:
        self.save_settings_calls += 1


@dataclass(frozen=True, slots=True)
class NativeFrameHarness:
    app: NativeWxApp
    frame: gui.Frame
    dialogs: DialogRecorder
    root: Path

    def dispatch_menu(self, item) -> None:
        event = wx.CommandEvent(wx.EVT_MENU.typeId, item.GetId())
        self.frame.ProcessEvent(event)
        wx.Yield()


@pytest.fixture
def native_runtime(isolated_runtime):
    user_paths = resolve_user_paths(
        PathResolution(
            isolated_runtime.env,
            current_platform(),
            portable_root=isolated_runtime.root,
        )
    )
    initialize_user_paths(user_paths)
    config.init_config_paths(phatch.create_paths(".."), user_paths=user_paths)
    api.init()
    return isolated_runtime


@pytest.fixture
def native_frame_harness(native_runtime) -> Iterator[NativeFrameHarness]:
    app = NativeWxApp()
    frame: gui.Frame | None = None
    try:
        dialogs = DialogRecorder(app)
        dependencies = FrameDependencies(
            dialog_service_factory=lambda _parent: dialogs,
        )
        frame = gui.Frame("", None, wx.ID_ANY, "native", dependencies=dependencies)
        app.SetTopWindow(frame)
        frame.Show()
        wx.Yield()
        harness = NativeFrameHarness(app, frame, dialogs, native_runtime.root)
        yield harness
    finally:
        if frame is not None and getattr(frame, "_listeners", None):
            frame.unsubscribe_all()
        for window in tuple(vars(wx)["GetTopLevelWindows"]()):
            window.Destroy()
        wx.Yield()
        wx.App.Destroy(app)
