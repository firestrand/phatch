from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from tests.unit.pywx.native_inspector_support import jpeg_path as jpeg_path
from tests.unit.pywx.native_inspector_support import native_runtime as native_runtime
from tests.unit.pywx.native_inspector_support import show_frame, wx
from tests.unit.pywx.native_inspector_support import wx_app as wx_app

pytestmark = pytest.mark.requires_display

OLD_KEY = "Exif_Image_ImageDescription"
NEW_KEY = "Exif_Image_Copyright"


class RecordingMetadataImage:
    def __init__(self, filename: str, provider: RecordingMetadataProvider) -> None:
        self.filename = filename
        self.provider = provider

    def readMetadata(self) -> None:
        self.provider.trace.append(("read", self.filename, None))

    def writeMetadata(self) -> None:
        self.provider.write_count += 1
        self.provider.trace.append(("write", self.filename, None))
        if self.provider.write_count == self.provider.fail_write:
            raise OSError("injected metadata write failure")

    def __setitem__(self, key: str, value: str) -> None:
        self.provider.trace.append(("set", self.filename, f"{key}={value}"))

    def __delitem__(self, key: str) -> None:
        self.provider.trace.append(("delete", self.filename, key))


class RecordingMetadataProvider:
    def __init__(self, fail_write: int | None = None) -> None:
        self.fail_write = fail_write
        self.write_count = 0
        self.trace: list[tuple[str, str, str | None]] = []

    def Image(self, filename: str) -> RecordingMetadataImage:
        return RecordingMetadataImage(filename, self)


def _rename_frame(paths: list[Path], provider, monkeypatch):
    from phatch.lib import imageTable
    from phatch.lib.pyWx import imageInspector

    monkeypatch.setattr(imageTable, "pyexiv2", provider)
    monkeypatch.setattr(imageInspector, "pyexiv2", provider)
    frame = imageInspector.Frame(None, size=(720, 520))
    show_frame(frame)
    grid = frame.GetGrid()
    assert isinstance(grid, imageInspector.GridTag)
    grid.OpenImages([str(path) for path in paths])
    for index, image in enumerate(grid.image_table.images):
        image.info[OLD_KEY] = f"before-{index}"
    grid.image_table._update_keys(imageInspector.ALL, "")
    grid.RefreshAll()
    return grid


def test_invalid_gui_rename_reports_error_without_mutating_metadata(
    native_runtime, jpeg_path: Path, native_interaction, monkeypatch
) -> None:
    provider = RecordingMetadataProvider()
    grid = _rename_frame([jpeg_path], provider, monkeypatch)
    row = grid.image_table.keys.index(OLD_KEY)
    original_keys = list(grid.image_table.keys)
    original_info = dict(grid.image_table.images[0].info)
    original_key_amount = grid.image_table.key_amount
    native_interaction.expect_dialog(wx.TextEntryDialog, wx.ID_OK, ("plain",))
    native_interaction.expect_dialog(wx.MessageDialog, wx.ID_OK)

    grid.RenameRowLabelValue(row)

    assert grid.image_table.keys == original_keys
    assert grid.image_table.images[0].info == original_info
    assert grid.image_table.key_amount == original_key_amount
    assert provider.trace == []


def test_valid_gui_rename_updates_every_image_and_backend_trace(
    native_runtime,
    jpeg_path: Path,
    tmp_path: Path,
    native_interaction,
    monkeypatch,
) -> None:
    second_path = tmp_path / "second.jpg"
    Image.new("RGB", (48, 32), (4, 5, 6)).save(second_path)
    provider = RecordingMetadataProvider()
    grid = _rename_frame([jpeg_path, second_path], provider, monkeypatch)
    row = grid.image_table.keys.index(OLD_KEY)
    native_interaction.expect_dialog(wx.TextEntryDialog, wx.ID_OK, (NEW_KEY,))

    grid.RenameRowLabelValue(row)

    assert all(OLD_KEY not in image.info for image in grid.image_table.images)
    assert [image.info[NEW_KEY] for image in grid.image_table.images] == [
        "before-0",
        "before-1",
    ]
    assert grid.image_table.keys.count(NEW_KEY) == 1
    assert OLD_KEY not in grid.image_table.keys
    assert grid.image_table.key_amount == len(grid.image_table.keys)
    assert provider.trace == [
        ("read", str(jpeg_path), None),
        ("set", str(jpeg_path), "Exif.Image.Copyright=before-0"),
        ("delete", str(jpeg_path), "Exif.Image.ImageDescription"),
        ("write", str(jpeg_path), None),
        ("read", str(second_path), None),
        ("set", str(second_path), "Exif.Image.Copyright=before-1"),
        ("delete", str(second_path), "Exif.Image.ImageDescription"),
        ("write", str(second_path), None),
    ]


def test_second_rename_write_failure_preserves_explicit_partial_state(
    native_runtime,
    jpeg_path: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    second_path = tmp_path / "second.jpg"
    Image.new("RGB", (48, 32), (7, 8, 9)).save(second_path)
    provider = RecordingMetadataProvider(fail_write=2)
    grid = _rename_frame([jpeg_path, second_path], provider, monkeypatch)
    row = grid.image_table.keys.index(OLD_KEY)

    log = grid.table.SetRowLabelValue(row, NEW_KEY)

    first, second = grid.image_table.images
    assert "injected metadata write failure" in log
    assert first.info[NEW_KEY] == "before-0"
    assert OLD_KEY not in first.info
    assert second.info[OLD_KEY] == "before-1"
    assert NEW_KEY not in second.info
    assert OLD_KEY in grid.image_table.keys
    assert NEW_KEY in grid.image_table.keys
    assert grid.image_table.key_amount == len(grid.image_table.keys)
    assert OLD_KEY in log
    assert provider.trace == [
        ("read", str(jpeg_path), None),
        ("set", str(jpeg_path), "Exif.Image.Copyright=before-0"),
        ("delete", str(jpeg_path), "Exif.Image.ImageDescription"),
        ("write", str(jpeg_path), None),
        ("read", str(second_path), None),
        ("set", str(second_path), "Exif.Image.Copyright=before-1"),
        ("delete", str(second_path), "Exif.Image.ImageDescription"),
        ("write", str(second_path), None),
    ]
