from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from phatch.core import api, ct
from phatch.lib.pyWx import imageFileBrowser
from phatch.pyWx import dialogs, gui
from phatch.services.action_list import ActionListService

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


def test_library_menu_cancel_keeps_native_editor_empty(
    native_frame_harness, native_interaction
) -> None:
    # Given: an empty editor and a scripted cancellation of the real library dialog
    frame = native_frame_harness.frame
    native_interaction.expect_dialog(imageFileBrowser.Dialog, wx.ID_CANCEL)

    # When: the library menu is invoked
    frame.on_menu_file_open_library(None)

    # Then: the dialog is retained but hidden and no action list is loaded
    assert frame.dlg_library is not None
    assert not frame.dlg_library.IsShown()
    assert frame.IsEmpty()


def test_library_menu_reuses_dialog_and_opens_selected_action_list(
    native_frame_harness,
    native_interaction,
    test_input_dir,
    tmp_path: Path,
) -> None:
    # Given: a materialized native library dialog with Polaroid selected
    frame = native_frame_harness.frame
    preview = tmp_path / "Native.png"
    shutil.copy(next(test_input_dir.glob("*.png")), preview)
    selected = tmp_path / "Native.phatch"
    ActionListService().save(
        str(selected), "library selection", [api.ACTIONS["Border"]()]
    )
    frame.library_files_dictionary = {"Native": str(preview)}
    native_interaction.expect_dialog(imageFileBrowser.Dialog, wx.ID_CANCEL)
    frame.on_menu_file_open_library(None)
    frame.dlg_library.image_path.SetValue(str(preview))
    native_interaction.expect_dialog(imageFileBrowser.Dialog, wx.ID_OK)

    # When: the library menu is accepted on its second use
    frame.on_menu_file_open_library(None)

    # Then: the protected action list populates the real tree without recent history
    assert not frame.IsEmpty()
    assert frame.filename == str(selected)
    assert frame.filehistory.GetCount() == 1


def test_library_menu_rejection_does_not_open_dialog(
    native_frame_harness, monkeypatch
) -> None:
    # Given: the file coordinator rejects replacing dirty state
    frame = native_frame_harness.frame
    monkeypatch.setattr(frame.file_menu, "confirm_proceed", lambda: False)

    # When: the library menu is requested
    frame.on_menu_file_open_library(None)

    # Then: no native library dialog is created
    assert frame.dlg_library is None


def test_add_action_cancel_preserves_empty_native_tree(
    native_frame_harness, native_interaction
) -> None:
    # Given: an empty editor and a scripted cancellation of the real action dialog
    frame = native_frame_harness.frame
    native_interaction.expect_dialog(dialogs.ActionDialog, wx.ID_CANCEL)

    # When: Add is invoked
    frame.on_menu_edit_add(None)

    # Then: the dialog remains reusable and the native tree stays empty
    assert frame.dialog_actions is not None
    assert not frame.dialog_actions.IsShown()
    assert frame.IsEmpty()


def test_add_action_accepts_native_dialog_selection(
    native_frame_harness, native_interaction
) -> None:
    # Given: a real action dialog whose first available action is selected
    frame = native_frame_harness.frame
    native_interaction.expect_dialog(dialogs.ActionDialog, wx.ID_CANCEL)
    frame.on_menu_edit_add(None)
    frame.dialog_actions.GetListBox().SetSelection(0)
    expected_label = frame.dialog_actions.GetStringSelection()
    native_interaction.expect_dialog(dialogs.ActionDialog, wx.ID_OK)

    # When: the reusable dialog is accepted
    frame.on_menu_edit_add(None)

    # Then: the selected production action appears in the native tree
    assert [action.label for action in frame.controller.export_actions()] == [
        expected_label
    ]
    assert frame.controller.state.dirty


def test_remove_without_selection_preserves_native_action(
    native_frame_harness,
) -> None:
    # Given: a real action tree whose selection has been cleared
    frame = native_frame_harness.frame
    frame.tree.Unselect()

    # When: Remove is invoked
    frame.on_menu_edit_remove(None)

    # Then: no state transition occurs
    assert frame.IsEmpty()


def test_move_down_reorders_native_actions(native_frame_harness) -> None:
    # Given: two actions with the first selected
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    frame.controller.add_action_by_label_to_last("Save")
    first = frame.tree.GetFirstChild(frame.tree.GetRootItem())[0]
    frame.tree.SelectItem(first)

    # When: Move Down is invoked
    frame.on_menu_edit_down(None)

    # Then: the native tree exports the moved order
    assert [action.label for action in frame.controller.export_actions()] == [
        "Save",
        "Border",
    ]


