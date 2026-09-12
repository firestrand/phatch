from __future__ import annotations

import pytest

from phatch.lib.events import send
from phatch.pyWx import dialogs
from phatch.pyWx.dialog_service import DialogService

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


def test_progress_api_shows_updates_and_closes_real_native_dialog(
    native_frame_harness,
) -> None:
    # Given: the native frame wired to the production dialog service
    frame = native_frame_harness.frame
    frame._dialog_service = DialogService(frame)

    # When: progress is shown and updated through the real pubsub channel
    frame.show_progress("Native progress", 2, 2, "starting")
    progress = next(
        window
        for window in wx.GetTopLevelWindows()
        if isinstance(window, dialogs.ProgressDialog)
    )
    result = {}
    send.progress_update(result, 1, newmsg="working")
    wx.Yield()

    # Then: the real progress window remains live and reports continuation
    assert progress.IsShown()
    assert result == {"keepgoing": True, "skip": False}

    send.progress_close()
    wx.Yield()
    assert all(
        not isinstance(window, dialogs.ProgressDialog)
        for window in wx.GetTopLevelWindows()
    )


def test_valid_droplet_toggle_shows_and_closes_native_droplet(
    native_frame_harness,
) -> None:
    # Given: a valid native action list ending in Save
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")
    frame.controller.add_action_by_label_to_last("Save")
    frame._set_filename(str(native_frame_harness.root / "droplet.phatch"))

    # When: droplet mode is enabled
    frame.show_droplet(True)
    wx.Yield()

    # Then: a real droplet replaces the editor and menu state follows it
    droplet_windows = [
        window for window in wx.GetTopLevelWindows() if window is not frame
    ]
    assert len(droplet_windows) == 1
    assert droplet_windows[0].IsShown()
    assert not frame.IsShown()
    assert frame.menu_view_droplet.IsChecked()
    assert native_frame_harness.dialogs.messages

    frame.show_droplet(False)
    wx.Yield()
    assert frame.IsShown()
    assert not frame.menu_view_droplet.IsChecked()


def test_invalid_droplet_toggle_restores_native_menu_state(
    native_frame_harness,
) -> None:
    # Given: an action list without a required Save action
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label("Border")

    # When: droplet mode is requested through the frame
    frame.show_droplet(True)
    wx.Yield()

    # Then: no droplet opens and deferred state returns to unchecked
    assert frame.IsShown()
    assert not frame.menu_view_droplet.IsChecked()
    assert len(wx.GetTopLevelWindows()) == 1


def test_droplet_show_event_releases_hidden_native_window(native_frame_harness) -> None:
    # Given: a valid droplet that has been materialized
    frame = native_frame_harness.frame
    frame.controller.add_action_by_label_to_last("Save")
    frame._set_filename(str(native_frame_harness.root / "managed.phatch"))
    frame.show_droplet(True)
    wx.Yield()

    # When: its real show callback reports hidden state
    frame.on_show_droplet(False)

    # Then: frame state is unchecked and a future toggle can create anew
    assert not frame.menu_view_droplet.IsChecked()
