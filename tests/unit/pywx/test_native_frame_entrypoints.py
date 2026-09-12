from __future__ import annotations

from pathlib import Path

import pytest

from phatch.core import api, config, settings
from phatch.pyWx import gui
from phatch.pyWx.frame_dependencies import FrameDependencies
from phatch.services.action_list import (
    ActionListLoadResult,
    ActionListService,
    IncompatibleActionListError,
)

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


class EmptyActionService(ActionListService):
    def load(self, filename: str) -> ActionListLoadResult:
        raise IncompatibleActionListError(filename)


def destroy_app(app) -> None:
    for window in tuple(wx.GetTopLevelWindows()):
        if getattr(window, "_listeners", None):
            window.unsubscribe_all()
        window.Destroy()
    wx.Yield()
    app.OnExit()
    wx.Yield()
    app.Destroy()


def test_droplet_selection_cancel_returns_no_action_list(
    native_frame_harness, native_interaction, monkeypatch, tmp_path: Path
) -> None:
    # Given: one real candidate and a scripted cancellation of the native chooser
    candidate = tmp_path / "candidate.phatch"
    candidate.touch()
    monkeypatch.setattr(
        wx.SingleChoiceDialog,
        "ShowModal",
        lambda dialog: native_interaction.show_modal(dialog),
    )
    native_interaction.expect_dialog(wx.SingleChoiceDialog, wx.ID_CANCEL)

    # When: the droplet action-list chooser runs
    result = gui.DropletMixin.get_action_list(
        native_frame_harness.app, [str(candidate)]
    )

    # Then: cancellation has an explicit absent result
    assert result is None


def test_droplet_selection_accepts_native_choice(
    native_frame_harness, native_interaction, monkeypatch, tmp_path: Path
) -> None:
    # Given: one candidate selected by the real native chooser
    candidate = tmp_path / "candidate.phatch"
    candidate.touch()
    monkeypatch.setattr(
        wx.SingleChoiceDialog,
        "GetStringSelection",
        lambda _dialog: "Candidate",
    )
    monkeypatch.setattr(
        wx.SingleChoiceDialog,
        "ShowModal",
        lambda dialog: native_interaction.show_modal(dialog),
    )
    native_interaction.expect_dialog(wx.SingleChoiceDialog, wx.ID_OK)

    # When: the chooser is accepted
    result = gui.DropletMixin.get_action_list(
        native_frame_harness.app, [str(candidate)]
    )

    # Then: the selected title resolves to its source path
    assert result == str(candidate)


def test_empty_droplet_selection_rechecks_discovery(
    native_frame_harness, native_interaction, monkeypatch
) -> None:
    # Given: both supplied and discovered action-list collections are empty
    monkeypatch.setattr(
        native_frame_harness.app,
        "get_action_list_files",
        lambda: [],
        raising=False,
    )
    monkeypatch.setattr(
        wx.SingleChoiceDialog,
        "ShowModal",
        lambda dialog: native_interaction.show_modal(dialog),
    )
    native_interaction.expect_dialog(wx.SingleChoiceDialog, wx.ID_CANCEL)

    # When: selection starts without candidates
    result = gui.DropletMixin.get_action_list(native_frame_harness.app, [])

    # Then: the real empty chooser can be cancelled safely
    assert result is None


def test_droplet_frame_reports_unloadable_action_list(
    native_frame_harness, native_interaction, tmp_path: Path
) -> None:
    # Given: an existing action list rejected by the load boundary
    path = tmp_path / "unloadable.phatch"
    path.touch()
    dependencies = FrameDependencies(action_service_factory=EmptyActionService)
    native_interaction.expect_dialog(wx.MessageDialog, wx.ID_OK)

    # When: the production droplet frame attempts initialization
    with pytest.raises(SystemExit, match="Impossible to load"):
        gui.DropletFrame(
            str(path),
            ["input.png"],
            None,
            wx.ID_ANY,
            "droplet",
            dependencies=dependencies,
        )

    # Then: no executable droplet becomes the application's top window
    assert native_frame_harness.app.GetTopWindow() is native_frame_harness.frame


