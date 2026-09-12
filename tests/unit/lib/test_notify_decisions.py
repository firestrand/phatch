from __future__ import annotations

import builtins
from pathlib import Path
from types import ModuleType

import pytest

NOTIFY_PATH = Path(__file__).parents[3] / "phatch" / "lib" / "notify.py"
BACKEND_IMPORTS = {"pynotify", "gobject", "Growl", "wx", "other.pyWx.toasterbox"}


def load_notify(
    monkeypatch: pytest.MonkeyPatch, available: dict[str, ModuleType]
) -> ModuleType:
    original_import = builtins.__import__

    def import_backend(name, globals=None, locals=None, fromlist=(), level=0):
        if name in available:
            return available[name]
        if name == "other.pyWx.toasterbox" and "other" in available:
            return available["other"]
        if name in BACKEND_IMPORTS:
            raise ImportError(name)
        return original_import(name, globals, locals, fromlist, level)

    module = ModuleType("notify_under_test")
    with monkeypatch.context() as context:
        context.setattr(builtins, "__import__", import_backend)
        exec(
            compile(NOTIFY_PATH.read_text(encoding="utf-8"), NOTIFY_PATH, "exec"),
            module.__dict__,
        )
    return module


class FakeNotification:
    def __init__(self, title: str, message: str, icon: str) -> None:
        self.created_with = (title, message, icon)
        self.urgencies: list[int] = []
        self.timeouts: list[int] = []
        self.shown = 0

    def set_urgency(self, urgency: int) -> None:
        self.urgencies.append(urgency)

    def set_timeout(self, timeout: int) -> None:
        self.timeouts.append(timeout)

    def show(self) -> None:
        self.shown += 1


class FakeGrowlNotifier:
    def __init__(self) -> None:
        self.notifications: list[tuple[str, str, str]] = []

    def notify(self, app_name: str, title: str, message: str) -> None:
        self.notifications.append((app_name, title, message))


def test_pynotify_backend_initializes_and_dispatches_optional_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifications: list[FakeNotification] = []
    initialized: list[str] = []
    thread_initializations: list[bool] = []
    pynotify = ModuleType("pynotify")
    vars(pynotify)["URGENCY_CRITICAL"] = 3
    vars(pynotify)["init"] = initialized.append

    def notification(title: str, message: str, icon: str) -> FakeNotification:
        created = FakeNotification(title, message, icon)
        notifications.append(created)
        return created

    vars(pynotify)["Notification"] = notification
    gobject = ModuleType("gobject")
    vars(gobject)["threads_init"] = lambda: thread_initializations.append(True)
    notify = load_notify(monkeypatch, {"pynotify": pynotify, "gobject": gobject})

    notify.init("Phatch")
    notify.send("Finished", "All images", urgency="critical", timeout=2500)
    notify.send("Saved", "One image")

    assert thread_initializations == [True]
    assert initialized == ["Phatch"]
    assert notify.APP_NAME == "Phatch"
    assert [item.created_with for item in notifications] == [
        ("Finished", "All images", "gtk-dialog-info"),
        ("Saved", "One image", "gtk-dialog-info"),
    ]
    assert notifications[0].urgencies == [3]
    assert notifications[0].timeouts == [2500]
    assert notifications[0].shown == notifications[1].shown == 1


@pytest.mark.parametrize(
    ("icon", "expected_icon"),
    [(None, None), ("/tmp/phatch.png", "loaded:/tmp/phatch.png")],
)
def test_growl_backend_initializes_icon_and_dispatches_registered_name(
    monkeypatch: pytest.MonkeyPatch, icon: str | None, expected_icon: str | None
) -> None:
    constructor_calls: list[tuple[str, list[str], str | None]] = []
    notifier = FakeGrowlNotifier()
    growl_module = ModuleType("Growl")

    class Image:
        imageFromPath = staticmethod(lambda path: f"loaded:{path}")

    def make_notifier(
        app_name: str, classes: list[str], applicationIcon: str | None = None
    ) -> FakeGrowlNotifier:
        constructor_calls.append((app_name, classes, applicationIcon))
        return notifier

    vars(growl_module)["Image"] = Image
    vars(growl_module)["GrowlNotifier"] = make_notifier
    notify = load_notify(monkeypatch, {"Growl": growl_module})

    notify.init("Phatch", icon)
    notify.send("Finished", "All images")

    assert constructor_calls == [("Phatch", ["Phatch"], expected_icon)]
    assert notifier.notifications == [("Phatch", "Finished", "All images")]


def test_no_backend_registers_name_and_accepts_notification_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notify = load_notify(monkeypatch, {})

    notify.init("Headless")
    result = notify.send("Finished", "All images", urgency="low", timeout=1)

    assert notify.APP_NAME == "Headless"
    assert result is None
