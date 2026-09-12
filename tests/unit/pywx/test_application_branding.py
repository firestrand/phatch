from __future__ import annotations

import pytest

from phatch.pyWx import application_branding
from phatch.pyWx.application_branding import (
    ApplicationBrandingMixin,
    DockIconInstallError,
)


class DockIconRecorder:
    def __init__(self) -> None:
        self.destroy_calls = 0
        self.remove_calls = 0

    def Destroy(self) -> None:
        self.destroy_calls += 1

    def IsIconInstalled(self) -> bool:
        return True

    def RemoveIcon(self) -> bool:
        self.remove_calls += 1
        return True


class BrandingApplication(ApplicationBrandingMixin):
    def __init__(self) -> None:
        self.app_names: list[str] = []
        self.display_names: list[str] = []

    def SetAppName(self, name: str) -> None:
        self.app_names.append(name)

    def SetAppDisplayName(self, name: str) -> None:
        self.display_names.append(name)


class FailingDockIcon(DockIconRecorder):
    latest: FailingDockIcon | None = None

    def __init__(self, icon_type: int) -> None:
        del icon_type
        super().__init__()
        type(self).latest = self

    def SetIcon(self, bundle, tooltip: str) -> bool:
        del bundle, tooltip
        return False


class WxModule:
    BITMAP_TYPE_PNG = 1

    class Image:
        def __init__(self, stream, bitmap_type: int) -> None:
            del stream, bitmap_type

    class Bitmap:
        def __init__(self, image) -> None:
            del image

    class BitmapBundle:
        @staticmethod
        def FromBitmap(bitmap):
            return bitmap


class WxAdvModule:
    TBI_DOCK = 0
    TaskBarIcon = FailingDockIcon


def test_successful_macos_install_uses_dock_not_system_tray(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed: list[tuple[int, str]] = []

    class SuccessfulDockIcon(DockIconRecorder):
        def __init__(self, icon_type: int) -> None:
            super().__init__()
            self.icon_type = icon_type

        def SetIcon(self, bundle, tooltip: str) -> bool:
            installed.append((self.icon_type, tooltip))
            return True

    monkeypatch.setattr(WxAdvModule, "TaskBarIcon", SuccessfulDockIcon)
    monkeypatch.setattr(
        application_branding,
        "import_module",
        lambda name: WxModule if name == "wx" else WxAdvModule,
    )

    icon = application_branding.install_macos_dock_icon(platform="darwin")

    assert isinstance(icon, SuccessfulDockIcon)
    assert installed == [(WxAdvModule.TBI_DOCK, "Phatch")]
    assert icon.destroy_calls == 0


def test_application_exit_destroys_owned_dock_icon_once() -> None:
    # Given: application branding that owns a native Dock icon
    app = BrandingApplication()
    icon = DockIconRecorder()
    app._dock_icon = icon

    # When: cleanup runs repeatedly across explicit and framework exit paths
    first_result = app.OnExit()
    second_result = app.OnExit()

    # Then: native ownership is released exactly once and exit remains successful
    assert icon.destroy_calls == 1
    assert icon.remove_calls == 1
    assert app._dock_icon is None
    assert (first_result, second_result) == (0, 0)


def test_application_branding_sets_name_without_release_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a wx application whose platform icon installation is isolated
    app = BrandingApplication()
    monkeypatch.setattr(application_branding, "install_macos_dock_icon", lambda: None)

    # When: the shared application branding boundary initializes
    app._install_application_branding()

    # Then: native application identity uses only the product name
    assert app.app_names == ["Phatch"]
    assert app.display_names == ["Phatch"]


def test_non_macos_branding_does_not_import_or_create_wx_taskbar_icon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a non-macOS application process where wx taskbar APIs are forbidden
    def reject_wx_import(module_name: str):
        raise AssertionError(f"unexpected GUI import: {module_name}")

    monkeypatch.setattr(application_branding, "import_module", reject_wx_import)

    # When: application branding is initialized
    icon = application_branding.install_macos_dock_icon(platform="linux")

    # Then: the platform no-op creates no Dock or system-tray icon
    assert icon is None


def test_failed_native_install_destroys_taskbar_icon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: wx accepts a Dock icon owner but rejects its bitmap bundle
    def import_fake_wx(module_name: str):
        return WxModule if module_name == "wx" else WxAdvModule

    monkeypatch.setattr(application_branding, "import_module", import_fake_wx)

    # When: native icon installation reports failure
    with pytest.raises(DockIconInstallError):
        application_branding.install_macos_dock_icon(platform="darwin")

    # Then: the rejected native owner is destroyed instead of leaking globally
    assert FailingDockIcon.latest is not None
    assert FailingDockIcon.latest.destroy_calls == 1
