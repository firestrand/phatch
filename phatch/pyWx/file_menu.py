"""Coordinator that handles wx file menu operations for the main frame."""

from __future__ import annotations

import builtins
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from phatch.core import ct
from phatch.pyWx.controller_history import ActionListState
from phatch.services.file_dialogs import DialogSelection

_ = getattr(builtins, "_", lambda value: value)

try:  # pragma: no cover - optional at test time
    import wx
except ImportError:  # pragma: no cover - used in headless test environments

    class _WxStub:  # minimal shim so unit tests run without wxPython
        ID_CANCEL = -1
        ID_YES = -2
        ID_NO = -3
        YES_NO = 0
        CANCEL = 0
        ICON_EXCLAMATION = 0
        FD_OPEN = 0
        FD_SAVE = 0

    wx = _WxStub()


class DescriptionControl(Protocol):
    def SetValue(self, value: str) -> None: ...


class FileMenuController(Protocol):
    state: ActionListState

    def new_actionlist(self) -> ActionListState: ...

    def begin_open(self) -> None: ...

    def finish_open(self, *, success: bool) -> None: ...

    def begin_save(self) -> None: ...

    def finish_save(self, *, success: bool) -> None: ...


class FileMenuFrame(Protocol):
    controller: FileMenuController
    filename: str
    description: DescriptionControl

    def show_message(self, message: str, *, style: int) -> int: ...

    def show_question(self, message: str) -> int: ...

    def show_info(self, message: str) -> None: ...

    def is_protected_actionlist(self, filename: str) -> bool: ...

    def show_description(self, visible: bool) -> None: ...

    def enable_actions(self, enabled: bool) -> None: ...

    def _set_filename(self, filename: str) -> None: ...

    def _open(self, path: str) -> None: ...

    def _save(self, path: str | None = None) -> None: ...


class FileHistory(Protocol):
    def GetHistoryFile(self, index: int) -> str: ...

    def GetCount(self) -> int: ...

    def AddFileToHistory(self, filename: str) -> None: ...


class FileDialogs(Protocol):
    def open_actionlist(
        self,
        *,
        parent: FileMenuFrame,
        message: str,
        default_dir: str,
        wildcard: str,
        style: int,
    ) -> DialogSelection | None: ...

    def save_actionlist(
        self,
        *,
        parent: FileMenuFrame,
        message: str,
        default_dir: str,
        wildcard: str,
        style: int,
    ) -> DialogSelection | None: ...


@dataclass(frozen=True, slots=True)
class ClipboardMessages:
    """Bundle of user-facing clipboard hints."""

    paste_hint: str
    actionlist: str
    recent: str
    inspector: str


