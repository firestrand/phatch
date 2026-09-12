from __future__ import annotations

from collections.abc import Callable
from ctypes import wintypes

import pytest

import scripts.windows_window_probe as windows_window_probe


class FakeFunction:
    def __init__(self, implementation: Callable[..., int]) -> None:
        self.implementation = implementation
        self.argtypes = None
        self.restype = None

    def __call__(self, *arguments) -> int:
        return self.implementation(*arguments)


class FakeUser32:
    def __init__(self, windows: tuple[windows_window_probe.VisibleWindow, ...]):
        self.windows = {window.handle: window for window in windows}
        self.closed: list[int] = []
        self.post_attempts: list[int] = []
        self.enum_result = 1
        self.post_result = 1
        self.process_id = 73
        self.visible = 1
        self.EnumWindows = FakeFunction(self._enum_windows)
        self.GetWindowThreadProcessId = FakeFunction(self._process_id)
        self.IsWindowVisible = FakeFunction(lambda window: self.visible)
        self.GetWindowTextLengthW = FakeFunction(
            lambda window: len(self.windows[window].title)
        )
        self.GetWindowTextW = FakeFunction(self._window_text)
        self.GetClassNameW = FakeFunction(self._class_name)
        self.GetWindow = FakeFunction(
            lambda window, command: self.windows[window].owner
        )
        self.GetWindowLongPtrW = FakeFunction(
            lambda window, index: self.windows[window].style
        )
        self.PostMessageW = FakeFunction(self._post_message)

    def _enum_windows(self, callback, parameter) -> int:
        for handle in self.windows:
            callback(handle, parameter)
        return self.enum_result

    def _process_id(self, window, output) -> int:
        del window
        output._obj.value = self.process_id
        return 1

    def _window_text(self, window, output, size) -> int:
        del size
        output.value = self.windows[window].title
        return len(output.value)

    def _class_name(self, window, output, size) -> int:
        del size
        output.value = self.windows[window].class_name
        return len(output.value)

    def _post_message(self, window, message, first, second) -> int:
        del message, first, second
        self.post_attempts.append(window)
        if self.post_result:
            self.closed.append(window)
        return self.post_result


class Process:
    pid = 73


class ExpectedWindowsError(RuntimeError):
    pass


def _install_ctypes_namespace(
    monkeypatch: pytest.MonkeyPatch,
    user32: FakeUser32,
    error: ExpectedWindowsError,
) -> tuple[list[tuple[str, bool]], list[tuple[object, ...]]]:
    loader_calls: list[tuple[str, bool]] = []
    callback_signatures: list[tuple[object, ...]] = []

    def load_library(name: str, *, use_last_error: bool):
        loader_calls.append((name, use_last_error))
        return user32

    def callback_factory(*signature):
        callback_signatures.append(signature)
        return lambda function: function

    monkeypatch.setitem(vars(windows_window_probe.ctypes), "WinDLL", load_library)
    monkeypatch.setitem(
        vars(windows_window_probe.ctypes), "WINFUNCTYPE", callback_factory
    )
    monkeypatch.setitem(
        vars(windows_window_probe.ctypes), "get_last_error", lambda: 1234
    )
    monkeypatch.setitem(
        vars(windows_window_probe.ctypes),
        "WinError",
        lambda code: error if code == 1234 else AssertionError(code),
    )
    return loader_calls, callback_signatures


def _inspect(
    monkeypatch: pytest.MonkeyPatch,
    windows: tuple[windows_window_probe.VisibleWindow, ...],
) -> tuple[bool, FakeUser32]:
    user32 = FakeUser32(windows)
    monkeypatch.setattr(windows_window_probe, "_load_user32", lambda: user32)
    monkeypatch.setattr(
        windows_window_probe,
        "_windows_callback_type",
        lambda: lambda function: function,
    )
    result = windows_window_probe.close_process_main_window(
        Process(), "actions - Phatch"
    )
    return result, user32


