from __future__ import annotations

import ctypes
from dataclasses import dataclass
from typing import NoReturn, Protocol


class ProcessIdentity(Protocol):
    pid: int


@dataclass(frozen=True, slots=True)
class VisibleWindow:
    handle: int
    title: str
    class_name: str
    owner: int
    style: int


def select_main_window(
    windows: tuple[VisibleWindow, ...], expected_title: str
) -> int | None:
    if not windows:
        return None
    matching = tuple(
        window
        for window in windows
        if window.title == expected_title
        and window.owner == 0
        and window.class_name.startswith("wxWindow")
        and window.style & 0x00CF0000 == 0x00CF0000
    )
    unexpected = tuple(window for window in windows if window not in matching)
    if unexpected or len(matching) != 1:
        details = "; ".join(
            f"title={window.title!r}, class={window.class_name!r}, "
            f"owner={window.owner}, style=0x{window.style:x}"
            for window in (unexpected or matching)
        )
        raise RuntimeError(f"unexpected GUI window for portable Phatch: {details}")
    return matching[0].handle


def _load_user32():
    loader = vars(ctypes)["WinDLL"]
    return loader("user32", use_last_error=True)


def _windows_callback_type():
    from ctypes import wintypes

    callback_factory = vars(ctypes)["WINFUNCTYPE"]
    return callback_factory(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _raise_windows_error() -> NoReturn:
    error_factory = vars(ctypes)["WinError"]
    get_last_error = vars(ctypes)["get_last_error"]
    raise error_factory(get_last_error())


def close_process_main_window(process: ProcessIdentity, expected_title: str) -> bool:
    from ctypes import wintypes

    user32 = _load_user32()
    callback_type = _windows_callback_type()
    user32.EnumWindows.argtypes = (callback_type, wintypes.LPARAM)
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = (
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    )
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = (wintypes.HWND,)
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetWindow.argtypes = (wintypes.HWND, wintypes.UINT)
    user32.GetWindow.restype = wintypes.HWND
    user32.GetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int)
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.PostMessageW.argtypes = (
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )
    user32.PostMessageW.restype = wintypes.BOOL
    windows: list[VisibleWindow] = []

    def inspect_window(window: int, parameter: int) -> bool:
        del parameter
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(window, ctypes.byref(process_id))
        if process_id.value == process.pid and user32.IsWindowVisible(window):
            title = ctypes.create_unicode_buffer(
                user32.GetWindowTextLengthW(window) + 1
            )
            user32.GetWindowTextW(window, title, len(title))
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(window, class_name, len(class_name))
            windows.append(
                VisibleWindow(
                    window,
                    title.value,
                    class_name.value,
                    user32.GetWindow(window, 4) or 0,
                    user32.GetWindowLongPtrW(window, -16),
                )
            )
        return True

    if not user32.EnumWindows(callback_type(inspect_window), 0):
        _raise_windows_error()
    main_window = select_main_window(tuple(windows), expected_title)
    if main_window is None:
        return False
    if not user32.PostMessageW(main_window, 0x0010, 0, 0):
        _raise_windows_error()
    return True
