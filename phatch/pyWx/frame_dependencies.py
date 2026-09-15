"""Factories and defaults for wiring the main wx frame."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

try:  # pragma: no cover - relies on wxPython
    import wx
except ImportError:  # pragma: no cover - fallback for headless tests

    class _WxStub:
        class FileDialog:
            pass

    wx = _WxStub()

from phatch.core.action_registry import ImmutableActionRegistry
from phatch.core.execution_ports import ActionRegistry
from phatch.core.user_paths import current_platform
from phatch.external_tools import default_external_tools
from phatch.lib.capabilities import Capability
from phatch.resources.provider import ResourceProvider
from phatch.services import ActionListService
from phatch.services.action_advisor import ActionListAdvisor
from phatch.services.action_schema import RegistrySchemaCatalog
from phatch.services.file_dialogs import FileDialogService
from phatch.services.preview_types import PreviewDependencies
from phatch.services.shell_launcher import ShellLauncher

from .controller import ActionListController
from .controller_tree import ActionTree
from .dialog_service import DialogService
from .droplet_manager import DropletManager
from .file_menu import FileMenuCoordinator


class FrameHost(Protocol):
    pass


class FileDialogClass(Protocol):
    pass


class ShellWindow(Protocol):
    def Show(self, show: bool = True) -> bool: ...


class _ShellFrameStub:
    def __init__(self, *args, **kwargs) -> None:
        del args, kwargs

    def Show(self, show: bool = True) -> bool:
        del show
        return True


@dataclass(frozen=True, slots=True)
class PreviewDependenciesUnavailable(RuntimeError):
    reason: str

    def __str__(self) -> str:
        return self.reason


def _default_shell_frame_factory() -> type[ShellWindow]:
    try:  # pragma: no cover - wx shell available at runtime
        from phatch.lib.pyWx import shell

        return shell.Frame
    except ImportError:  # pragma: no cover - headless tests
        return _ShellFrameStub


@lru_cache(maxsize=1)
def _default_action_capabilities() -> Mapping[str, Capability]:
    tools = default_external_tools()
    return MappingProxyType(
        {str(identifier): probe() for identifier, probe in tools.probes}
    )


def _default_preview_dependencies() -> PreviewDependencies:
    from phatch.core import api

    actions = api.ACTIONS
    action_fields = api.ACTION_FIELDS
    if actions is None or action_fields is None:
        raise PreviewDependenciesUnavailable("the action registry is not initialized")
    registry = ImmutableActionRegistry(
        actions,
        {label: Path("<legacy>") for label in actions},
        action_fields,
    )
    return PreviewDependencies(
        catalog_factory=lambda: RegistrySchemaCatalog(registry),
        resources=ResourceProvider(),
        platform=current_platform(),
    )


class FrameDependencies:
    """Provides factories used to assemble the GUI frame."""

    def __init__(
        self,
        *,
        controller_factory: Callable[[ActionTree], ActionListController] | None = None,
        action_service_factory: Callable[[], ActionListService] | None = None,
        dialog_service_factory: Callable[[FrameHost], DialogService] | None = None,
        action_advisor_factory: Callable[[], ActionListAdvisor] | None = None,
        file_dialog_service_factory: (
            Callable[[type[FileDialogClass]], FileDialogService] | None
        ) = None,
        droplet_manager_factory: Callable[..., DropletManager] | None = None,
        shell_launcher_factory: Callable[..., ShellLauncher] | None = None,
        file_menu_factory: Callable[..., FileMenuCoordinator] | None = None,
        file_dialog_class: type[FileDialogClass] | None = None,
        shell_frame_factory: type[ShellWindow] | None = None,
        preview_dependencies_factory: (Callable[[], PreviewDependencies] | None) = None,
        action_capabilities_factory: (
            Callable[[], Mapping[str, Capability]] | None
        ) = None,
    ) -> None:
        self.controller_factory = controller_factory or ActionListController
        self.action_service_factory = action_service_factory or ActionListService
        self.dialog_service_factory = dialog_service_factory or DialogService
        self.action_advisor_factory = action_advisor_factory or ActionListAdvisor
        self.file_dialog_service_factory = file_dialog_service_factory or (
            lambda dialog_cls: FileDialogService(dialog_cls)
        )
        self.droplet_manager_factory = droplet_manager_factory or (
            lambda **kwargs: DropletManager(**kwargs)
        )
        self.shell_launcher_factory = shell_launcher_factory or (
            lambda **kwargs: ShellLauncher(**kwargs)
        )
        self.file_menu_factory = file_menu_factory or (
            lambda **kwargs: FileMenuCoordinator(**kwargs)
        )
        self.file_dialog_class = file_dialog_class or getattr(wx, "FileDialog", None)
        self.shell_frame_factory = shell_frame_factory or _default_shell_frame_factory()
        self.preview_dependencies_factory = (
            preview_dependencies_factory or _default_preview_dependencies
        )
        self.action_capabilities_factory = (
            action_capabilities_factory or _default_action_capabilities
        )

    @classmethod
    def for_action_registry(cls, registry: ActionRegistry) -> FrameDependencies:
        return cls(action_service_factory=lambda: ActionListService(registry=registry))
