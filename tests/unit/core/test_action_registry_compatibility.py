from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

from phatch.core import action_registry, api
from phatch.core.action_registry import ActionRegistryBuildError


class PluginModule(ModuleType):
    Action: type


@dataclass(frozen=True, slots=True)
class PluginConstructionError(RuntimeError):
    reason: str

    def __str__(self) -> str:
        return self.reason


class ValidAction:
    tags: tuple[str, ...] = ()
    metadata: tuple[str, ...] = ()
    valid_last = False

    def load(self, fields: dict[str, str]) -> list[str]:
        return []

    def is_enabled(self) -> bool:
        return True

    def is_overwrite_existing_images_forced(self) -> bool:
        return False


class FirstAction(ValidAction):
    label = "First"

    def __init__(self) -> None:
        self._fields = {"first": "field"}


class OverrideAction(ValidAction):
    label = "First"

    def __init__(self) -> None:
        self._fields = {"override": "field"}


class BrokenAction(ValidAction):
    label = "Broken"

    def __init__(self) -> None:
        raise PluginConstructionError("broken fields")


def plugin(module_name: str, action: type) -> ModuleType:
    module = PluginModule(module_name)
    module.Action = action
    return module


def configure_catalog(monkeypatch, modules: dict[str, ModuleType]) -> None:
    monkeypatch.setattr(api.ct, "PHATCH_ACTIONS_PATH", "/built-in")
    monkeypatch.setattr(api.ct, "USER_ACTIONS_PATH", "/user")

    def fake_glob(pattern: str) -> list[str]:
        if pattern == "/built-in/*.py":
            return ["/built-in/first.py"]
        return ["/user/first.py"]

    def fake_import(module_name: str) -> ModuleType:
        return modules[module_name]

    monkeypatch.setattr(api.glob, "glob", fake_glob)
    monkeypatch.setattr(action_registry.importlib, "import_module", fake_import)


def test_legacy_api_signatures_are_preserved() -> None:
    assert str(inspect.signature(api.import_actions)) == "()"
    assert str(inspect.signature(api.import_module)) == "(module, folder=None)"


def test_import_module_delegates_to_importlib_with_legacy_module_names(
    monkeypatch,
) -> None:
    imported = ModuleType("actions.first")
    calls: list[str] = []

    def fake_import(module_name: str) -> ModuleType:
        calls.append(module_name)
        return imported

    monkeypatch.setattr(api.importlib, "import_module", fake_import)

    assert api.import_module("first", "actions") is imported
    assert api.import_module("first") is imported
    assert calls == ["actions.first", "first"]


def test_successful_import_publishes_exact_legacy_projection_shapes(
    monkeypatch,
) -> None:
    configure_catalog(
        monkeypatch,
        {
            "actions.first": plugin("actions.first", FirstAction),
            "first": plugin("first", OverrideAction),
        },
    )

    registry = api.import_actions()

    assert registry.factories["First"] is OverrideAction
    assert type(api.ACTIONS) is dict
    assert type(api.ACTION_LABELS) is list
    assert type(api.ACTION_FIELDS) is dict
    assert {"First": OverrideAction} == api.ACTIONS
    assert api.ACTION_LABELS == ["First"]
    assert api.ACTION_FIELDS == {"First": {"override": "field"}}
    assert isinstance(api.ACTIONS["First"](), OverrideAction)


def test_failed_rebuild_preserves_prior_projection_objects(monkeypatch) -> None:
    prior_actions = {"Old": FirstAction}
    prior_labels = ["Old"]
    prior_fields = {"Old": {"old": "field"}}
    monkeypatch.setattr(api, "ACTIONS", prior_actions)
    monkeypatch.setattr(api, "ACTION_LABELS", prior_labels)
    monkeypatch.setattr(api, "ACTION_FIELDS", prior_fields)
    configure_catalog(
        monkeypatch,
        {
            "actions.first": plugin("actions.first", FirstAction),
            "first": plugin("first", BrokenAction),
        },
    )

    with pytest.raises(ActionRegistryBuildError) as captured:
        api.import_actions()

    assert captured.value.issues[0].source == Path("/user/first.py")
    assert str(captured.value) == ("Could not initialize action 'Broken' from 'first'.")
    assert api.ACTIONS is prior_actions
    assert api.ACTION_LABELS is prior_labels
    assert api.ACTION_FIELDS is prior_fields
