from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import wx

from .native_popup_support import pump_events


@dataclass(frozen=True, slots=True)
class BrowserPaths:
    root: Path
    first: Path
    second: Path
    source: Path
    source_bytes: bytes


def seed_browser_paths(
    root: Path, bundled_images: Path, *, nested: bool = True
) -> BrowserPaths:
    source = bundled_images / "bee.png"
    source_bytes = source.read_bytes()
    image_root = root / "browser-images"
    second_root = image_root / "nested" if nested else image_root
    second_root.mkdir(parents=True)
    first = image_root / "alpha.png"
    second = second_root / "bravo.png"
    shutil.copyfile(source, first)
    shutil.copyfile(source, second)
    return BrowserPaths(image_root, first, second, source, source_bytes)


def attach_and_show(frame: wx.Frame, control: wx.Window) -> None:
    panel = control.GetParent()
    if panel.GetSizer() is None:
        panel.SetSizer(wx.BoxSizer(wx.VERTICAL))
    panel.GetSizer().Add(control, 1, wx.EXPAND)
    frame.Layout()
    pump_events()


def list_event(control: wx.ListCtrl, event_type: int, index: int) -> wx.ListEvent:
    event = wx.ListEvent(event_type, control.GetId())
    event.SetEventObject(control)
    event.SetIndex(index)
    event.SetItem(control.GetItem(index))
    return event


def tree_event(
    control: wx.TreeCtrl, event_type: int, item: wx.TreeItemId
) -> wx.TreeEvent:
    event = wx.TreeEvent(event_type, control, item)
    event.SetEventObject(control)
    return event


def child_items(tree: wx.TreeCtrl, parent: wx.TreeItemId) -> list[wx.TreeItemId]:
    items: list[wx.TreeItemId] = []
    item, cookie = tree.GetFirstChild(parent)
    while item.IsOk():
        items.append(item)
        item, cookie = tree.GetNextChild(parent, cookie)
    return items
