from __future__ import annotations

import pytest

from phatch.core import config, ct
from phatch.pyWx import gui
from phatch.services.action_list import ActionListService

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


def test_action_enable_state_updates_native_toolbar_menu_and_panels(
    native_frame_harness,
) -> None:
    # Given: an empty real frame with native action controls
    frame = native_frame_harness.frame

    # When: action-dependent controls are enabled then disabled
    frame.enable_actions(True)
    enabled = [frame.frame_toolbar.GetToolEnabled(tool) for tool in frame.tools_item]
    frame.enable_actions(False)

    # Then: toolbar and panel visibility consistently reflect both states
    assert all(enabled)
    assert all(
        not frame.frame_toolbar.GetToolEnabled(tool) for tool in frame.tools_item
    )
    assert not frame.tree.IsShown()
    assert frame.empty.IsShown()


def test_global_menu_and_toolbar_state_changes_native_controls(
    native_frame_harness,
) -> None:
    # Given: a fully enabled real menu bar and toolbar
    frame = native_frame_harness.frame

    # When: global frame controls are disabled
    frame.enable_menu(False)
    frame.enable_toolbar(False)

    # Then: each native top menu and tool is disabled
    assert all(
        not frame.frame_menubar.IsEnabledTop(index)
        for index in range(frame.frame_menubar.GetMenuCount())
    )
    assert all(
        not frame.frame_toolbar.GetToolEnabled(tool) for tool in frame.tools_all
    )


def test_paint_message_sets_and_resets_visible_frame_state(
    native_frame_harness,
) -> None:
    # Given: a real frame with its default paint message
    frame = native_frame_harness.frame

    # When: a status message is set and then reset
    frame.show_paint_message("Drop files here")
    assert frame.paint_message == "Drop files here"
    frame.show_paint_message()

    # Then: the frame restores its documented default
    assert frame.paint_message == frame.DEFAULT_PAINT_MESSAGE


def test_new_resets_populated_native_editor(native_frame_harness) -> None:
    # Given: a dirty native action tree
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")

    # When: the frame creates a new action-list state
    state = frame._new()

    # Then: native tree and controller return to clean defaults
    assert frame.IsEmpty()
    assert not state.dirty
    assert state.filename == ct.UNKNOWN


def test_save_placeholder_description_persists_as_empty(
    native_frame_harness, tmp_path
) -> None:
    # Given: a native tree whose description is the placeholder
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    frame.description.SetValue(ct.ACTION_LIST_DESCRIPTION)
    path = tmp_path / "placeholder.phatch"

    # When: the frame persists the action list
    frame._save(str(path))

    # Then: the service stores an empty semantic description
    assert ActionListService().load(str(path)).description == ""


def test_image_input_reports_guidance_and_opens_library_example(
    native_frame_harness, test_input_dir
) -> None:
    # Given: a real image path instead of an action-list path
    image = next(test_input_dir.glob("*.png"))

    # When: the frame attempts to open the image
    native_frame_harness.frame._open(str(image))

    # Then: user guidance is reported without treating the image as an action list
    assert native_frame_harness.dialogs.errors[0] == gui.NO_PHOTOS
    assert native_frame_harness.frame.filename == ct.UNKNOWN


def test_append_save_advice_adds_real_save_action(native_frame_harness) -> None:
    # Given: a native action list without a Save action
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    actions = list(frame.controller.export_actions())

    # When: the frame handles save-action advice
    frame.append_save_action(actions)

    # Then: advice is shown and the actual Save form is appended
    assert native_frame_harness.dialogs.messages
    assert [action.label for action in frame.controller.export_actions()] == [
        "Border",
        "Save",
    ]


def test_droplet_folder_selection_updates_isolated_setting(
    native_frame_harness, tmp_path, monkeypatch
) -> None:
    # Given: a real frame whose directory interaction returns an isolated path
    chosen = str(tmp_path / "droplets")
    monkeypatch.setattr(
        native_frame_harness.frame,
        "show_dir_dialog",
        lambda **_options: chosen,
    )

    # When: the frame requests its droplet folder
    result = native_frame_harness.frame.get_droplet_folder()

    # Then: result and app setting retain the chosen path
    assert result == chosen
    assert native_frame_harness.app.settings["droplet_path"] == chosen


def test_droplet_export_reports_success_and_typed_failure(
    native_frame_harness, tmp_path, monkeypatch
) -> None:
    # Given: an isolated selected folder and two export adapters
    monkeypatch.setattr(
        native_frame_harness.frame,
        "get_droplet_folder",
        lambda: str(tmp_path),
    )
    calls: list[str] = []

    def succeed(*, folder: str) -> None:
        calls.append(folder)

    def fail(*, folder: str) -> None:
        raise OSError(folder)

    # When: successful and failing exports cross the frame boundary
    native_frame_harness.frame.menu_file_export_droplet(succeed)
    native_frame_harness.frame.menu_file_export_droplet(fail)

    # Then: both outcomes produce explicit user-visible state
    assert calls == [str(tmp_path)]
    assert native_frame_harness.dialogs.infos
    assert str(tmp_path) in native_frame_harness.dialogs.errors[-1]


def test_miscellaneous_handlers_preserve_real_frame_state(native_frame_harness) -> None:
    # Given: a real frame and native checked/enter events
    frame = native_frame_harness.frame
    checked = wx.CommandEvent()
    checked.SetInt(1)
    enter = wx.CommandEvent()

    # When: simple view/tool handlers are routed
    frame.on_menu_view_droplet(checked)
    wx.Yield()
    frame.on_menu_tools_safe(checked)
    frame.on_menu_tools_show_report(None)
    frame.on_menu_tools_show_log(None)
    frame.on_menu_tool_enter(enter)

    # Then: stateful handlers leave the native editor available
    assert frame.IsShown()
    assert ("report", ()) in native_frame_harness.dialogs.calls
    assert ("log", ()) in native_frame_harness.dialogs.calls


def test_context_menu_uses_detached_native_menu(
    native_frame_harness, monkeypatch
) -> None:
    # Given: a selected real tree action and an observed controller boundary
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    observed: list[tuple[bool, list[int]]] = []

    def observe(menu) -> None:
        observed.append(
            (
                not menu.IsAttached(),
                [
                    item.GetId()
                    for item in menu.GetMenuItems()
                    if not item.IsSeparator()
                ],
            )
        )

    monkeypatch.setattr(frame.controller, "show_context_menu", observe)

    # When: the frame handles a context-menu request
    frame.on_context_menu(None)

    # Then: Cocoa receives a detached menu preserving the edit command IDs
    assert observed == [
        (
            True,
            [
                item.GetId()
                for item in frame.menu_edit.GetMenuItems()
                if not item.IsSeparator()
            ],
        )
    ]


def test_frame_path_helpers_and_window_lookup_use_native_state(
    native_frame_harness,
) -> None:
    # Given: a real frame and configured protected library path
    frame = native_frame_harness.frame

    # When: helper APIs inspect native/configured state
    found = gui.findWindowById(frame.description.GetId())
    protected = frame.is_protected_actionlist(
        str(config.PATHS["PHATCH_ACTIONLISTS_PATH"] + "/example.phatch")
    )

    # Then: wx lookup and protection decisions are concrete
    assert found is frame.description
    assert protected
