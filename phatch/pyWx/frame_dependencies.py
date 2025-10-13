"""Factories and defaults for wiring the main wx frame."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, Optional

try:  # pragma: no cover - relies on wxPython
    import wx  # type: ignore
except ImportError:  # pragma: no cover - fallback for headless tests

    class _WxStub:
        class FileDialog:  # type: ignore[dead-code]
            pass

    wx = _WxStub()  # type: ignore

from phatch.services import ActionListService
from phatch.services.action_advisor import ActionListAdvisor
from phatch.services.file_dialogs import FileDialogService
from phatch.services.shell_launcher import ShellLauncher

from .controller import ActionListController
from .dialog_service import DialogService
from .droplet_manager import DropletManager
from .file_menu import FileMenuCoordinator


def _default_shell_frame_factory() -> Any:
    try:  # pragma: no cover - wx shell available at runtime
        from phatch.lib.pyWx import shell

        return shell.Frame
    except ImportError:  # pragma: no cover - headless tests
        return SimpleNamespace


class FrameDependencies:
    """Provides factories used to assemble the GUI frame."""

    def __init__(
        self,
        *,
        controller_factory: Optional[Callable[[Any], ActionListController]] = None,
        action_service_factory: Optional[Callable[[], ActionListService]] = None,
        dialog_service_factory: Optional[Callable[[Any], DialogService]] = None,
        action_advisor_factory: Optional[Callable[[], ActionListAdvisor]] = None,
        file_dialog_service_factory: Optional[Callable[[Any], FileDialogService]] = None,
        droplet_manager_factory: Optional[Callable[..., DropletManager]] = None,
        shell_launcher_factory: Optional[Callable[..., ShellLauncher]] = None,
        file_menu_factory: Optional[Callable[..., FileMenuCoordinator]] = None,
        file_dialog_class: Optional[Any] = None,
        shell_frame_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.controller_factory = controller_factory or ActionListController
        self.action_service_factory = action_service_factory or ActionListService
        self.dialog_service_factory = dialog_service_factory or DialogService
        self.action_advisor_factory = action_advisor_factory or ActionListAdvisor
        self.file_dialog_service_factory = file_dialog_service_factory or (lambda dialog_cls: FileDialogService(dialog_cls))
        self.droplet_manager_factory = droplet_manager_factory or (lambda **kwargs: DropletManager(**kwargs))
        self.shell_launcher_factory = shell_launcher_factory or (lambda **kwargs: ShellLauncher(**kwargs))
        self.file_menu_factory = file_menu_factory or (lambda **kwargs: FileMenuCoordinator(**kwargs))
        self.file_dialog_class = file_dialog_class or getattr(wx, "FileDialog", None)
        self.shell_frame_factory = shell_frame_factory or _default_shell_frame_factory()