class FileMenuCoordinator:
    """Encapsulates file menu workflows so the frame stays thinner."""

    def __init__(
        self,
        *,
        frame: FileMenuFrame,
        file_history: FileHistory,
        file_dialogs: FileDialogs,
        clipboard_messages: ClipboardMessages,
        ensure_suffix: Callable[[str], str],
        copy_text: Callable[[str], None],
    ) -> None:
        self._frame = frame
        self._file_history = file_history
        self._file_dialogs = file_dialogs
        self._clipboard_messages = clipboard_messages
        self._ensure_suffix = ensure_suffix
        self._copy_text = copy_text

    # --- guards ---------------------------------------------------
    def confirm_proceed(self) -> bool:
        """Return True when it is safe to continue after dirty-check."""

        state = self._frame.controller.state
        if not getattr(state, "dirty", False):
            return True
        answer = self._frame.show_message(
            f'{_("Save last changes to")}\n"{self._frame.filename}"?',
            style=self._prompt_style(),
        )
        if answer == getattr(wx, "ID_CANCEL", -1):
            return False
        if answer == getattr(wx, "ID_YES", -1):
            return self.save_current()
        return True

    # --- public actions -------------------------------------------
    def new_actionlist(self) -> None:
        if not self.confirm_proceed():
            return
        state = self._frame.controller.new_actionlist()
        self._frame._set_filename(ct.UNKNOWN)
        self._frame.description.SetValue(state.description)
        self._frame.show_description(False)
        self._frame.enable_actions(False)

    def open_actionlist(self) -> None:
        if not self.confirm_proceed():
            return
        selection = self._file_dialogs.open_actionlist(
            parent=self._frame,
            message=_("Choose an Action List File..."),
            default_dir=os.path.dirname(self._frame.filename),
            wildcard=ct.WILDCARD,
            style=getattr(wx, "FD_OPEN", 0),
        )
        if selection:
            self._open_path(selection.path)

    def save_current(self) -> bool:
        filename = self._frame.filename
        if filename == ct.UNKNOWN or self._frame.is_protected_actionlist(filename):
            return self.save_as()
        return self._save_path()

    def save_as(self) -> bool:
        filename = self._frame.filename
        if self._frame.is_protected_actionlist(filename) or not os.path.isfile(
            filename
        ):
            default_dir = ct.USER_ACTIONLISTS_PATH
        else:
            default_dir = os.path.dirname(filename)
        selection = self._file_dialogs.save_actionlist(
            parent=self._frame,
            message=_("Save Action List As..."),
            default_dir=default_dir,
            wildcard=ct.WILDCARD,
            style=getattr(wx, "FD_SAVE", 0),
        )
        if not selection:
            return False
        path = self._ensure_suffix(selection.path)
        if os.path.exists(path):
            overwrite = self._frame.show_question(
                f"{_('This file exists already.')} {_('Do you want to overwrite it?')}"
            )
            if overwrite == getattr(wx, "ID_NO", -1):
                return False
        return self._save_path(path)

    def export_actionlist_to_clipboard(self) -> None:
        if not self.confirm_proceed():
            return
        self._copy_text(ct.COMMAND["DROP"] % self._frame.filename)
        self._frame.show_info(
            " ".join(
                [
                    self._clipboard_messages.actionlist,
                    self._clipboard_messages.paste_hint,
                ]
            )
        )

    def export_recent_to_clipboard(self) -> None:
        if not self.confirm_proceed():
            return
        self._copy_text(ct.COMMAND["RECENT"])
        self._frame.show_info(
            " ".join(
                [self._clipboard_messages.recent, self._clipboard_messages.paste_hint]
            )
        )

    def export_inspector_to_clipboard(self) -> None:
        if not self.confirm_proceed():
            return
        self._copy_text(ct.COMMAND["INSPECTOR"])
        self._frame.show_info(
            " ".join(
                [
                    self._clipboard_messages.inspector,
                    self._clipboard_messages.paste_hint,
                ]
            )
        )

    def open_recent(self, index: int) -> None:
        if not self.confirm_proceed():
            return
        filename = self._file_history.GetHistoryFile(index)
        if filename:
            self._open_path(filename)

    # --- history --------------------------------------------------
    def get_file_history(self) -> list[str]:
        result: list[str] = []
        count = self._file_history.GetCount()
        for index in range(count):
            filename = self._file_history.GetHistoryFile(index)
            if filename and filename.strip():
                result.append(filename)
        return result

    def load_file_history(self, files: Sequence[str] | None) -> None:
        if not files:
            return
        for filename in reversed(list(files)):
            if filename and os.path.exists(filename):
                self._file_history.AddFileToHistory(filename)

    def _open_path(self, path: str) -> None:
        controller = self._frame.controller
        controller.begin_open()
        success = False
        try:
            self._frame._open(path)
            success = controller.state.filename != ct.UNKNOWN
        finally:
            controller.finish_open(success=success)

    def _save_path(self, path: str | None = None) -> bool:
        controller = self._frame.controller
        controller.begin_save()
        success = False
        try:
            self._frame._save(path)
            success = True
            return True
        finally:
            controller.finish_save(success=success)

    # --- helpers --------------------------------------------------
    @staticmethod
    def _prompt_style() -> int:
        return (
            getattr(wx, "YES_NO", 0)
            | getattr(wx, "CANCEL", 0)
            | getattr(wx, "ICON_EXCLAMATION", 0)
        )
