"""Dialog and notification helpers extracted from the wx frame."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional, Sequence
from types import SimpleNamespace

from phatch.core import api as api_module, ct
from phatch.lib import listData as list_data_module
from phatch.lib import notify as notify_module
from phatch.lib import system as system_module

try:  # pragma: no cover - requires wxPython
    from phatch.lib.pyWx import graphics as graphics_module
except ImportError:  # pragma: no cover - fallback for headless tests
    graphics_module = SimpleNamespace()

try:  # pragma: no cover - requires wxPython
    from phatch.pyWx import dialogs as dialogs_module
except ImportError:  # pragma: no cover - fallback for headless tests
    dialogs_module = SimpleNamespace()

try:  # pragma: no cover - requires wxPython
    from phatch.pyWx import images as images_module
except ImportError:  # pragma: no cover - fallback for headless tests
    images_module = SimpleNamespace(ICON_PHATCH_64=None)

try:  # pragma: no cover - provided by runtime environment
    import wx  # type: ignore
    import wx.lib.dialogs as wx_lib_dialogs  # type: ignore
except ImportError:  # pragma: no cover - headless fall-back

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

        def CallAfter(self, func, *args, **kwargs):  # noqa: D401 - stub
            func(*args, **kwargs)

        def GetApp(self):  # noqa: D401 - stub
            raise NotImplementedError("wxPython required for dialog execution")

    class _WxLibDialogsStub:
        class ScrolledMessageDialog:  # type: ignore[dead-code]
            def __init__(self, *args, **kwargs):
                raise NotImplementedError("wxPython required for dialog execution")

    wx = _WxStub()  # type: ignore
    wx_lib_dialogs = _WxLibDialogsStub()  # type: ignore


@dataclass(frozen=True)
class DialogDependencies:
    """Explicit dependencies used by the dialog service."""

    wx: Any = wx
    wx_lib_dialogs: Any = wx_lib_dialogs
    dialogs: Any = dialogs_module
    list_data: Any = list_data_module
    notify: Any = notify_module
    graphics: Any = graphics_module
    images: Any = images_module
    system: Any = system_module
    api: Any = api_module


class DialogService:
    """Encapsulates message dialogs, notifications, and status helpers."""

    def __init__(self, frame: Any, dependencies: Optional[DialogDependencies] = None) -> None:
        self._frame = frame
        self._deps = dependencies or DialogDependencies()

    # --- basic dialogs ---------------------------------------------
    def show_error(self, message: str):
        return self.show_message(message, style=self._deps.wx.OK | self._deps.wx.ICON_ERROR)

    def show_execute_dialog(self, result: dict, settings: dict, files: Optional[Sequence[str]] = None) -> None:
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

    def show_files_message(self, result: dict, message: str, title: str, files: Sequence[str]) -> None:
        dlg = self._deps.dialogs.FilesDialog(self._frame, message, title, files)
        try:
            x0, y0 = self._frame.GetSize()
            x1, y1 = dlg.GetSize()
            dlg.SetSize((max(x0, x1), max(y1, 200)))
            result["cancel"] = dlg.ShowModal() == self._deps.wx.ID_CANCEL
        finally:
            dlg.Destroy()

    def show_message(self, message: str, title: str = "", style: int | None = None):
        style = self._deps.wx.OK | self._deps.wx.ICON_EXCLAMATION if style is None else style
        parent = self._frame if getattr(self._frame, "IsShown", lambda: False)() else None
        dlg = self._deps.wx.MessageDialog(
            parent,
            message,
            "%(name)s " % ct.INFO + title,
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
        style = self._deps.wx.YES_NO | self._deps.wx.ICON_QUESTION if style is None else style
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
            "%s - %s" % (_("Log"), ct.USER_LOG_PATH),
        )

    def show_info(self, message: str, title: str = ""):
        return self.show_message(message, title, style=self._deps.wx.OK | self._deps.wx.ICON_INFORMATION)

    def show_progress(self, title: str, parent_max: int, child_max: int = 1, message: str = "") -> None:
        self._deps.dialogs.ProgressDialog(self._frame, title, parent_max, child_max, message)

    def show_progress_error(self, result: dict, message: str, ignore: bool = True) -> None:
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

    def show_notification(self, message: str, force: bool = False, report: Optional[list] = None) -> None:
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

    def set_report(self, report: Optional[list]) -> None:
        self._deps.wx.GetApp().report = report


try:  # pragma: no cover - runtime gettext injection
    _  # type: ignore[name-defined]
except NameError:  # pragma: no cover - fallback for tests
    import builtins

    if "_" not in builtins.__dict__:
        builtins.__dict__["_"] = lambda value: value
    _ = builtins.__dict__["_"]
