import builtins

import pytest

if "_" not in builtins.__dict__:
    builtins.__dict__["_"] = lambda value: value


@pytest.mark.skip(reason="Requires wxPython to instantiate DropletApp")
def test_droplet_app_accepts_dependencies():
    pytest.importorskip("wx")
    from phatch.pyWx.frame_dependencies import FrameDependencies
    from phatch.pyWx.gui import DropletApp

    deps = FrameDependencies()
    app = DropletApp("recent", [], {}, dependencies=deps)

    assert app._dependencies is deps
