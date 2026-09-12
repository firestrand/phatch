from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image

wx = pytest.importorskip("wx")


def _display_available() -> bool:
    return sys.platform in {"darwin", "win32"} or bool(
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    )


pytestmark = pytest.mark.requires_display


@pytest.fixture
def wx_app():
    if not _display_available():
        pytest.skip("native wx tests require a display")
    app = wx.App(False)
    yield app
    for window in list(wx.GetTopLevelWindows()):
        window.Destroy()
    wx.Yield()
    app.Destroy()


@pytest.fixture(autouse=True)
def native_runtime(initialized_runtime, monkeypatch, wx_app) -> Iterator[None]:
    monkeypatch.setitem(__builtins__, "_", str)
    yield
    for window in list(wx.GetTopLevelWindows()):
        window.Destroy()
    wx.Yield()


@pytest.fixture
def jpeg_path(tmp_path: Path) -> Path:
    path = tmp_path / "inspector-fixture.jpg"
    exif = Image.Exif()
    exif[0x010E] = "native inspector fixture"
    Image.new("RGB", (96, 48), (12, 34, 56)).save(path, exif=exif)
    return path


def show_frame(frame) -> None:
    frame.Show()
    frame.Layout()
    wx.Yield()


class MetadataImage:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.values: dict[str, str] = {}
        self.deleted: list[str] = []
        self.written = False

    def readMetadata(self) -> None:
        return None

    def writeMetadata(self) -> None:
        self.written = True

    def __setitem__(self, key: str, value: str) -> None:
        self.values[key] = value

    def __delitem__(self, key: str) -> None:
        self.deleted.append(key)


class MetadataProvider:
    def __init__(self) -> None:
        self.images: list[MetadataImage] = []

    def Image(self, filename: str) -> MetadataImage:
        image = MetadataImage(filename)
        self.images.append(image)
        return image


@pytest.fixture
def metadata_provider(monkeypatch) -> MetadataProvider | None:
    from phatch.lib import imageTable
    from phatch.lib.pyWx import imageInspector

    if imageTable.pyexiv2 is not None:
        return None
    provider = MetadataProvider()
    monkeypatch.setattr(imageTable, "pyexiv2", provider)
    monkeypatch.setattr(imageInspector, "pyexiv2", provider)
    return provider
