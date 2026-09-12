from __future__ import annotations

import importlib

from phatch.core import ct
from phatch.lib.windows.register import ExplorerVerbError

from .droplet import (
    EXTENSIONS_INSTALL_SUCCESFUL,
    EXTENSIONS_INSTALL_UNSUCCESFUL,
    EXTENSIONS_UNINSTALL,
    DropletLauncherError,
    create_phatch_droplet,
    create_phatch_explorer_action,
    create_phatch_inspect_explorer_action,
    create_phatch_inspector_droplet,
    create_phatch_recent_droplet,
    create_phatch_recent_explorer_action,
    remove_phatch_explorer_actions,
    win32_missing,
)


def on_menu_file_export_droplet_actionlist(self, event) -> None:
    del event
    if self.is_save_not_ok() or win32_missing(self):
        return
    self.menu_file_export_droplet(create_phatch_droplet, self.filename)


def on_menu_file_export_droplet_recent(self, event) -> None:
    del event
    if not win32_missing(self):
        self.menu_file_export_droplet(create_phatch_recent_droplet)


def on_menu_file_export_droplet_inspector(self, event) -> None:
    del event
    if not win32_missing(self):
        self.menu_file_export_droplet(create_phatch_inspector_droplet)


def menu_file_export_explorer(self, method, *args, **kwargs) -> None:
    try:
        result = method(*args, **kwargs)
    except (ExplorerVerbError, DropletLauncherError):
        self.show_error(EXTENSIONS_INSTALL_UNSUCCESFUL)
        return
    if result:
        self.show_info(EXTENSIONS_INSTALL_SUCCESFUL + result)
    else:
        self.show_error(EXTENSIONS_INSTALL_UNSUCCESFUL)


def on_menu_file_export_explorer_actionlist(self, event) -> None:
    del event
    if not self.is_save_not_ok():
        menu_file_export_explorer(self, create_phatch_explorer_action, self.filename)


def on_menu_file_export_explorer_recent(self, event) -> None:
    del event
    menu_file_export_explorer(self, create_phatch_recent_explorer_action)


def on_menu_file_export_explorer_inspector(self, event) -> None:
    del event
    menu_file_export_explorer(self, create_phatch_inspect_explorer_action)


def on_menu_file_export_explorer_remove(self, event) -> None:
    del event
    try:
        remove_phatch_explorer_actions(self.filename)
    except ExplorerVerbError:
        self.show_error(EXTENSIONS_INSTALL_UNSUCCESFUL)
        return
    self.show_info(EXTENSIONS_UNINSTALL)


def install_menu_item(self, menu, name, label, tooltip="", style=None):
    if style is None:
        style = importlib.import_module("wx").ITEM_NORMAL
    method = globals()["on_" + name]
    return self.install_menu_item(menu, name, label, method, tooltip, style)


def install(self) -> None:
    entries = (
        (
            "menu_file_export_explorer_remove",
            ct.INTEGRATE_PHATCH_REMOVE % "Windows Explore&r",
        ),
        (
            "menu_file_export_explorer_inspector",
            ct.INTEGRATE_PHATCH_INSPECTOR % "Windows Explore&r",
        ),
        (
            "menu_file_export_explorer_recent",
            ct.INTEGRATE_PHATCH_RECENT % "Windows &Explorer",
        ),
    )
    for name, label in entries:
        install_menu_item(self, self.menu_file_export, name, label)
    explorer_action = install_menu_item(
        self,
        self.menu_file_export,
        "menu_file_export_explorer_actionlist",
        ct.INTEGRATE_PHATCH_ACTIONLIST % "&Windows Explorer",
    )
    self.menu_item.append((self.menu_file_export, [explorer_action]))
    self.menu_file_export.InsertSeparator(4)
    install_menu_item(
        self,
        self.menu_file_export,
        "menu_file_export_droplet_inspector",
        ct.DROPLET_PHATCH_INSPECTOR,
    )
    install_menu_item(
        self,
        self.menu_file_export,
        "menu_file_export_droplet_recent",
        ct.DROPLET_PHATCH_RECENT,
    )
    droplet_action = install_menu_item(
        self,
        self.menu_file_export,
        "menu_file_export_droplet_actionlist",
        ct.DROPLET_PHATCH_ACTIONLIST,
    )
    self.menu_item.append((self.menu_file_export, [droplet_action]))
    self.menu_file_export.InsertSeparator(3)
