"""Native application branding lifecycle for wx GUI entry points."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib import import_module
from io import BytesIO
from typing import Protocol

from phatch.data.info import NAME
from phatch.resources.provider import ResourceProvider

DOCK_ICON_RESOURCE = "images/icons/256x256/phatch.png"


class DockIcon(Protocol):
    def Destroy(self) -> None: ...

    def IsIconInstalled(self) -> bool: ...

    def RemoveIcon(self) -> bool: ...


class ApplicationIdentity(Protocol):
    _dock_icon: DockIcon | None

    def SetAppName(self, name: str) -> None: ...

    def SetAppDisplayName(self, name: str) -> None: ...


@dataclass(frozen=True, slots=True)
class DockIconInstallError(RuntimeError):
    resource: str

    def __str__(self) -> str:
        return f"wxPython could not install the macOS Dock icon: {self.resource}"


def install_macos_dock_icon(*, platform: str | None = None) -> DockIcon | None:
    current_platform = sys.platform if platform is None else platform
    if current_platform != "darwin":
        return None

    wx = import_module("wx")
    wx_adv = import_module("wx.adv")
    payload = ResourceProvider().read_bytes(DOCK_ICON_RESOURCE)
    image = wx.Image(BytesIO(payload), wx.BITMAP_TYPE_PNG)
    bundle = wx.BitmapBundle.FromBitmap(wx.Bitmap(image))
    dock_icon = wx_adv.TaskBarIcon(wx_adv.TBI_DOCK)
    if dock_icon.SetIcon(bundle, NAME):
        return dock_icon
    dock_icon.Destroy()
    raise DockIconInstallError(resource=DOCK_ICON_RESOURCE)


class ApplicationBrandingMixin:
    """Own the native application icon until the wx application exits."""

    _dock_icon: DockIcon | None = None

    def _install_application_branding(self: ApplicationIdentity) -> None:
        self.SetAppName(NAME)
        self.SetAppDisplayName(NAME)
        self._dock_icon = install_macos_dock_icon()

    def _cleanup_application_branding(self) -> None:
        dock_icon = self._dock_icon
        self._dock_icon = None
        if dock_icon is not None:
            dock_icon.RemoveIcon()
            dock_icon.Destroy()

    def OnExit(self) -> int:
        self._cleanup_application_branding()
        return 0
