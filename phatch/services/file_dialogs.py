"""Helpers for opening wx-based file dialogs in a testable way."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional


def _load_wx():  # pragma: no cover - exercised at runtime, stubbed in tests
    try:
        import wx  # type: ignore
    except ImportError:  # pragma: no cover - headless test environments
        class _WxStub:
            FD_OPEN = 0
            FD_SAVE = 0
            FD_OVERWRITE_PROMPT = 0
            ID_OK = True

        wx = _WxStub()  # type: ignore
    return wx


wx = _load_wx()


@dataclass(frozen=True)
class DialogSelection:
    path: str
    filter_index: Optional[int] = None


class FileDialogService:
    """Wraps wx file dialogs so the GUI can focus on control flow."""

    def __init__(self, dialog_cls: Callable[..., Any]) -> None:
        self._dialog_cls = dialog_cls
        self._ok_code = getattr(wx, 'ID_OK', None)
        self._overwrite_flag = getattr(wx, 'FD_OVERWRITE_PROMPT', getattr(wx, 'OVERWRITE_PROMPT', 0))

    def open_actionlist(self, parent: Any, *, message: str, default_dir: str,
                        wildcard: str, style: int) -> Optional[DialogSelection]:
        return self._show_dialog(parent, message=message, defaultDir=default_dir,
                                 wildcard=wildcard, style=style)

    def save_actionlist(self, parent: Any, *, message: str, default_dir: str,
                        wildcard: str, style: int, default_filename: Optional[str] = None) -> Optional[DialogSelection]:
        style |= self._overwrite_flag
        options: Mapping[str, Any] = {
            'message': message,
            'defaultDir': default_dir,
            'wildcard': wildcard,
            'style': style,
        }
        if default_filename:
            options = dict(options)
            options['defaultFile'] = default_filename
        return self._show_dialog(parent, **options)

    # --- internals -------------------------------------------------
    def _show_dialog(self, parent: Any, **options: Any) -> Optional[DialogSelection]:
        dlg = self._dialog_cls(parent, **options)
        try:
            result = dlg.ShowModal()
            if self._accepted(result):
                path = dlg.GetPath()
                filter_index = getattr(dlg, 'GetFilterIndex', lambda: None)()
                return DialogSelection(path=path, filter_index=filter_index)
            return None
        finally:
            if hasattr(dlg, 'Destroy'):
                dlg.Destroy()

    def _accepted(self, result: Any) -> bool:
        if self._ok_code is None:
            return bool(result)
        return result == self._ok_code
