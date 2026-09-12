from __future__ import annotations

from pathlib import Path

import pytest
import wx

from phatch.lib.pyWx import imageFileBrowser
from tests.unit.pywx.native_browser_support import (
    attach_and_show,
    list_event,
    seed_browser_paths,
)
from tests.unit.pywx.native_popup_support import panel, pump_events

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


class RecordingDialog(imageFileBrowser.Dialog):
    def __init__(self, parent: wx.Window, files: dict[str, str]) -> None:
        self.modal_results: list[int] = []
        super().__init__(parent, files, title="Native image browser")

    def EndModal(self, retCode: int) -> None:
        self.modal_results.append(retCode)


def test_truncate_preserves_short_text_and_suffixes_long_text() -> None:
    # Given / When / Then
    assert imageFileBrowser.truncate("short", 5) == "short"
    assert imageFileBrowser.truncate("alpha beta gamma", 12, "!") == "alpha beta!"


def test_image_list_uses_real_icons_and_caches_duplicate_file(
    native_frame, tmp_path: Path, test_input_dir: Path
) -> None:
    # Given
    paths = seed_browser_paths(tmp_path, test_input_dir, nested=False)
    files = {
        "Zulu": str(paths.first),
        "Alpha": str(paths.first),
        "Beta": str(paths.second),
    }

    # When
    control = imageFileBrowser.ListCtrl(panel(native_frame), files)
    attach_and_show(native_frame, control)

    # Then
    assert control.GetItemCount() == 3
    assert control.image_list.GetImageCount() == 2
    assert control._labels == ["Alpha", "Beta", "Zulu"]
    assert control.GetFileLabel(str(paths.first)) == "Zulu"
    assert control.GetFileLabel("missing.png") == "missing.png"
    assert control.GetItemFile(control.GetItem(1)) == str(paths.second)
    assert control.GetItemLabel(control.GetItem(1)) == "Beta"
    assert paths.source.read_bytes() == paths.source_bytes


def test_image_list_selection_updates_native_state(
    native_frame, tmp_path: Path, test_input_dir: Path
) -> None:
    # Given
    paths = seed_browser_paths(tmp_path, test_input_dir, nested=False)
    control = imageFileBrowser.ListCtrl(
        panel(native_frame), {"Alpha": str(paths.first), "Beta": str(paths.second)}
    )

    # When
    control.SelectItem(1)
    selected = control.GetFirstSelected()
    control.Deselect(1)
    pump_events()

    # Then
    assert selected == 1
    assert control.GetFirstSelected() == -1


def test_image_dialog_synchronizes_path_selection_and_visibility(
    native_frame, tmp_path: Path, test_input_dir: Path
) -> None:
    # Given
    paths = seed_browser_paths(tmp_path, test_input_dir, nested=False)
    files = {"Alpha": str(paths.first), "Beta": str(paths.second)}
    dialog = RecordingDialog(native_frame, files)

    # When
    dialog.image_list.Select(1)
    pump_events()
    selected_value = dialog.image_path.GetValue()
    dialog.OnItemSelected(
        list_event(dialog.image_list, wx.wxEVT_LIST_ITEM_SELECTED, 1)
    )
    dialog.SetValue(str(paths.first))
    dialog.ShowPath(False)
    dialog.OnActivated(
        list_event(dialog.image_list, wx.wxEVT_LIST_ITEM_ACTIVATED, 0)
    )

    # Then
    assert selected_value == "Beta"
    assert dialog.image_list.GetFirstSelected() == 0
    assert not dialog.image_path.IsShown()
    assert dialog.modal_results == [wx.ID_OK]
    dialog.Destroy()


def test_image_dialog_text_selects_library_value_and_clears_missing_selection(
    native_frame, tmp_path: Path, test_input_dir: Path
) -> None:
    # Given
    paths = seed_browser_paths(tmp_path, test_input_dir, nested=False)
    dialog = RecordingDialog(native_frame, {"Alpha": str(paths.first)})
    dialog.selection = 0

    # When
    event = wx.CommandEvent(wx.wxEVT_TEXT, dialog.image_path.path.GetId())
    event.SetString(str(paths.first))
    dialog.OnText(event)
    selected = dialog.image_list.GetFirstSelected()
    dialog.Select("not-in-library")
    dialog.Select("still-not-in-library")

    # Then
    assert selected == 0
    assert dialog.selection is None
    dialog.Destroy()
