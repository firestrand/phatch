from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from phatch.core import config, ct
from phatch.lib import system
from phatch.lib.capabilities import CapabilityStatus
from phatch.lib.capability_probes import Pywin32CapabilityProbe
from phatch.lib.formField import IMAGE_READ_EXTENSIONS
from phatch.lib.reverse_translation import _translate
from phatch.lib.windows.register import (
    ExplorerVerb,
    ExplorerVerbRegistry,
    ExplorerVerbResult,
    NativeRegistryStore,
)
from phatch.lib.windows.shortcut import ShortcutResult, ShortcutSpec, ShortcutWriter

WX_ENCODING = "utf-8"
EXTENSIONS_INSTALL_SUCCESFUL = _translate(
    "These extensions have been succesfully installed:\n\n"
)
EXTENSIONS_INSTALL_UNSUCCESFUL = _translate(
    "Phatch did not succeed to install the requested feature."
)
EXTENSIONS_UNINSTALL = _translate(
    "Phatch tried to uninstall itself from the Windows Explorer."
)
WIN32_MISSING = _translate(
    "You need to install the Python Win32 Extensions for this feature."
)

RECENT = ct.LABEL_PHATCH_RECENT + "..."
INSPECTOR = ct.TITLE + " " + ct.LABEL_PHATCH_INSPECTOR + "..."
_IMAGE_READ_EXTENSIONS = tuple("." + extension for extension in IMAGE_READ_EXTENSIONS)


@dataclass(frozen=True, slots=True)
class Launcher:
    argv: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DropletLauncherError(RuntimeError):
    reason: str

    def __str__(self) -> str:
        return self.reason


class ShortcutAdapter(Protocol):
    def create(self, spec: ShortcutSpec) -> ShortcutResult: ...


class ExplorerAdapter(Protocol):
    def register(self, verb: ExplorerVerb) -> ExplorerVerbResult: ...

    def remove(self, verb: ExplorerVerb) -> ExplorerVerbResult: ...


def resolve_launcher(
    installed_gui: Path,
    active_interpreter: Path,
    legacy_entry: Path,
) -> Launcher:
    if installed_gui.is_file():
        return Launcher((str(installed_gui),))
    pythonw = active_interpreter.with_name("pythonw.exe")
    if pythonw.is_file() and legacy_entry.is_file():
        return Launcher((str(pythonw), str(legacy_entry)))
    raise DropletLauncherError("Phatch has no usable Windows GUI launcher")


def _launcher() -> Launcher:
    from phatch import phatch as legacy_entrypoint

    interpreter = Path(sys.executable)
    return resolve_launcher(
        interpreter.with_name("phatch-gui.exe"),
        interpreter,
        Path(legacy_entrypoint.__file__),
    )


def _icon() -> Path:
    return Path(config.PATHS["PHATCH_IMAGE_PATH"]) / "phatch.ico"


def win32_missing(frame) -> bool:
    capability = Pywin32CapabilityProbe(platform="win32")()
    if capability.status is CapabilityStatus.AVAILABLE:
        return False
    frame.show_info(WIN32_MISSING)
    return True


def create_droplet(
    name: str,
    arguments: tuple[str, ...],
    folder: str,
    description: str | None = None,
    *,
    writer: ShortcutAdapter | None = None,
    launcher: Launcher | None = None,
    icon: Path | None = None,
) -> None:
    selected_launcher = launcher or _launcher()
    selected_writer = writer or ShortcutWriter()
    selected_writer.create(
        ShortcutSpec(
            destination=Path(folder) / f"{name}.lnk",
            target=Path(selected_launcher.argv[0]),
            arguments=selected_launcher.argv[1:] + arguments,
            description=name if description is None else description,
            icon_path=icon or _icon(),
        )
    )


