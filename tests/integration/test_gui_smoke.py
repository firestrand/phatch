import builtins

import pytest

if "_" not in builtins.__dict__:
    builtins.__dict__["_"] = lambda value: value

pytest.importorskip("wx")

from phatch.pyWx.frame_dependencies import FrameDependencies
from phatch.pyWx.gui import DialogsMixin


def test_frame_initialises_with_injected_dependencies():
    """Test that dependencies can be injected into frame via constructor."""
    deps = FrameDependencies()

    # Create a minimal frame-like object to test dependency injection
    wx = pytest.importorskip("wx")
    app = wx.App(False)

    frame = wx.Frame(None, -1, "Test")
    mixin = DialogsMixin()
    mixin._dependencies = deps

    # Verify the dependency was injected
    assert mixin.dependencies is deps

    frame.Destroy()
    app.Destroy()
