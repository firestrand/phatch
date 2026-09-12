from __future__ import annotations

from pathlib import Path

import pytest

from phatch.core import api, config, settings
from phatch.pyWx import gui
from phatch.pyWx.frame_dependencies import FrameDependencies
from phatch.services.action_list import ActionListLoadResult, ActionListService

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


def destroy_app(app) -> None:
    for window in tuple(wx.GetTopLevelWindows()):
        if getattr(window, "_listeners", None):
            window.unsubscribe_all()
        window.Destroy()
    wx.Yield()
    app.Destroy()


def test_application_replaces_real_splash_with_native_main_frame(
    native_runtime, monkeypatch
) -> None:
    # Given: isolated runtime settings and suppressed persistence adapter
    saved: list[bool] = []
    monkeypatch.setattr(
        gui.DropletMixin,
        "_saveSettings",
        lambda _app: saved.append(True),
    )
    app = gui.App(settings.create_settings(config.PATHS), "", False)

    try:
        # When: deferred native startup events are processed
        wx.Yield()
        frame = app.GetTopWindow()

        # Then: the visible top-level window is the production main frame
        assert isinstance(frame, gui.Frame)
        assert frame.IsShown()
        assert not hasattr(app, "splash")
        frame.filehistory.AddFileToHistory(str(native_runtime.root / "one.phatch"))
        app.MacReopenApp()
        app._saveSettings()
        assert app.settings["file_history"]
        assert saved == [True]
    finally:
        destroy_app(app)


class DropletActionService(ActionListService):
    def __init__(self) -> None:
        self.executions: list[tuple] = []

    def load(self, filename: str) -> ActionListLoadResult:
        return ActionListLoadResult(
            data={"actions": [api.ACTIONS["Save"]()]},
            warning="",
            invalid_labels=(),
        )

    def execute(
        self, actions, settings, update_callback=None, recovery=None, **options
    ) -> None:
        self.executions.append((tuple(actions), settings, options))


def test_droplet_application_executes_and_closes_hidden_native_frame(
    native_runtime, tmp_path: Path
) -> None:
    # Given: a real droplet app with an existing isolated action-list path
    actionlist = tmp_path / "droplet.phatch"
    actionlist.touch()
    service = DropletActionService()
    dependencies = FrameDependencies(action_service_factory=lambda: service)
    app = gui.DropletApp(
        str(actionlist),
        ["input.png"],
        settings.create_settings(config.PATHS),
        False,
        dependencies=dependencies,
    )

    try:
        frame = app.GetTopWindow()
        assert isinstance(frame, gui.DropletFrame)
        assert not frame.IsShown()

        # When: deferred droplet execution is processed
        wx.Yield()

        # Then: production routing executes once and destroys its hidden frame
        assert len(service.executions) == 1
        assert service.executions[0][2] == {"paths": ["input.png"], "drop": True}
        assert not wx.GetTopLevelWindows()
    finally:
        destroy_app(app)


def test_settings_lifecycle_reads_and_writes_only_isolated_path(
    native_frame_harness, tmp_path: Path
) -> None:
    # Given: a real app and an isolated settings file with persistent values
    config_path = Path(gui.ct.USER_SETTINGS_PATH)
    assert config_path.is_relative_to(native_frame_harness.root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "{'description': False, 'desktop': True, 'USER_PATH': 'ignored'}",
        encoding="utf-8",
    )
    values = settings.create_settings(config.PATHS)

    # When: the application settings lifecycle loads and saves
    gui.DropletMixin._loadSettings(native_frame_harness.app, values)
    gui.DropletMixin._saveSettings(native_frame_harness.app)

    # Then: persistent data stays isolated and transient/path values are filtered
    persisted = config_path.read_text(encoding="utf-8")
    assert not native_frame_harness.app.settings["description"]
    assert "desktop" not in persisted
    assert "USER_PATH" in persisted


def test_corrupt_isolated_settings_report_and_exit(
    native_frame_harness, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given: a corrupt settings file under the isolated runtime
    config_path = Path(gui.ct.USER_SETTINGS_PATH)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("not valid python", encoding="utf-8")

    # When: settings loading reaches the application boundary
    with pytest.raises(SystemExit):
        gui.DropletMixin._loadSettings(
            native_frame_harness.app,
            settings.create_settings(config.PATHS),
        )

    # Then: the input error is reported without touching the real home
    assert "settings seem corrupt" in capsys.readouterr().out


def test_droplet_file_discovery_uses_isolated_user_library(
    native_frame_harness,
) -> None:
    # Given: one action list in the isolated user action-list directory
    user_path = Path(gui.ct.USER_ACTIONLISTS_PATH)
    user_path.mkdir(parents=True, exist_ok=True)
    actionlist = user_path / "recent.phatch"
    actionlist.touch()

    # When: droplet discovery scans configured libraries
    files = gui.DropletMixin.get_action_list_files(native_frame_harness.app)

    # Then: the isolated action list is discoverable
    assert str(actionlist) in files