def test_expected_main_frame_alone_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    main = windows_window_probe.VisibleWindow(
        1, "actions - Phatch", "wxWindowNR", 0, 0x10CF0000
    )

    found, user32 = _inspect(monkeypatch, (main,))

    assert found is True
    assert user32.closed == [1]
    assert user32.EnumWindows.argtypes is not None
    assert user32.GetWindowLongPtrW.restype is windows_window_probe.ctypes.c_ssize_t


@pytest.mark.parametrize(
    "windows",
    [
        (windows_window_probe.VisibleWindow(2, "Phatch error", "#32770", 0, 0),),
        (
            windows_window_probe.VisibleWindow(
                1, "actions - Phatch", "wxWindowNR", 0, 0x10CF0000
            ),
            windows_window_probe.VisibleWindow(
                2, "Phatch error", "wxDialog", 1, 0x80C80000
            ),
        ),
    ],
)
def test_dialog_only_and_mixed_windows_fail_before_any_close(
    monkeypatch: pytest.MonkeyPatch,
    windows: tuple[windows_window_probe.VisibleWindow, ...],
) -> None:
    user32 = FakeUser32(windows)
    monkeypatch.setattr(windows_window_probe, "_load_user32", lambda: user32)
    monkeypatch.setattr(
        windows_window_probe,
        "_windows_callback_type",
        lambda: lambda function: function,
    )

    with pytest.raises(RuntimeError, match="unexpected GUI window"):
        windows_window_probe.close_process_main_window(Process(), "actions - Phatch")

    assert user32.closed == []


def test_windows_ctypes_factories_use_stdcall_and_last_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user32 = FakeUser32(())
    error = ExpectedWindowsError("win32 failure 1234")
    loader_calls, callback_signatures = _install_ctypes_namespace(
        monkeypatch, user32, error
    )

    loaded = windows_window_probe._load_user32()
    callback_type = windows_window_probe._windows_callback_type()
    with pytest.raises(ExpectedWindowsError) as error_info:
        windows_window_probe._raise_windows_error()

    assert loaded is user32
    assert loader_calls == [("user32", True)]
    assert callback_signatures == [(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)]
    assert callback_type(lambda: None)() is None
    assert error_info.value is error


def test_enum_failure_raises_last_error_without_closing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user32 = FakeUser32(())
    user32.enum_result = 0
    error = ExpectedWindowsError("enum failed")
    _install_ctypes_namespace(monkeypatch, user32, error)

    with pytest.raises(ExpectedWindowsError) as error_info:
        windows_window_probe.close_process_main_window(Process(), "actions - Phatch")

    assert error_info.value is error
    assert user32.post_attempts == []
    assert user32.closed == []


def test_post_failure_raises_last_error_without_reporting_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = windows_window_probe.VisibleWindow(
        1, "actions - Phatch", "wxWindowNR", 0, 0x10CF0000
    )
    user32 = FakeUser32((main,))
    user32.post_result = 0
    error = ExpectedWindowsError("post failed")
    _install_ctypes_namespace(monkeypatch, user32, error)

    with pytest.raises(ExpectedWindowsError) as error_info:
        windows_window_probe.close_process_main_window(Process(), "actions - Phatch")

    assert error_info.value is error
    assert user32.post_attempts == [1]
    assert user32.closed == []


@pytest.mark.parametrize(("process_id", "visible"), [(74, 1), (73, 0)])
def test_nonmatching_or_hidden_windows_are_not_main_frame(
    monkeypatch: pytest.MonkeyPatch, process_id: int, visible: int
) -> None:
    main = windows_window_probe.VisibleWindow(
        1, "actions - Phatch", "wxWindowNR", 0, 0x10CF0000
    )
    user32 = FakeUser32((main,))
    user32.process_id = process_id
    user32.visible = visible
    error = ExpectedWindowsError("unused")
    _install_ctypes_namespace(monkeypatch, user32, error)

    found = windows_window_probe.close_process_main_window(
        Process(), "actions - Phatch"
    )

    assert found is False
    assert user32.post_attempts == []
