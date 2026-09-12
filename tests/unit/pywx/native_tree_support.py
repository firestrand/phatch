from __future__ import annotations

import builtins
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

import pytest

import phatch as phatch

try:
    import wx
except ImportError:
    pytest.skip("wxPython runtime unavailable", allow_module_level=True)

from phatch.lib.pyWx import treeEdit


class ActionForm(Protocol):
    label: str

    def dump(self) -> dict[str, str | dict[str, str]]: ...

    def get_field_string(self, label: str) -> str: ...


@dataclass(slots=True)
class WidgetSignals:
    dirty: list[bool] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class LocalText:
    _to_local = staticmethod(str)
    _to_english = staticmethod(str)


class NativeTree(treeEdit.TreeMixin, wx.TreeCtrl):
    def __init__(self, parent: wx.Window, signals: WidgetSignals) -> None:
        from phatch.core import api

        wx.TreeCtrl.__init__(self, parent, style=treeEdit.TR_DEFAULT_STYLE)
        treeEdit.TreeMixin.__init__(
            self,
            form_factory=api.ACTIONS,
            CtrlMixin=LocalText,
            show_error=signals.errors.append,
            set_dirty=signals.dirty.append,
        )

    def OnCompareItems(
        self, item1: wx.TreeItemId, item2: wx.TreeItemId
    ) -> Literal[-1, 0, 1]:
        return treeEdit.TreeMixin.OnCompareItems(self, item1, item2)


@dataclass(slots=True)
class NativeTreeHarness:
    app: wx.App
    frame: wx.Frame
    tree: NativeTree
    signals: WidgetSignals

    def action_items(self) -> list[wx.TreeItemId]:
        return self.tree.GetItemChildren(self.tree.GetRootItem())

    def labels(self) -> list[str]:
        return [self.tree.GetItemText(item) for item in self.action_items()]

    def fields(self, action_item: wx.TreeItemId) -> list[wx.TreeItemId]:
        return self.tree.GetItemChildren(action_item)

    def event(self, event_type: int, item: wx.TreeItemId) -> wx.TreeEvent:
        event = wx.TreeEvent(event_type, self.tree, item)
        event.SetEventObject(self.tree)
        return event


def _display_available() -> bool:
    return wx.App.IsDisplayAvailable()


requires_native_display = pytest.mark.skipif(
    not _display_available(), reason="wxPython runtime or graphical display unavailable"
)


@pytest.fixture
def wx_app(initialized_runtime) -> Iterator[wx.App]:
    app = wx.App(False)
    yield app
    app.Destroy()


@pytest.fixture
def native_tree(initialized_runtime, wx_app: wx.App) -> Iterator[NativeTreeHarness]:
    builtins.__dict__.setdefault("_", str)
    from phatch.other import pubsub

    signals = WidgetSignals()
    frame = wx.Frame(None, title="Native tree test", size=wx.Size(520, 420))
    tree = NativeTree(frame, signals)
    frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
    frame.GetSizer().Add(tree, 1, wx.EXPAND)
    frame.Show()
    wx_app.Yield()
    yield NativeTreeHarness(wx_app, frame, tree, signals)
    tree.close_popup()
    frame.Destroy()
    pubsub.Publisher().unsubAll()
    wx_app.Yield()


def save_and_load(path: Path, actions: list[ActionForm]) -> list[ActionForm]:
    from phatch.core import api

    api.save_actionlist(str(path), {"description": "native tree", "actions": actions})
    loaded = api.open_actionlist(str(path))
    assert loaded is not None
    data, warning = loaded
    assert warning == ""
    return data["actions"]
