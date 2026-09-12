from __future__ import annotations

from pathlib import Path

import pytest

from phatch.core import api, ct
from phatch.services.action_list import ActionListService

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


@pytest.fixture
def saved_actionlist(native_runtime, tmp_path: Path) -> Path:
    path = tmp_path / "loaded actions.phatch"
    ActionListService().save(
        str(path),
        "native description",
        [api.ACTIONS["Border"](), api.ACTIONS["Save"]()],
    )
    return path


def test_open_loads_persisted_actions_into_native_tree(
    native_frame_harness, saved_actionlist: Path
) -> None:
    # Given: a real persisted action list and an empty native editor
    frame = native_frame_harness.frame

    # When: the frame opens the action list
    frame._open(str(saved_actionlist))

    # Then: native controls and controller state represent the file
    assert frame.filename == str(saved_actionlist)
    assert frame.description.GetValue() == "native description"
    assert [action.label for action in frame.controller.export_actions()] == [
        "Border",
        "Save",
    ]
    assert frame.tree.IsShown()
    assert not frame.empty.IsShown()
    assert frame.filehistory.GetCount() == 1


def test_save_persists_native_tree_and_normalizes_suffix(
    native_frame_harness, tmp_path: Path
) -> None:
    # Given: a native editor containing a real action and description
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    frame.description.SetValue("saved from native frame")
    destination = tmp_path / "saved actions"

    # When: the frame saves to a suffix-less temporary path
    frame._save(str(destination))

    # Then: the saved file round-trips through the production service
    saved_path = destination.with_suffix(ct.EXTENSION)
    loaded = ActionListService().load(str(saved_path))
    assert frame.filename == str(saved_path)
    assert loaded.description == "saved from native frame"
    assert [action.label for action in loaded.actions] == ["Border"]
    assert not frame.controller.state.dirty
    assert frame.filehistory.GetHistoryFile(0) == str(saved_path)


def test_open_missing_path_reports_input_error_in_frame(native_frame_harness) -> None:
    # Given: a path outside the isolated runtime that does not exist
    frame = native_frame_harness.frame
    missing = native_frame_harness.root / "missing.phatch"

    # When: the frame receives the invalid path
    frame._open(str(missing))

    # Then: the dialog boundary receives the error and the editor stays empty
    assert native_frame_harness.dialogs.errors
    assert str(missing) in native_frame_harness.dialogs.errors[-1]
    assert frame.IsEmpty()
    assert frame.filename == ct.UNKNOWN


def test_open_incompatible_file_reports_input_error(
    native_frame_harness, tmp_path: Path
) -> None:
    # Given: an existing file that is not an action list
    invalid = tmp_path / "invalid.phatch"
    invalid.write_text("not an action list", encoding="utf-8")

    # When: the frame attempts to open it
    native_frame_harness.frame._open(str(invalid))

    # Then: the compatibility error is reported without populating the tree
    assert native_frame_harness.dialogs.errors
    assert native_frame_harness.frame.IsEmpty()


def test_file_history_round_trips_existing_native_paths(
    native_frame_harness, saved_actionlist: Path, tmp_path: Path
) -> None:
    # Given: two existing files in newest-first settings order
    second = tmp_path / "second.phatch"
    second.write_text("placeholder", encoding="utf-8")

    # When: history is loaded and read through the frame
    native_frame_harness.frame._set_file_history([str(saved_actionlist), str(second)])

    # Then: wx FileHistory preserves both valid entries
    assert native_frame_harness.frame._get_file_history() == [
        str(saved_actionlist),
        str(second),
    ]
