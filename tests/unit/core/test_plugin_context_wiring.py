from __future__ import annotations

from pathlib import Path
from types import ModuleType

from PIL import Image

from phatch.core import api
from phatch.core.action_registry import (
    ActionCatalogSources,
    ActionRegistryBuildSuccess,
    build_action_registry,
)
from phatch.core.execution_types import ExecutionOptions
from phatch.core.plugin_context import PluginContext, default_plugin_context
from phatch.services.action_list import ActionListService
from phatch.services.legacy_actions import LegacyActionAdapter, LegacyActionDependencies
from phatch.services.legacy_execution import apply_actions_to_photos
from tests.unit.core.test_execution_characterization_batch import batch_settings
from tests.unit.core.test_legacy_execution_adapters import InteractionFake
from tests.unit.core.test_legacy_execution_public_api import _configure_real_execution


class ContextAction:
    label = "Context"
    tags: tuple[str, ...] = ()
    metadata: tuple[str, ...] = ()
    valid_last = False

    def __init__(self, *, plugin_context: PluginContext) -> None:
        self.plugin_context = plugin_context
        self._fields = {"context": "field"}

    def load(self, fields: dict[str, str]) -> list[str]:
        return []

    def is_enabled(self) -> bool:
        return True

    def is_overwrite_existing_images_forced(self) -> bool:
        return False


class PluginModule(ModuleType):
    Action: type[ContextAction]


def test_registry_binds_selected_context_during_construction() -> None:
    context = default_plugin_context()
    module = PluginModule("actions.context")
    module.Action = ContextAction
    result = build_action_registry(
        ActionCatalogSources(built_in=(Path("context.py"),), user=()),
        lambda module_name: module,
        plugin_context=context,
    )
    assert isinstance(result, ActionRegistryBuildSuccess)

    action = result.registry.create("Context")

    assert isinstance(action, ContextAction)
    assert action.plugin_context is context


def test_action_list_service_forwards_selected_context() -> None:
    context = default_plugin_context()
    calls: list[tuple[str, dict[str, PluginContext]]] = []

    def fake_open(path: str, **kwargs: PluginContext):
        calls.append(("load", kwargs))
        return {"actions": []}, ""

    def fake_apply(actions, settings, **kwargs: PluginContext) -> None:
        calls.append(("execute", kwargs))

    service = ActionListService(
        open_actionlist=fake_open,
        apply_actions_to_photos=fake_apply,
        safe_mode_checker=lambda: False,
        plugin_context=context,
    )

    service.load("sample.phatch")
    service.execute([], {})

    assert calls == [
        ("load", {"plugin_context": context}),
        ("execute", {}),
    ]


class ContextTrackingAction:
    label = "enabled"
    tags = ("file",)
    metadata: tuple[str, ...] = ()
    valid_last = False

    def __init__(self, plugin_context: PluginContext) -> None:
        self.plugin_context = plugin_context
        self.observed: list[PluginContext] = []

    def bind_plugin_context(self, plugin_context: PluginContext) -> None:
        self.plugin_context = plugin_context

    def init(self) -> None:
        self.observed.append(self.plugin_context)

    def is_enabled(self) -> bool:
        return True

    def is_overwrite_existing_images_forced(self) -> bool:
        return False

    def is_done(self, photo) -> bool:
        return False

    def _get_fields(self):
        return {}

    def dump(self):
        return {}

    def apply(self, photo, settings, cache):
        return photo


def test_explicit_run_context_rebinds_before_initialization() -> None:
    original_context = default_plugin_context()
    selected_context = default_plugin_context()
    action = ContextTrackingAction(original_context)
    run = LegacyActionDependencies(
        {}, InteractionFake(), (action,), selected_context
    ).begin_run(ExecutionOptions(()))

    issue = run.initialize(LegacyActionAdapter(action))

    assert issue is None
    assert action.observed == [selected_context]


def test_legacy_entrypoint_initializes_with_caller_selected_context(
    monkeypatch, tmp_path
) -> None:
    _configure_real_execution(monkeypatch)
    context = default_plugin_context()
    action = ContextTrackingAction(context)
    monkeypatch.setattr(api, "check_actionlist", lambda actions, settings: [action])
    image_path = tmp_path / "photo.png"
    Image.new("RGB", (4, 3)).save(image_path)

    apply_actions_to_photos(
        [action],
        batch_settings(no_save=True),
        [str(image_path)],
    )

    assert action.observed == [context]
