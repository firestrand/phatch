from __future__ import annotations

import builtins
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pytest
import wx

from phatch.lib import listData


@dataclass(slots=True)
class SaveCounter:
    calls: int = 0

    def __call__(self) -> None:
        self.calls += 1


class ActionFixture:
    label = "Resize"
    __doc__ = "Resize an image"
    tags: ClassVar[tuple[str, ...]] = ("default", "geometry")
    tags_hidden: ClassVar[tuple[str, ...]] = ("dimensions",)
    icon = "ART_INFORMATION"
    __module__ = "phatch.actions.resize"


class ModalResultMixin:
    modal_result: int | None = None

    def EndModal(self, retCode: int) -> None:
        self.modal_result = retCode


@pytest.fixture
def dialog_runtime(initialized_runtime, native_frame, wx_app, monkeypatch):
    counter = SaveCounter()
    monkeypatch.setattr(builtins, "_", str, raising=False)
    monkeypatch.setattr(wx_app, "_saveSettings", counter, raising=False)
    monkeypatch.setattr(wx_app, "report", [], raising=False)
    wx_app.SetTopWindow(native_frame)
    return native_frame, counter, initialized_runtime.root


def image_tree_data(path: Path):
    rows = [
        {
            "path": str(path),
            "filename": path.name,
            "width": 32,
            "height": 16,
        }
    ]
    return listData.files_data_dict(rows), listData.DataDict


def command_event(control: wx.Window) -> wx.CommandEvent:
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, control.GetId())
    event.SetEventObject(control)
    return event
