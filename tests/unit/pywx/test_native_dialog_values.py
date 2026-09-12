from __future__ import annotations

from pathlib import Path

import pytest
import wx

from phatch.core import ct, pil

from .native_dialog_support import ModalResultMixin, command_event
from .native_dialog_support import dialog_runtime as dialog_runtime

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def settings_fixture(path: Path):
    return {
        "paths": [str(path)],
        "browse_source": 0,
        "extensions": list(pil.IMAGE_READ_EXTENSIONS[:2]),
        "overwrite_existing_images": False,
        "overwrite_existing_images_forced": True,
        "check_images_first": True,
        "recursive": True,
        "stop_for_errors": False,
        "always_show_status_dialog": False,
        "desktop": True,
        "repeat": 3,
    }


def test_error_dialog_configures_buttons_and_maps_all_results(dialog_runtime) -> None:
    # Given
    from phatch.pyWx import dialogs

    class TestableErrorDialog(ModalResultMixin, dialogs.ErrorDialog):
        pass

    parent, _counter, _root = dialog_runtime
    dialog = TestableErrorDialog(parent, "broken input", ignore=False)

    # When / Then
    assert not dialog.ignore.IsShown()
    assert dialog.GetDefaultItem() is dialog.skip
    dialog.on_skip(command_event(dialog.skip))
    assert dialog.modal_result == wx.ID_FORWARD
    dialog.on_abort(command_event(dialog.abort))
    assert dialog.modal_result == wx.ID_ABORT
    dialog.on_ignore(command_event(dialog.ignore))
    assert dialog.modal_result == wx.ID_IGNORE

    ignored = dialogs.ErrorDialog(parent, "recoverable", ignore=True)
    assert ignored.ignore.IsShown()


def test_execute_import_export_updates_actual_controls_and_settings(
    dialog_runtime, tmp_path: Path
) -> None:
    # Given
    from phatch.pyWx import dialogs

    parent, counter, _root = dialog_runtime
    dialog = dialogs.ExecuteDialog(parent)
    settings = settings_fixture(tmp_path / "images")

    # When
    dialog.import_settings(settings)
    dialog.export_settings(settings)

    # Then
    assert dialog.path.GetValue() == str(tmp_path / "images")
    assert dialog.get_selected_extensions() == list(pil.IMAGE_READ_EXTENSIONS[:2])
    assert settings["paths"] == [str(tmp_path / "images")]
    assert settings["overwrite_existing_images"] is True
    assert settings["check_images_first"] is True
    assert settings["repeat"] == 3
    assert counter.calls == 1


def test_execute_source_selection_filter_toggle_and_drop_state(
    dialog_runtime, monkeypatch
) -> None:
    # Given
    from phatch.pyWx import dialogs

    parent, _counter, _root = dialog_runtime
    monkeypatch.setattr(dialogs.clipboard, "get_text", lambda: "one\ntwo")
    dialog = dialogs.ExecuteDialog(parent)
    dialog.extensions.Set(list(pil.IMAGE_READ_EXTENSIONS))

    # When
    dialog.on_default(command_event(dialog.select))
    dialog.on_default(command_event(dialog.select))
    dialog.source.SetSelection(2)
    dialog.on_source(None)

    # Then
    assert dialog.select.GetLabel() == "&All Types"
    assert not dialog.browse.IsEnabled()
    assert dialog.path.GetValue() == ct.PATH_DELIMITER.join(("one", "two"))
    assert "All readable types" in dialog.wildcard()

    dialog.source.SetSelection(1)
    dialog.on_source(None)
    assert dialog.browse.IsEnabled()
    assert "File(s)" in dialog.browse.GetLabel()

    dropped = dialogs.ExecuteDialog(parent, drop=True)
    assert dropped.GetTitle() == "Drag & Drop"
    assert not dropped.source.IsShown()
    assert not dropped.path.IsShown()


def test_execute_browse_consumes_scripted_file_and_directory_results(
    dialog_runtime, tmp_path: Path, native_interaction, monkeypatch
) -> None:
    # Given
    from phatch.pyWx import dialogs

    class ScriptableFileDialog(wx.FileDialog):
        scripted_path = ""

        def SetPath(self, path: str) -> None:
            self.scripted_path = path

        def GetPaths(self) -> list[str]:
            return [self.scripted_path]

    parent, _counter, _root = dialog_runtime
    folder = tmp_path / "folder"
    folder.mkdir()
    image = tmp_path / "image.jpg"
    image.touch()
    native_interaction.expect_dialog(wx.DirDialog, wx.ID_OK, path=str(folder))
    monkeypatch.setattr(dialogs.wx, "FileDialog", ScriptableFileDialog)
    native_interaction.expect_dialog(
        ScriptableFileDialog, wx.ID_OK, path=str(image)
    )
    native_interaction.expect_dialog(ScriptableFileDialog, wx.ID_CANCEL)
    native_interaction.expect_dialog(wx.DirDialog, wx.ID_CANCEL)
    dialog = dialogs.ExecuteDialog(parent)
    dialog.extensions.Set(list(pil.IMAGE_READ_EXTENSIONS))

    # When / Then
    dialog.browse_folder()
    assert dialog.path.GetValue() == str(folder)
    dialog.browse_files()
    assert dialog.path.GetValue() == str(image)
    dialog.browse_files()
    assert dialog.path.GetValue() == str(image)
    dialog.browse_folder()
    assert dialog.path.GetValue() == str(image)
