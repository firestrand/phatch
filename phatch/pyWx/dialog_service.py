"""Dialog and notification helpers extracted from the wx frame."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import partial
from importlib import import_module
from types import SimpleNamespace
from typing import Any, TypeVar

from phatch.core import api as api_module
from phatch.core import ct
from phatch.lib import listData as list_data_module
from phatch.lib import notify as notify_module
from phatch.lib import system as system_module
from phatch.lib.reverse_translation import _translate as _

Dependency = TypeVar("Dependency")


def _module_default(dependency: Dependency) -> Dependency:
    return dependency


try:
    imported_wx = import_module("wx")
    imported_wx_lib_dialogs = import_module("wx.lib.dialogs")
except ModuleNotFoundError as error:
    if error.name not in {"wx", "wx.lib", "wx.lib.dialogs"}:
        raise

    class _WxStub:
        OK = 0
        ICON_ERROR = 0
        ICON_EXCLAMATION = 0
        ICON_INFORMATION = 0
        ICON_QUESTION = 0
        DEFAULT_DIALOG_STYLE = 0
        MAXIMIZE_BOX = 0
        RESIZE_BORDER = 0
        YES_NO = 0
        CANCEL = 0
        ID_CANCEL = -1
        ID_ABORT = -2
        ID_FORWARD = -3
        ID_NO = -4
        ID_YES = -5
        ID_OK = -6

        def MessageDialog(self, *args, **kwargs):
            raise NotImplementedError("wxPython required for dialog execution")

        def CallAfter(self, func, *args, **kwargs):
            func(*args, **kwargs)

        def GetApp(self):
            raise NotImplementedError("wxPython required for dialog execution")

    class _WxLibDialogsStub:
        class ScrolledMessageDialog:
            def __init__(self, *args, **kwargs):
                raise NotImplementedError("wxPython required for dialog execution")

    wx = _WxStub()
    wx_lib_dialogs = _WxLibDialogsStub()
    graphics_module = SimpleNamespace()
    dialogs_module = SimpleNamespace()
    images_module = SimpleNamespace(ICON_PHATCH_64=None)
    wx_default = _WxStub
    wx_lib_dialogs_default = _WxLibDialogsStub
    graphics_default = SimpleNamespace
    dialogs_default = SimpleNamespace
    images_default = partial(SimpleNamespace, ICON_PHATCH_64=None)
else:
    from phatch.lib.pyWx import graphics as imported_graphics
    from phatch.pyWx import dialogs as imported_dialogs
    from phatch.pyWx import images as imported_images

    wx = imported_wx
    wx_lib_dialogs = imported_wx_lib_dialogs
    graphics_module = imported_graphics
    dialogs_module = imported_dialogs
    images_module = imported_images

    wx_default = partial(_module_default, wx)
    wx_lib_dialogs_default = partial(_module_default, wx_lib_dialogs)
    graphics_default = partial(_module_default, graphics_module)
    dialogs_default = partial(_module_default, dialogs_module)
    images_default = partial(_module_default, images_module)


@dataclass(frozen=True)
class DialogDependencies:
    """Explicit dependencies used by the dialog service."""

    wx: Any = field(default_factory=wx_default)
    wx_lib_dialogs: Any = field(default_factory=wx_lib_dialogs_default)
    dialogs: Any = field(default_factory=dialogs_default)
    list_data: Any = field(default_factory=partial(_module_default, list_data_module))
    notify: Any = field(default_factory=partial(_module_default, notify_module))
    graphics: Any = field(default_factory=graphics_default)
    images: Any = field(default_factory=images_default)
    system: Any = field(default_factory=partial(_module_default, system_module))
    api: Any = field(default_factory=partial(_module_default, api_module))


class DialogService:
    """Encapsulates message dialogs, notifications, and status helpers."""

    def __init__(
        self, frame: Any, dependencies: DialogDependencies | None = None
    ) -> None:
        self._frame = frame
        self._deps = dependencies or DialogDependencies()

    # --- basic dialogs ---------------------------------------------
    def show_error(self, message: str):
        return self.show_message(
            message, style=self._deps.wx.OK | self._deps.wx.ICON_ERROR
        )

    def show_execute_dialog(
        self, result: dict, settings: dict, files: Sequence[str] | None = None
    ) -> None:
        dlg = self._deps.dialogs.ExecuteDialog(self._frame, drop=files)
        try:
            if settings.get("overwrite_existing_images_forced"):
                dlg.overwrite_existing_images.Disable()
            if files:
                settings["paths"] = files
            dlg.import_settings(settings)
            result["cancel"] = dlg.ShowModal() == self._deps.wx.ID_CANCEL
            if result["cancel"]:
                return
            dlg.export_settings(settings)
        finally:
            dlg.Destroy()

    def show_files_message(
        self, result: dict, message: str, title: str, files: Sequence[str]
    ) -> None:
        dlg = self._deps.dialogs.FilesDialog(self._frame, message, title, files)
        try:
            x0, _y0 = self._frame.GetSize()
            x1, y1 = dlg.GetSize()
            dlg.SetSize((max(x0, x1), max(y1, 200)))
            result["cancel"] = dlg.ShowModal() == self._deps.wx.ID_CANCEL
        finally:
            dlg.Destroy()

    def show_message(self, message: str, title: str = "", style: int | None = None):
        style = (
            self._deps.wx.OK | self._deps.wx.ICON_EXCLAMATION
            if style is None
            else style
        )
        parent = (
            self._frame if getattr(self._frame, "IsShown", lambda: False)() else None
        )
        dlg = self._deps.wx.MessageDialog(
            parent,
            message,
            f"{ct.INFO['name']} {title}",
            style,
        )
        try:
            return dlg.ShowModal()
        finally:
            dlg.Destroy()

    def show_status(self, message: str, log: bool = True) -> None:
        dlg = self._deps.dialogs.StatusDialog(self._frame)
        try:
            dlg.log.Show(log)
            dlg.SetMessage(message)
            dlg.ShowModal()
        finally:
            dlg.Destroy()

    def show_question(self, message: str, style: int | None = None):
        style = (
            self._deps.wx.YES_NO | self._deps.wx.ICON_QUESTION
            if style is None
            else style
        )
        return self.show_message(message, style=style)

    def show_image_tree(
        self,
        result: dict,
        image_infos: Sequence[Sequence[Any]],
        widths: Sequence[int],
        headers: Sequence[str],
        ok_label: str = "&OK",
        buttons: bool = False,
        modal: bool = False,
    ) -> None:
        data = self._deps.list_data.files_data_dict(image_infos)
        dlg = self._deps.dialogs.ImageTreeDialog(
            data,
            self._deps.list_data.DataDict,
            headers,
            self._frame,
            size=(600, self._deps.dialogs.get_max_height(300)),
        )
        dlg.SetColumnWidths(*widths)
        dlg.SetOkLabel(ok_label)
        dlg.ShowButtons(buttons)
        if modal or buttons:
            answer = dlg.ShowModal()
            dlg.Destroy()
            result["answer"] = answer == self._deps.wx.ID_OK
        else:
            dlg.Show()

    def show_report(self) -> None:
        report = self._deps.wx.GetApp().report
        if report:
            modal = not hasattr(self._frame, "controller")
            self.show_image_tree(
                {},
                report,
                widths=(200, 60, 60, 60, 500),
                headers=["filename", "width", "height", "mode", "source"],
                buttons=False,
                modal=modal,
            )
        else:
            self.show_message(_("No images have been processed to report."))

    def show_log(self) -> None:
        if os.path.exists(ct.USER_LOG_PATH):
            with open(ct.USER_LOG_PATH) as log_file:
                message = log_file.read().strip()
            if not message:
                message = _("Hooray, no issues!")
        else:
            message = _("Nothing has been logged yet.")
        self.show_scrolled_message(
            message,
            f"{_('Log')} - {ct.USER_LOG_PATH}",
        )

    def show_info(self, message: str, title: str = ""):
        return self.show_message(
            message, title, style=self._deps.wx.OK | self._deps.wx.ICON_INFORMATION
        )

    def show_progress(
        self, title: str, parent_max: int, child_max: int = 1, message: str = ""
    ) -> None:
        self._deps.dialogs.ProgressDialog(
            self._frame, title, parent_max, child_max, message
        )

    def show_progress_error(
        self, result: dict, message: str, ignore: bool = True
    ) -> None:
        message += "\n\n" + self._deps.api.SEE_LOG
        dlg = self._deps.dialogs.ErrorDialog(self._frame, message, ignore)
        try:
            answer = dlg.ShowModal()
            result["stop_for_errors"] = not dlg.future_errors.GetValue()
        finally:
            dlg.Destroy()
        if answer == self._deps.wx.ID_ABORT:
            result["answer"] = _("abort")
            self.show_log()
        elif answer == self._deps.wx.ID_FORWARD:
            result["answer"] = _("skip")
        else:
            result["answer"] = _("ignore")

    def show_scrolled_message(self, message: str, title: str, **options: Any) -> None:
        scrolled_dialog = self._deps.wx_lib_dialogs.ScrolledMessageDialog(
            self._frame,
            message,
            title,
            style=self._deps.wx.DEFAULT_DIALOG_STYLE
            | self._deps.wx.MAXIMIZE_BOX
            | self._deps.wx.RESIZE_BORDER,
            **options,
        )
        scrolled_dialog.ShowModal()
        scrolled_dialog.Destroy()

    def show_notification(
        self, message: str, force: bool = False, report: list | None = None
    ) -> None:
        self.set_report(report)
        app = self._deps.wx.GetApp()
        active = app.IsActive() or self._frame.IsActive()
        if force or not active:
            self._deps.notify.send(
                title=self._deps.system.filename_to_title(self._frame.filename),
                message=message,
                icon=self._frame.get_icon_filename(),
                wxicon=self._deps.graphics.bitmap(self._deps.images.ICON_PHATCH_64),
            )
        if not active:
            self._frame.RequestUserAttention()

    # --- settings helpers ------------------------------------------
    def get_setting(self, name: str):
        return self._deps.wx.GetApp().settings[name]

    def set_setting(self, name: str, value: Any) -> None:
        self._deps.wx.GetApp().settings[name] = value

    def set_report(self, report: list | None) -> None:
        self._deps.wx.GetApp().report = report
