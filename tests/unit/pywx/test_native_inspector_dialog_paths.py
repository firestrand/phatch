from __future__ import annotations

import runpy
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


def _editable_grid(jpeg_path: Path):
    from phatch.lib.pyWx import imageInspector

    frame = imageInspector.Frame(None, str(jpeg_path), size=(720, 520))
    show_frame(frame)
    grid = frame.GetGrid()
    assert isinstance(grid, imageInspector.GridTag)
    image = grid.image_table.images[0]
    image.info["Exif_Image_ImageDescription"] = "before"
    grid.image_table._update_keys(imageInspector.ALL, "")
    grid.RefreshAll()
    return frame, grid


def test_add_tag_modal_cancel_returns_empty_values(
    native_runtime, native_interaction
) -> None:
    from phatch.lib.pyWx import imageInspector

    dialog = imageInspector.AddTagDialog(None, [])
    native_interaction.expect_dialog(imageInspector.AddTagDialog, wx.ID_CANCEL)

    result = dialog.GetModal()

    assert result == (None, None)


def test_add_column_then_delete_row_updates_real_metadata(
    native_runtime,
    jpeg_path: Path,
    metadata_provider,
    native_interaction,
) -> None:
    from phatch.lib.pyWx import imageInspector

    _frame, grid = _editable_grid(jpeg_path)
    native_interaction.expect_dialog(
        imageInspector.AddTagDialog,
        wx.ID_ADD,
        ("Exif_Image_Artist", "Ada"),
    )
    grid.AddColumnRow(0)
    artist_row = grid.image_table.keys.index("Exif_Image_Artist")
    native_interaction.expect_dialog(wx.MessageDialog, wx.ID_YES)

    grid.DeleteRows(artist_row)

    assert "Exif_Image_Artist" not in grid.image_table.images[0].info
    if metadata_provider is not None:
        assert "Exif.Image.Artist" in metadata_provider.images[-1].deleted


def test_cancelled_edit_dialogs_preserve_metadata(
    native_runtime, jpeg_path: Path, native_interaction
) -> None:
    _frame, grid = _editable_grid(jpeg_path)
    row = grid.image_table.keys.index("Exif_Image_ImageDescription")
    native_interaction.expect_dialog(wx.MessageDialog, wx.ID_NO)
    native_interaction.expect_dialog(wx.TextEntryDialog, wx.ID_CANCEL)
    native_interaction.expect_dialog(wx.TextEntryDialog, wx.ID_CANCEL)

    grid.DeleteCell(row, 0)
    grid.RenameRowLabelValue(row)
    grid.ChangeRowValues(row)

    assert grid.image_table.images[0].info["Exif_Image_ImageDescription"] == ("before")


def test_delete_last_image_switches_to_empty_view(
    native_runtime, jpeg_path: Path
) -> None:
    frame, grid = _editable_grid(jpeg_path)

    grid.DeleteCols(0)

    assert grid.GetNumberCols() == 0
    assert frame.browser.empty.IsShown()


class GridEvent:
    def __init__(self, row: int, col: int) -> None:
        self._row = row
        self._col = col
        self.skipped = False

    def GetRow(self) -> int:
        return self._row

    def GetCol(self) -> int:
        return self._col

    def Skip(self) -> None:
        self.skipped = True


def test_grid_events_build_guarded_menus_and_dispatch_labels(
    native_runtime,
    jpeg_path: Path,
    metadata_provider,
    native_interaction,
    monkeypatch,
) -> None:
    from phatch.lib.pyWx import imageInspector

    _frame, grid = _editable_grid(jpeg_path)
    row = grid.image_table.keys.index("Exif_Image_ImageDescription")
    copied: list[str] = []
    opened: list[str] = []
    monkeypatch.setattr(imageInspector.clipboard, "copy_text", copied.append)
    monkeypatch.setattr(imageInspector.system, "start", opened.append)
    native_interaction.expect_popup()
    native_interaction.expect_popup()
    native_interaction.expect_popup()
    cell_event = GridEvent(row, 0)
    column_event = GridEvent(-1, 0)
    row_event = GridEvent(row, -1)

    grid.OnGridCellLeftClick(cell_event)
    grid.OnGridCellRightClicked(cell_event)
    grid.OnGridLabelRightClicked(column_event)
    grid.OnGridLabelRightClicked(row_event)
    grid.OnGridLabelLeftDclicked(column_event)
    grid.CopyCellValue(row, 0)
    grid.CopyRowLabel(row)

    assert cell_event.skipped
    assert column_event.skipped
    assert row_event.skipped
    assert opened == [str(jpeg_path)]
    assert copied == ["before", "<Exif_Image_ImageDescription>"]


def test_native_open_dialogs_add_selected_images(
    native_runtime, jpeg_path: Path, native_interaction
) -> None:
    _frame, grid = _editable_grid(jpeg_path)
    native_interaction.expect_dialog(wx.FileDialog, wx.ID_OK, path=str(jpeg_path))
    native_interaction.expect_dialog(wx.TextEntryDialog, wx.ID_OK, (str(jpeg_path),))

    grid.OnOpen(wx.CommandEvent())
    grid.OnOpenUrl(wx.CommandEvent())

    assert grid.GetNumberCols() == 3
    assert all(image.filename == str(jpeg_path) for image in grid.image_table.images)


def test_browser_messages_and_frame_titles_follow_native_state(
    native_runtime, jpeg_path: Path, monkeypatch
) -> None:
    from phatch.lib.pyWx import imageInspector

    empty_frame = imageInspector.Frame(None, size=(720, 520))
    show_frame(empty_frame)
    assert "drag" in empty_frame.browser.GetPaintMessage()
    frame, grid = _editable_grid(jpeg_path)
    frame.SetTitleFilename("")
    assert frame.GetTitle() == imageInspector.TITLE
    frame.browser.tag.Append("Exif")
    frame.browser.tag.SetSelection(frame.browser.tag.FindString("Exif"))
    monkeypatch.setattr(imageInspector, "pyexiv2", None)
    assert "pyexiv2" in frame.browser.GetPaintMessage()
    monkeypatch.setattr(imageInspector, "pyexiv2", True)
    grid.image_table.key_amount_tag = 1
    assert "broaden" in frame.browser.GetPaintMessage()
    grid.image_table.key_amount_tag = 0
    assert "no exif" in frame.browser.GetPaintMessage().lower()


def test_generated_dialog_handlers_and_demo_construct_native_controls(
    native_runtime, native_interaction, wx_app, monkeypatch, capsys
) -> None:
    from phatch.lib.pyWx import dialogsInspector

    dialog = dialogsInspector.AddTagDialog(None)
    tag_event = wx.CommandEvent(wx.wxEVT_TEXT, dialog.tag.GetId())
    add_event = wx.CommandEvent(wx.wxEVT_BUTTON, dialog.add.GetId())
    native_interaction.expect_main_loop()
    monkeypatch.setattr(wx, "PySimpleApp", lambda _redirect=0: wx_app)

    dialog.OnTagText(tag_event)
    dialog.OnAdd(add_event)
    runpy.run_path(dialogsInspector.__file__, run_name="__main__")

    demo = wx_app.GetTopWindow()
    assert isinstance(demo, wx.Dialog)
    assert len(demo.GetChildren()) == 8
    assert [control.GetValue() for control in (demo.tag, demo.value)] == [
        "Exif_Photo_UserComment",
        "",
    ]
    assert tag_event.GetSkipped()
    assert add_event.GetSkipped()
    assert "OnTagText" in capsys.readouterr().out
