"""Coordinator that handles wx file menu operations for the main frame."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

from phatch.core import ct

try:  # pragma: no cover - provided by gettext at runtime
    _  # type: ignore[name-defined]
except NameError:  # pragma: no cover - fallback for tests
    import builtins

    if '_' not in builtins.__dict__:
        builtins.__dict__['_'] = lambda value: value
    _ = builtins.__dict__['_']

try:  # pragma: no cover - optional at test time
    import wx  # type: ignore
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

    wx = _WxStub()  # type: ignore


@dataclass(frozen=True)
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
        frame: Any,
        file_history: Any,
        file_dialogs: Any,
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
            _('Save last changes to') + '\n"%s"?' % self._frame.filename,
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
            self._frame._open(selection.path)

    def save_current(self) -> bool:
        filename = self._frame.filename
        if filename == ct.UNKNOWN or self._frame.is_protected_actionlist(filename):
            return self.save_as()
        self._frame._save()
        return True

    def save_as(self) -> bool:
        filename = self._frame.filename
        if self._frame.is_protected_actionlist(filename) or not os.path.isfile(filename):
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
                "%s %s"
                % (_("This file exists already."), _("Do you want to overwrite it?"))
            )
            if overwrite == getattr(wx, "ID_NO", -1):
                return False
        self._frame._save(path)
        return True

    def export_actionlist_to_clipboard(self) -> None:
        if not self.confirm_proceed():
            return
        self._copy_text(ct.COMMAND["DROP"] % self._frame.filename)
        self._frame.show_info(
            " ".join([self._clipboard_messages.actionlist, self._clipboard_messages.paste_hint])
        )

    def export_recent_to_clipboard(self) -> None:
        if not self.confirm_proceed():
            return
        self._copy_text(ct.COMMAND["RECENT"])
        self._frame.show_info(
            " ".join([self._clipboard_messages.recent, self._clipboard_messages.paste_hint])
        )

    def export_inspector_to_clipboard(self) -> None:
        if not self.confirm_proceed():
            return
        self._copy_text(ct.COMMAND["INSPECTOR"])
        self._frame.show_info(
            " ".join([self._clipboard_messages.inspector, self._clipboard_messages.paste_hint])
        )

    def open_recent(self, index: int) -> None:
        if not self.confirm_proceed():
            return
        filename = self._file_history.GetHistoryFile(index)
        if filename:
            self._frame._open(filename)

    # --- history --------------------------------------------------
    def get_file_history(self) -> list[str]:
        result: list[str] = []
        count = self._file_history.GetCount()
        for index in range(count):
            filename = self._file_history.GetHistoryFile(index)
            if filename and filename.strip():
                result.append(filename)
        return result

    def load_file_history(self, files: Optional[Sequence[str]]) -> None:
        if not files:
            return
        for filename in reversed(list(files)):
            if filename and os.path.exists(filename):
                self._file_history.AddFileToHistory(filename)

    # --- helpers --------------------------------------------------
    @staticmethod
    def _prompt_style() -> int:
        return (
            getattr(wx, "YES_NO", 0)
            | getattr(wx, "CANCEL", 0)
            | getattr(wx, "ICON_EXCLAMATION", 0)
        )
