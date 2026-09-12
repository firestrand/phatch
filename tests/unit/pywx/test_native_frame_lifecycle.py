from __future__ import annotations

import pytest

from phatch.core import ct

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


def test_frame_is_shown_with_native_controls_and_initial_state(
    native_frame_harness,
) -> None:
    # Given: the isolated native frame fixture
    frame = native_frame_harness.frame

    # When: wx finishes processing frame construction
    wx.Yield()

    # Then: the actual controls expose the initial editor state
    assert frame.IsShown()
    assert frame.GetMenuBar().GetMenuCount() == 5
    assert frame.GetToolBar().GetToolsCount() == 11
    assert len(frame.tools_all) == 8
    assert frame.filename == ct.UNKNOWN
    assert frame.IsEmpty()
    assert not frame.tree.IsShown()
    assert frame.empty.IsShown()


def test_close_hides_destroys_and_requests_settings_save(native_frame_harness) -> None:
    # Given: a clean visible native frame
    frame = native_frame_harness.frame
    frame_id = frame.GetId()

    # When: the real close event is dispatched
    frame.Close()
    wx.Yield()

    # Then: lifecycle persistence runs and the native frame is gone
    assert native_frame_harness.app.save_settings_calls == 1
    assert all(window.GetId() != frame_id for window in wx.GetTopLevelWindows())