def test_recent_droplet_cancel_stops_before_frame_creation(
    native_runtime, native_interaction, monkeypatch
) -> None:
    # Given: recent mode with no isolated action lists and a cancelled native chooser
    branding_installs: list[bool] = []
    monkeypatch.setattr(
        gui.DropletMixin,
        "_install_application_branding",
        lambda _app: branding_installs.append(True),
    )
    monkeypatch.setattr(
        wx.SingleChoiceDialog,
        "ShowModal",
        lambda dialog: native_interaction.show_modal(dialog),
    )
    native_interaction.expect_dialog(wx.SingleChoiceDialog, wx.ID_CANCEL)

    # When: a real droplet app initializes
    with pytest.raises(SystemExit, match="OnInit returned false"):
        gui.DropletApp(
            "recent",
            ["input.png"],
            settings.create_settings(config.PATHS),
            False,
        )

    # Then: initialization owns no top-level processing frame
    assert not wx.GetTopLevelWindows()
    assert branding_installs == []


def test_inspect_entrypoint_owns_scripted_main_loop(
    native_runtime, native_interaction, test_input_dir
) -> None:
    # Given: a real image and one expected application loop
    image = next(test_input_dir.glob("*.png"))
    native_interaction.expect_main_loop()

    # When: the image-inspector entrypoint runs
    gui.inspect([str(image)])

    # Then: the loop belongs to an inspector app with a native top window
    app = native_interaction.main_loop_apps[-1]
    try:
        assert isinstance(app, gui.ImageInspectorApp)
        assert app.GetTopWindow().IsShown()
    finally:
        destroy_app(app)


def test_main_entrypoint_owns_scripted_main_loop(
    native_runtime, native_interaction
) -> None:
    # Given: isolated settings and one expected application loop
    native_interaction.expect_main_loop()

    # When: the main GUI entrypoint runs
    gui.main(settings.create_settings(config.PATHS), "")

    # Then: the loop belongs to the production application
    app = native_interaction.main_loop_apps[-1]
    try:
        assert isinstance(app, gui.App)
    finally:
        destroy_app(app)


def test_drop_entrypoint_owns_scripted_main_loop(
    native_runtime, native_interaction, tmp_path: Path
) -> None:
    # Given: a persisted executable action list and one expected loop
    path = tmp_path / "drop.phatch"
    ActionListService().save(str(path), "", [api.ACTIONS["Save"]()])
    native_interaction.expect_main_loop()

    # When: the droplet entrypoint runs
    gui.drop(
        str(path),
        ["input.png"],
        settings.create_settings(config.PATHS),
    )

    # Then: the loop belongs to the production droplet application
    app = native_interaction.main_loop_apps[-1]
    try:
        assert isinstance(app, gui.DropletApp)
    finally:
        destroy_app(app)


def test_dependencies_are_lazily_recreated_at_real_frame_boundary(
    native_frame_harness,
) -> None:
    # Given: a real frame before its optional dependency container is assigned
    frame = native_frame_harness.frame
    del frame._dependencies

    # When: a frame service first requests dependencies
    dependencies = frame.dependencies

    # Then: the frame owns a concrete production dependency container
    assert isinstance(dependencies, FrameDependencies)
    assert frame.dependencies is dependencies


def test_constructor_defers_initial_action_list_until_native_frame_exists(
    native_frame_harness, tmp_path: Path
) -> None:
    # Given: a persisted action list passed directly to a second real frame
    path = tmp_path / "initial.phatch"
    ActionListService().save(str(path), "", [api.ACTIONS["Border"]()])

    # When: construction completes and wx processes the deferred callback
    frame = gui.Frame(
        str(path),
        None,
        wx.ID_ANY,
        "initial",
        dependencies=native_frame_harness.frame.dependencies,
    )
    frame.Show()
    wx.Yield()

    # Then: the callback populates the live tree after initialization
    assert frame.filename == str(path)
    assert [action.label for action in frame.controller.export_actions()] == ["Border"]
