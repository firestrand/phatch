from __future__ import annotations

from importlib import import_module
from types import ModuleType

import pytest

load_notify = vars(import_module("tests.unit.lib.test_notify_decisions"))["load_notify"]


class FakeWidget:
    def __init__(self, *args) -> None:
        self.args = args
        self.background = None
        self.sizer = None

    def SetBackgroundColour(self, colour) -> None:
        self.background = colour

    def SetSizer(self, sizer) -> None:
        self.sizer = sizer


class FakeSizer:
    def __init__(self, orientation: int) -> None:
        self.orientation = orientation
        self.items: list[tuple] = []
        self.layouts = 0

    def Add(self, *args) -> None:
        self.items.append(args)

    def Layout(self) -> None:
        self.layouts += 1


class FakeToaster:
    def __init__(self, *args) -> None:
        self.args = args
        self.calls: list[tuple[str, int | tuple[int, int]]] = []
        self.panel = FakeWidget()
        self.added: list[FakeWidget] = []
        self.played = 0

    def SetPopupSize(self, value) -> None:
        self.calls.append(("size", value))

    def SetPopupPauseTime(self, value: int) -> None:
        self.calls.append(("pause", value))

    def SetPopupScrollSpeed(self, value: int) -> None:
        self.calls.append(("speed", value))

    def SetPopupPositionByInt(self, value: int) -> None:
        self.calls.append(("position", value))

    def GetToasterBoxWindow(self) -> FakeWidget:
        return self.panel

    def AddPanel(self, panel: FakeWidget) -> None:
        self.added.append(panel)

    def Play(self) -> None:
        self.played += 1


def test_toaster_backend_builds_popup_only_through_fake_outer_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[FakeToaster] = []
    bitmap_calls: list[tuple[int, int, tuple[int, int]]] = []
    wx = ModuleType("wx")
    vars(wx).update(
        ART_INFORMATION=1,
        ART_OTHER=2,
        WHITE="white",
        VERTICAL=4,
        HORIZONTAL=8,
        ALL=16,
        ALIGN_CENTER_VERTICAL=32,
        ALIGN_CENTER_HORIZONTAL=64,
        EXPAND=128,
        Panel=FakeWidget,
        StaticBitmap=FakeWidget,
        StaticText=FakeWidget,
        BoxSizer=FakeSizer,
    )

    class ArtProvider:
        @staticmethod
        def GetBitmap(art: int, client: int, size: tuple[int, int]) -> str:
            bitmap_calls.append((art, client, size))
            return "default-bitmap"

    class App:
        @staticmethod
        def GetTopWindow() -> str:
            return "top-window"

    vars(wx)["ArtProvider"] = ArtProvider
    vars(wx)["GetApp"] = App
    toasterbox = ModuleType("toasterbox")
    vars(toasterbox).update(TB_COMPLEX=1, DEFAULT_TB_STYLE=2, TB_ONTIME=3)

    def make_toaster(*args) -> FakeToaster:
        toaster = FakeToaster(*args)
        created.append(toaster)
        return toaster

    vars(toasterbox)["ToasterBox"] = make_toaster
    pywx = ModuleType("other.pyWx")
    vars(pywx)["toasterbox"] = toasterbox
    other = ModuleType("other")
    vars(other)["pyWx"] = pywx
    notify = load_notify(monkeypatch, {"wx": wx, "other": other})

    notify.send("Finished", "All images")
    notify.send("Saved", "One image", wxicon="provided-bitmap")

    assert bitmap_calls == [(1, 2, (48, 48))]
    assert len(created) == 2
    assert created[0].args == ("top-window", 1, 2, 3)
    assert created[0].calls == [
        ("size", (300, 80)),
        ("pause", 5000),
        ("speed", 8),
        ("position", 3),
    ]
    assert len(created[0].added) == 1
    assert created[0].played == created[1].played == 1
