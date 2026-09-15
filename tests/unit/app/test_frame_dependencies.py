from collections.abc import Callable
from typing import ParamSpec, TypeVar

import pytest

from phatch.core import api
from phatch.pyWx import frame_dependencies
from phatch.pyWx.dialog_service import DialogService
from phatch.pyWx.frame_dependencies import FrameDependencies, FrameHost
from phatch.services import ActionListService
from tests.unit.core.execution_fakes import ActionFake, ActionRegistryFake

Parameters = ParamSpec("Parameters")
Result = TypeVar("Result")


def override(factory: Callable[Parameters, Result]) -> Callable[Parameters, Result]:
    def wrapped(*args: Parameters.args, **kwargs: Parameters.kwargs) -> Result:
        return factory(*args, **kwargs)

    return wrapped


def test_action_service_factory_can_be_overridden():
    service = ActionListService()

    def factory() -> ActionListService:
        return service

    dependencies = FrameDependencies(action_service_factory=factory)

    assert dependencies.action_service_factory() is service


def test_dialog_service_factory_can_be_overridden():
    class Frame:
        pass

    def factory(frame: FrameHost) -> DialogService:
        return DialogService(frame)

    frame = Frame()
    dependencies = FrameDependencies(dialog_service_factory=factory)

    assert dependencies.dialog_service_factory(frame)._frame is frame


def test_application_dependencies_retain_action_registry():
    registry = ActionRegistryFake(ActionFake())

    dependencies = FrameDependencies.for_action_registry(registry)

    assert dependencies.action_service_factory().registry is registry


def test_all_frame_dependency_factories_can_be_overridden():
    class FileDialog:
        pass

    class ShellFrame:
        def Show(self, show=True):
            return show

    defaults = FrameDependencies()
    controller_factory = override(defaults.controller_factory)
    action_service_factory = override(defaults.action_service_factory)
    dialog_service_factory = override(defaults.dialog_service_factory)
    action_advisor_factory = override(defaults.action_advisor_factory)
    file_dialog_service_factory = override(defaults.file_dialog_service_factory)
    droplet_manager_factory = override(defaults.droplet_manager_factory)
    shell_launcher_factory = override(defaults.shell_launcher_factory)
    file_menu_factory = override(defaults.file_menu_factory)
    preview_dependencies_factory = override(defaults.preview_dependencies_factory)
    action_capabilities_factory = override(defaults.action_capabilities_factory)

    dependencies = FrameDependencies(
        controller_factory=controller_factory,
        action_service_factory=action_service_factory,
        dialog_service_factory=dialog_service_factory,
        action_advisor_factory=action_advisor_factory,
        file_dialog_service_factory=file_dialog_service_factory,
        droplet_manager_factory=droplet_manager_factory,
        shell_launcher_factory=shell_launcher_factory,
        file_menu_factory=file_menu_factory,
        file_dialog_class=FileDialog,
        shell_frame_factory=ShellFrame,
        preview_dependencies_factory=preview_dependencies_factory,
        action_capabilities_factory=action_capabilities_factory,
    )

    assert dependencies.controller_factory is controller_factory
    assert dependencies.action_service_factory is action_service_factory
    assert dependencies.dialog_service_factory is dialog_service_factory
    assert dependencies.action_advisor_factory is action_advisor_factory
    assert dependencies.file_dialog_service_factory is file_dialog_service_factory
    assert dependencies.droplet_manager_factory is droplet_manager_factory
    assert dependencies.shell_launcher_factory is shell_launcher_factory
    assert dependencies.file_menu_factory is file_menu_factory
    assert dependencies.file_dialog_class is FileDialog
    assert dependencies.shell_frame_factory is ShellFrame
    assert dependencies.preview_dependencies_factory is preview_dependencies_factory
    assert dependencies.action_capabilities_factory is action_capabilities_factory


def test_default_preview_dependencies_requires_initialized_action_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api, "ACTIONS", None)

    with pytest.raises(frame_dependencies.PreviewDependenciesUnavailable):
        frame_dependencies._default_preview_dependencies()
