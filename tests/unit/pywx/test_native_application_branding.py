from __future__ import annotations

import sys

import pytest

from phatch.data import info
from phatch.data.version import VERSION
from phatch.lib.pyWx import about
from phatch.pyWx.application_branding import ApplicationBrandingMixin

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


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

        # Then: wx reports the product identity without a version suffix
        assert app.GetAppName() == info.NAME
        assert app.GetAppDisplayName() == info.NAME
        if sys.platform == "darwin":
            assert icon is not None
            assert icon.IsIconInstalled()
        else:
            assert icon is None
    finally:
        app.OnExit()
        wx.Yield()
        app.Destroy()


def test_about_menu_shows_product_name_with_canonical_version(
    native_frame_harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: the production About dialog observed at its modal boundary
    shown_titles: list[str] = []

    def show_modal(dialog: about.Dialog) -> int:
        shown_titles.append(dialog.title.GetLabel())
        return wx.ID_CLOSE

    monkeypatch.setattr(about.Dialog, "ShowModal", show_modal)

    # When: the real frame handles Help > About
    native_frame_harness.frame.on_menu_help_about(None)

    # Then: About identifies the product and its canonical release
    assert shown_titles == [f"{info.NAME} {VERSION}"]