def create_phatch_droplet(
    actionlist: str,
    folder: str,
    *,
    writer: ShortcutAdapter | None = None,
    launcher: Launcher | None = None,
    icon: Path | None = None,
) -> None:
    name = Path(actionlist).stem
    create_droplet(
        name,
        ("-d", actionlist),
        folder,
        ct.LABEL_PHATCH_ACTIONLIST % system.filename_to_title(name),
        writer=writer,
        launcher=launcher,
        icon=icon,
    )


def create_phatch_recent_droplet(
    folder: str,
    *,
    writer: ShortcutAdapter | None = None,
    launcher: Launcher | None = None,
    icon: Path | None = None,
) -> None:
    create_droplet(
        ct.LABEL_PHATCH_RECENT,
        ("-d", "recent"),
        folder,
        writer=writer,
        launcher=launcher,
        icon=icon,
    )


def create_phatch_inspector_droplet(
    folder: str,
    *,
    writer: ShortcutAdapter | None = None,
    launcher: Launcher | None = None,
    icon: Path | None = None,
) -> None:
    create_droplet(
        ct.LABEL_PHATCH_INSPECTOR,
        ("-n",),
        folder,
        ct.TITLE + " " + ct.LABEL_PHATCH_INSPECTOR,
        writer=writer,
        launcher=launcher,
        icon=icon,
    )


def _registrar() -> ExplorerVerbRegistry:
    return ExplorerVerbRegistry(NativeRegistryStore.create())


def register_phatch(
    verb: ExplorerVerb,
    registrar: ExplorerAdapter | None = None,
) -> str:
    result = (registrar or _registrar()).register(verb)
    return ", ".join(target.lstrip(".") for target in result.targets)


def create_phatch_explorer_action(
    actionlist: str,
    *,
    registrar: ExplorerAdapter | None = None,
    launcher: Launcher | None = None,
    extensions: tuple[str, ...] = _IMAGE_READ_EXTENSIONS,
) -> str:
    selected = launcher or _launcher()
    return register_phatch(
        ExplorerVerb(
            "action-list",
            ct.LABEL_PHATCH_ACTIONLIST % system.filename_to_title(actionlist),
            (*selected.argv, "-d", actionlist),
            extensions,
            True,
            actionlist,
        ),
        registrar,
    )


def create_phatch_recent_explorer_action(
    *,
    registrar: ExplorerAdapter | None = None,
    launcher: Launcher | None = None,
    extensions: tuple[str, ...] = _IMAGE_READ_EXTENSIONS,
) -> str:
    selected = launcher or _launcher()
    return register_phatch(
        ExplorerVerb(
            "recent", RECENT, (*selected.argv, "-d", "recent"), extensions, True
        ),
        registrar,
    )


def create_phatch_inspect_explorer_action(
    *,
    registrar: ExplorerAdapter | None = None,
    launcher: Launcher | None = None,
    extensions: tuple[str, ...] = _IMAGE_READ_EXTENSIONS,
) -> str:
    selected = launcher or _launcher()
    return register_phatch(
        ExplorerVerb("inspector", INSPECTOR, (*selected.argv, "-n"), extensions),
        registrar,
    )


def remove_phatch_explorer_actions(
    actionlist: str,
    *,
    registrar: ExplorerAdapter | None = None,
    extensions: tuple[str, ...] = _IMAGE_READ_EXTENSIONS,
) -> None:
    selected = registrar or _registrar()
    selected.remove(ExplorerVerb("recent", RECENT, (), extensions, True))
    selected.remove(ExplorerVerb("inspector", INSPECTOR, (), extensions))
    selected.remove(ExplorerVerb("action-list", "", (), extensions, True, actionlist))


def menu_file_export_explorer(self, method, *args, **kwargs) -> None:
    from phatch.windows.droplet_menu import menu_file_export_explorer as dispatch

    dispatch(self, method, *args, **kwargs)


def install(self) -> None:
    from phatch.windows.droplet_menu import install as install_menu

    install_menu(self)
