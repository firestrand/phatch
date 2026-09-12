from __future__ import annotations

import pytest

try:
    import wx
except ImportError:
    pytest.skip("wxPython runtime unavailable", allow_module_level=True)

from .native_tree_support import requires_native_display

pytestmark = [pytest.mark.unit, pytest.mark.requires_display, requires_native_display]


def test_example_constructs_real_tree_without_blocking_event_loop(
    native_interaction,
) -> None:
    from phatch.lib.pyWx import treeEdit

    native_interaction.expect_main_loop()

    treeEdit.example()

    app = native_interaction.main_loop_apps[0]
    frame = app.GetTopWindow()
    assert isinstance(frame, wx.Frame)
    assert frame.IsShown()
    assert frame.GetTitle() == "treeEdit test"
    assert frame.GetChildren()[0].GetCount() > 0
    frame.Destroy()
    app.Destroy()