def test_context_menu_ignores_empty_selection(native_frame_harness) -> None:
    # Given: a native action tree with a property field selected
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    form = frame.tree.GetFirstChild(frame.tree.GetRootItem())[0]
    field = frame.tree.GetFirstChild(form)[0]
    frame.tree.SelectItem(field)

    # When: a context-menu event arrives
    frame.on_context_menu(None)

    # Then: no transient popup is retained by the controller
    assert frame.tree.is_field_selected()


def test_close_rejection_preserves_visible_frame(
    native_frame_harness, monkeypatch
) -> None:
    # Given: a visible editor whose file coordinator rejects closing
    frame = native_frame_harness.frame
    monkeypatch.setattr(frame.file_menu, "confirm_proceed", lambda: False)

    # When: close handling runs
    frame.on_close()

    # Then: the native frame remains visible and settings are not persisted
    assert frame.IsShown()
    assert native_frame_harness.app.save_settings_calls == 0


def test_missing_file_menu_allows_close_check(native_frame_harness) -> None:
    # Given: a frame at the pre-coordinator initialization boundary
    frame = native_frame_harness.frame
    frame.file_menu = None

    # When: save safety is queried
    result = frame.is_save_not_ok()

    # Then: no unsaved-state veto is reported
    assert not result


def test_save_existing_filename_persists_without_history_duplicate(
    native_frame_harness, tmp_path: Path
) -> None:
    # Given: a native action list with an established filename
    frame = native_frame_harness.frame
    path = tmp_path / "existing.phatch"
    frame.controller.add_action_by_label("Border")
    frame._set_filename(str(path))

    # When: Save persists the current filename
    frame._save()

    # Then: production persistence succeeds without adding Save-As history
    assert ActionListService().load(str(path)).actions[0].label == "Border"
    assert frame.filehistory.GetCount() == 0


def test_open_descriptionless_action_list_keeps_description_visible_state(
    native_frame_harness, tmp_path: Path
) -> None:
    # Given: a persisted action list with no semantic description
    path = tmp_path / "plain.phatch"
    ActionListService().save(str(path), "", [api.ACTIONS["Border"]()])

    # When: the real frame opens it
    native_frame_harness.frame._open(str(path))

    # Then: no transient description timer is needed and the action is loaded
    assert native_frame_harness.frame.filename == str(path)
    assert (
        native_frame_harness.frame.description.GetValue()
        == ct.ACTION_LIST_DESCRIPTION
    )
    assert not native_frame_harness.frame.IsEmpty()


@pytest.mark.parametrize(
    ("layout", "expected_suffix"),
    [
        ("root", "index.html"),
        ("build", "build/html/index.html"),
        ("installed", "share/phatch/docs/index.html"),
    ],
)
def test_plugin_help_resolves_documentation_layout_with_native_dialog(
    native_frame_harness,
    native_interaction,
    monkeypatch,
    tmp_path: Path,
    layout: str,
    expected_suffix: str,
) -> None:
    # Given: one supported documentation layout and a scripted real help dialog
    docs = tmp_path / "docs"
    if layout == "root":
        target = docs / "index.html"
        target.parent.mkdir(parents=True)
        target.touch()
    elif layout == "build":
        target = docs / "build" / "html" / "index.html"
        target.parent.mkdir(parents=True)
        target.touch()
    else:
        target = Path(gui.sys.prefix) / expected_suffix
    opened: list[str] = []
    monkeypatch.setitem(
        native_frame_harness.app.settings, "PHATCH_DOCS_PATH", str(docs)
    )
    monkeypatch.setattr(gui.webbrowser, "open", opened.append)
    native_interaction.expect_dialog(dialogs.WritePluginDialog, wx.ID_OK)

    # When: plugin help is invoked
    native_frame_harness.frame.on_menu_help_plugin(None)

    # Then: only the resolved local documentation target reaches the browser seam
    assert opened == [str(target)]


def test_documentation_menu_uses_outer_browser_launch_seam(
    native_frame_harness, monkeypatch
) -> None:
    # Given: browser launch is observed outside the frame
    opened: list[str] = []
    monkeypatch.setattr(gui.webbrowser, "open", opened.append)

    # When: the documentation menu handler runs
    native_frame_harness.frame.on_menu_help_documentation(None)

    # Then: exactly the configured documentation URL is requested
    assert opened == [gui.HELP_LINKS["documentation"]]


def test_cancelled_native_droplet_folder_prevents_export(
    native_frame_harness, native_interaction
) -> None:
    # Given: a real directory dialog scripted to cancel
    calls: list[str] = []
    native_interaction.expect_dialog(wx.DirDialog, wx.ID_CANCEL)

    # When: droplet export requests its destination
    native_frame_harness.frame.menu_file_export_droplet(
        lambda *, folder: calls.append(folder)
    )

    # Then: no exporter or success/error message runs
    assert calls == []
    assert not native_frame_harness.dialogs.infos
    assert not native_frame_harness.dialogs.errors
