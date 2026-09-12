from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import ClassVar, cast

import pytest

from phatch.core.action_registry import (
    ActionCatalogSources,
    ActionRegistryBuildFailure,
    ActionRegistryBuildSuccess,
    build_action_registry,
)
from phatch.core.execution_types import IssueStage


class PluginModule(ModuleType):
    Action: type


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


def plugin(module_name: str, action: type) -> ModuleType:
    module = PluginModule(module_name)
    module.Action = action
    return module


class MissingActionOperations:
    label = "Incomplete"
    tags: tuple[str, ...] = ()
    metadata: tuple[str, ...] = ()
    valid_last = True

    def __init__(self) -> None:
        self._fields = {}

    def load(self, fields: dict[str, str]) -> list[str]:
        return []

    def is_enabled(self) -> bool:
        return True


class SignatureActionBase:
    tags: tuple[str, ...] = ()
    metadata: tuple[str, ...] = ()
    valid_last = False
    constructions = 0

    def __init__(self) -> None:
        type(self).constructions += 1
        self._fields: dict[str, str] = {}

    def is_overwrite_existing_images_forced(self) -> bool:
        return False


class WrongLoadSignatureAction(SignatureActionBase):
    label = "Wrong load"

    def load(self) -> list[str]:
        return []

    def is_enabled(self) -> bool:
        return True


class WrongEnabledSignatureAction(SignatureActionBase):
    label = "Wrong enabled"

    def load(self, fields: dict[str, str]) -> list[str]:
        return []

    def is_enabled(self, unexpected: bool) -> bool:
        return unexpected


def test_labeled_class_missing_action_operations_is_rejected() -> None:
    result = build_action_registry(
        ActionCatalogSources(built_in=(Path("incomplete.py"),), user=()),
        lambda module_name: plugin(module_name, MissingActionOperations),
    )

    assert isinstance(result, ActionRegistryBuildFailure)
    assert result.issues[0].stage is IssueStage.PLUGIN_IMPORT
    assert result.issues[0].action_label == "Incomplete"
    assert result.issues[0].details is not None
    assert "is_overwrite_existing_images_forced" in result.issues[0].details


@pytest.mark.parametrize(
    "action",
    [WrongLoadSignatureAction, WrongEnabledSignatureAction],
)
def test_malformed_action_method_signature_is_rejected_before_construction(
    action,
) -> None:
    action.constructions = 0

    result = build_action_registry(
        ActionCatalogSources(built_in=(Path("malformed.py"),), user=()),
        lambda module_name: plugin(module_name, action),
    )

    assert isinstance(result, ActionRegistryBuildFailure)
    assert result.issues[0].stage is IssueStage.PLUGIN_IMPORT
    assert action.constructions == 0


def test_runtime_error_during_import_is_structured() -> None:
    def failing_importer(module_name: str) -> ModuleType:
        raise RuntimeError(f"failed to execute {module_name}")

    result = build_action_registry(
        ActionCatalogSources(built_in=(Path("broken.py"),), user=()),
        failing_importer,
    )

    assert isinstance(result, ActionRegistryBuildFailure)
    assert result.issues[0].stage is IssueStage.PLUGIN_IMPORT
    assert result.issues[0].details == (
        "RuntimeError: failed to execute actions.broken"
    )


class OperatingSystemFailureAction(ValidAction):
    label = "OS Failure"

    def __init__(self) -> None:
        raise OSError("resource unavailable")


def test_os_error_during_construction_is_structured() -> None:
    result = build_action_registry(
        ActionCatalogSources(built_in=(Path("os_failure.py"),), user=()),
        lambda module_name: plugin(module_name, OperatingSystemFailureAction),
    )

    assert isinstance(result, ActionRegistryBuildFailure)
    assert result.issues[0].stage is IssueStage.ACTION_INITIALIZATION
    assert result.issues[0].details == "OSError: resource unavailable"


class AlphaAction(ValidAction):
    label = "Alpha"

    def __init__(self) -> None:
        self._fields = {}


class ZuluAction(ValidAction):
    label = "Zulu"

    def __init__(self) -> None:
        self._fields = {}


class FieldFake:
    def __init__(self) -> None:
        self.value = "default"

    def get_as_string(self) -> str:
        return self.value

    def set_as_string(self, value: str) -> None:
        self.value = value


class StatefulFieldsAction(ValidAction):
    label = "Stateful"

    def __init__(self) -> None:
        self._fields = {"value": FieldFake()}


class MutableDefaultsAction:
    label = "Mutable Defaults"
    valid_last = False
    tags: ClassVar[list[str]] = ["tag"]
    metadata: ClassVar[list[str]] = ["metadata"]
    tags_hidden: ClassVar[list[str]] = ["hidden"]
    exe: ClassVar[dict[str, str]] = {"tool": "path"}
    cache: ClassVar[dict[str, str]] = {"value": "cached"}

    def __init__(self) -> None:
        self._fields = {}
        self.__dict__["tags"] = list(type(self).tags)
        self.__dict__["metadata"] = list(type(self).metadata)
        self.__dict__["tags_hidden"] = list(type(self).tags_hidden)
        self.__dict__["exe"] = dict(type(self).exe)
        self.__dict__["cache"] = dict(type(self).cache)

    def load(self, fields: dict[str, str]) -> list[str]:
        return []

    def is_enabled(self) -> bool:
        return True

    def is_overwrite_existing_images_forced(self) -> bool:
        return False


def test_registry_preserves_plugin_owned_mutable_state() -> None:
    result = build_action_registry(
        ActionCatalogSources(built_in=(Path("mutable.py"),), user=()),
        lambda module_name: plugin(module_name, MutableDefaultsAction),
    )
    assert isinstance(result, ActionRegistryBuildSuccess)

    first = result.registry.create("Mutable Defaults")
    second = result.registry.create("Mutable Defaults")
    assert isinstance(first, MutableDefaultsAction)
    assert isinstance(second, MutableDefaultsAction)
    first = cast(MutableDefaultsAction, first)
    second = cast(MutableDefaultsAction, second)

    first.tags.append("changed")
    first.metadata.append("changed")
    first.tags_hidden.append("changed")
    first.exe["changed"] = "value"
    first.cache["changed"] = "value"

    assert second.tags == ["tag"]
    assert second.metadata == ["metadata"]
    assert second.tags_hidden == ["hidden"]
    assert second.exe == {"tool": "path"}
    assert second.cache == {"value": "cached"}


def test_registry_fields_returns_fresh_action_state() -> None:
    result = build_action_registry(
        ActionCatalogSources(built_in=(Path("stateful.py"),), user=()),
        lambda module_name: plugin(module_name, StatefulFieldsAction),
    )
    assert isinstance(result, ActionRegistryBuildSuccess)

    first = result.registry.fields["Stateful"]["value"]
    first.set_as_string("changed")

    assert result.registry.fields["Stateful"]["value"].get_as_string() == "default"


def test_independent_registries_do_not_share_catalog_mutation() -> None:
    sources = ActionCatalogSources(built_in=(Path("action.py"),), user=())
    alpha_result = build_action_registry(
        sources, lambda module_name: plugin(module_name, AlphaAction)
    )
    zulu_result = build_action_registry(
        sources, lambda module_name: plugin(module_name, ZuluAction)
    )

    assert isinstance(alpha_result, ActionRegistryBuildSuccess)
    assert isinstance(zulu_result, ActionRegistryBuildSuccess)
    assert alpha_result.registry.labels() == ("Alpha",)
    assert zulu_result.registry.labels() == ("Zulu",)
    assert not hasattr(alpha_result.registry.factories, "__setitem__")
