from __future__ import annotations

import sys

import pytest

from phatch.pyWx.application_branding import ApplicationBrandingMixin

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


class NativeBrandingApplication(ApplicationBrandingMixin, wx.App):
    def __init__(self) -> None:
        wx.App.__init__(self, False)

    def OnInit(self) -> bool:
        self._install_application_branding()
        return True


def test_real_application_installs_dock_icon_only_on_macos() -> None:
    # Given: a real initialized wx application using production branding
    app = NativeBrandingApplication()

    try:
        # When: the native branding helper completes startup
        icon = app._dock_icon

        # Then: wx reports the packaged Phatch Dock icon as installed
        if sys.platform == "darwin":
            assert icon is not None
            assert icon.IsIconInstalled()
        else:
            assert icon is None
    finally:
        app.OnExit()
        wx.Yield()
        app.Destroy()
