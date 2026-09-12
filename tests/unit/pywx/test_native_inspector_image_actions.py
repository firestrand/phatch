from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.unit.pywx.native_inspector_support import jpeg_path as jpeg_path
from tests.unit.pywx.native_inspector_support import (
    metadata_provider as metadata_provider,
)
from tests.unit.pywx.native_inspector_support import native_runtime as native_runtime
from tests.unit.pywx.native_inspector_support import show_frame, wx
from tests.unit.pywx.native_inspector_support import wx_app as wx_app

pytestmark = pytest.mark.requires_display

EDITABLE_KEY = "Exif_Image_ImageDescription"


def _editable_frame(jpeg_path: Path):
    from phatch.lib.pyWx import imageInspector

    frame = imageInspector.Frame(None, str(jpeg_path), size=(720, 520))
    show_frame(frame)
    grid = frame.GetGrid()
    assert isinstance(grid, imageInspector.GridTag)
    image = grid.image_table.images[0]
    image.info[EDITABLE_KEY] = "before"
    grid.image_table._update_keys(imageInspector.ALL, "")
    grid.RefreshAll()
    return frame, grid


def test_add_tag_dialog_validates_native_input_states(native_runtime) -> None:
    from phatch.lib.pyWx import imageInspector

    # Given
    dialog = imageInspector.AddTagDialog(None, [EDITABLE_KEY])
    dialog.Show()
    wx.Yield()

    # When
    dialog.tag.SetValue("invalid")
    wx.Yield()

    # Then
    assert not dialog.add.IsEnabled()
    assert dialog.warning.GetLabel()

    # When
    dialog.tag.SetValue(EDITABLE_KEY)
    wx.Yield()

    # Then
    assert not dialog.add.IsEnabled()
    assert "exists" in dialog.warning.GetLabel().lower()

    # When
    dialog.tag.SetValue("Exif_Image_Artist")
    wx.Yield()

    # Then
    assert dialog.add.IsEnabled()
    assert dialog.warning.GetLabel() == ""


def test_add_tag_dialog_returns_values_from_real_modal(
    native_runtime, native_interaction
) -> None:
    from phatch.lib.pyWx import imageInspector

    # Given
    dialog = imageInspector.AddTagDialog(None, [])
    native_interaction.expect_dialog(
        imageInspector.AddTagDialog,
        wx.ID_ADD,
        ("Exif_Image_Artist", "Ada"),
    )

    # When
    result = dialog.GetModal()

    # Then
    assert result == ("Exif_Image_Artist", "Ada")


def test_grid_edit_writes_metadata_and_updates_visible_value(
    native_runtime, jpeg_path: Path, metadata_provider
) -> None:
    # Given
    _frame, grid = _editable_frame(jpeg_path)
    row = grid.image_table.keys.index(EDITABLE_KEY)

    # When
    grid.table.SetValue(row, 0, "after")
    grid.OnGridCellChange(wx.CommandEvent())
    wx.Yield()

    # Then
    assert grid.GetCellValue(row, 0) == "after"
    assert grid.table.log == ""
    if metadata_provider is not None:
        written = metadata_provider.images[-1]
        assert written.filename == str(jpeg_path)
        assert written.values["Exif.Image.ImageDescription"] == "after"
        assert written.written


def test_delete_cell_uses_confirmation_and_removes_metadata(
    native_runtime, jpeg_path: Path, metadata_provider, native_interaction
) -> None:
    # Given
    _frame, grid = _editable_frame(jpeg_path)
    row = grid.image_table.keys.index(EDITABLE_KEY)
    native_interaction.expect_dialog(wx.MessageDialog, wx.ID_YES)

    # When
    grid.DeleteCell(row, 0)
    wx.Yield()

    # Then
    assert EDITABLE_KEY not in grid.image_table.images[0].info
    if metadata_provider is not None:
        assert "Exif.Image.ImageDescription" in metadata_provider.images[-1].deleted


def test_add_rename_and_change_tag_values_through_native_dialogs(
    native_runtime, jpeg_path: Path, metadata_provider, native_interaction
) -> None:
    from phatch.lib.pyWx import imageInspector

    # Given
    _frame, grid = _editable_frame(jpeg_path)
    native_interaction.expect_dialog(
        imageInspector.AddTagDialog,
        wx.ID_ADD,
        ("Exif_Image_Artist", "Ada"),
    )

    # When
    grid.AddRow()
    artist_row = grid.image_table.keys.index("Exif_Image_Artist")
    native_interaction.expect_dialog(
        wx.TextEntryDialog, wx.ID_OK, ("Exif_Image_Copyright",)
    )
    grid.RenameRowLabelValue(artist_row)
    exif_keys = [
        key for key in grid.image_table.keys if key.startswith("Exif_Image_")
    ]
    assert "Exif_Image_Copyright" in exif_keys, exif_keys
    copyright_row = grid.image_table.keys.index("Exif_Image_Copyright")
    native_interaction.expect_dialog(wx.TextEntryDialog, wx.ID_OK, ("Copyright 2026",))
    grid.ChangeRowValues(copyright_row)
    wx.Yield()

    # Then
    image_info = grid.image_table.images[0].info
    assert "Exif_Image_Artist" not in image_info
    assert image_info["Exif_Image_Copyright"] == "Copyright 2026"
    assert grid.GetNumberRows() > 0
    assert imageInspector.ALL == "All"
    if metadata_provider is not None:
        assert any(
            image.values.get("Exif.Image.Artist") == "Ada"
            for image in metadata_provider.images
        )
        assert any(
            "Exif.Image.Artist" in image.deleted
            for image in metadata_provider.images
        )
        assert metadata_provider.images[-1].values["Exif.Image.Copyright"] == (
            "Copyright 2026"
        )


def test_open_images_reports_invalid_path_and_keeps_valid_image(
    native_runtime, jpeg_path: Path, native_interaction
) -> None:
    from phatch.lib.pyWx import imageInspector

    # Given
    frame = imageInspector.Frame(None, size=(720, 520))
    show_frame(frame)
    missing = jpeg_path.with_name("missing.jpg")
    native_interaction.expect_dialog(wx.MessageDialog, wx.ID_OK)

    # When
    frame.OpenImages([str(jpeg_path), str(missing)])
    wx.Yield()

    # Then
    grid = frame.GetGrid()
    assert isinstance(grid, imageInspector.GridTag)
    assert grid.GetNumberCols() == 1
    assert grid.image_table.images[0].filename == str(jpeg_path)
    assert not wx.IsBusy()


def test_activate_refreshes_modified_pillow_file(
    native_runtime, jpeg_path: Path
) -> None:
    from phatch.lib.pyWx import imageInspector

    # Given
    frame = imageInspector.Frame(None, str(jpeg_path), size=(720, 520))
    show_frame(frame)
    grid = frame.GetGrid()
    assert isinstance(grid, imageInspector.GridTag)
    old_time = grid.image_table.images[0].time
    os.utime(jpeg_path, (old_time + 10, old_time + 10))

    # When
    event = wx.ActivateEvent(wx.wxEVT_ACTIVATE, True, frame.GetId())
    frame.OnActivate(event)
    wx.Yield()

    # Then
    assert grid.image_table.images[0].time > old_time
