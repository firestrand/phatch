from __future__ import annotations

import importlib
import inspect
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Protocol, TypeAlias, runtime_checkable

from phatch.core.execution_ports import Action
from phatch.core.execution_types import ExecutionIssue, IssueSeverity, IssueStage
from phatch.core.plugin_context import PluginContext, default_plugin_context


class RegistryField(Protocol):
    def get_as_string(self) -> str: ...

    def set_as_string(self, value: str) -> None: ...


@runtime_checkable
class RegisteredAction(Action, Protocol):
    @property
    def _fields(self) -> Mapping[str, RegistryField]: ...

    def load(self, fields: Mapping[str, str]) -> list[str]: ...

    def is_enabled(self) -> bool: ...

    def is_overwrite_existing_images_forced(self) -> bool: ...


class ActionFactory(Protocol):
    def __call__(self, **options: PluginContext) -> RegisteredAction: ...


class ModuleImporter(Protocol):
    def __call__(self, module_name: str) -> ModuleType: ...


FieldCollection: TypeAlias = Mapping[str, RegistryField]


@dataclass(frozen=True, slots=True)
class ActionCatalogSources:
    built_in: tuple[Path, ...]
    user: tuple[Path, ...]
    action_attribute: str = "Action"
    built_in_package: str = "actions"


@dataclass(frozen=True, slots=True)
class ImmutableActionRegistry:
    _factories: Mapping[str, ActionFactory]
    _sources: Mapping[str, Path]
    _field_catalog: Mapping[str, FieldCollection]
    _plugin_context: PluginContext = field(default_factory=default_plugin_context)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_factories", MappingProxyType(dict(self._factories)))
        object.__setattr__(self, "_sources", MappingProxyType(dict(self._sources)))
        object.__setattr__(
            self,
            "_field_catalog",
            MappingProxyType(
                {
                    label: MappingProxyType(dict(fields))
                    for label, fields in self._field_catalog.items()
                }
            ),
        )

    def labels(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))

    def create(self, label: str) -> RegisteredAction | ExecutionIssue:
        factory = self._factories.get(label)
        if factory is None:
            return ExecutionIssue(
                stage=IssueStage.ACTION_INITIALIZATION,
                severity=IssueSeverity.ERROR,
                message=f"Action '{label}' is not registered.",
                action_label=label,
                details="Choose one of the registered action labels.",
            )
        try:
            return construct_action(factory, self._plugin_context)
        except Exception as error:
            return ExecutionIssue(
                stage=IssueStage.ACTION_INITIALIZATION,
                severity=IssueSeverity.ERROR,
                message=f"Could not create action '{label}'.",
                source=self._sources[label],
                action_label=label,
                details=f"{type(error).__name__}: {error}",
            )

    def instantiate(self, label: str) -> RegisteredAction:
        factory = self._factories[label]
        return construct_action(factory, self._plugin_context)

    @property
    def factories(self) -> Mapping[str, ActionFactory]:
        return self._factories

    @property
    def fields(self) -> Mapping[str, FieldCollection]:
        return MappingProxyType(
            {
                label: MappingProxyType(
                    {name: deepcopy(value) for name, value in fields.items()}
                )
                for label, fields in self._field_catalog.items()
            }
        )


def construct_action(
    factory: ActionFactory, plugin_context: PluginContext
) -> RegisteredAction:
    parameters = inspect.signature(factory).parameters.values()
    accepts_context = any(
        parameter.name == "plugin_context"
        or parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )
    if accepts_context:
        return factory(plugin_context=plugin_context)
    return factory()


def _action_signature_error(candidate: type) -> str | None:
    operations = [("load", ({},)), ("is_enabled", ())]
    if bool(getattr(candidate, "valid_last", False)) or "file" in getattr(
        candidate, "tags", ()
    ):
        operations.append(("is_overwrite_existing_images_forced", ()))
    for name, arguments in operations:
        try:
            inspect.signature(getattr(candidate, name)).bind(None, *arguments)
        except (AttributeError, TypeError, ValueError):
            return f"'{name}' cannot be called with the required arguments"
    return None


@dataclass(frozen=True, slots=True)
class ActionRegistryBuildSuccess:
    registry: ImmutableActionRegistry


@dataclass(frozen=True, slots=True)
class ActionRegistryBuildFailure:
    issues: tuple[ExecutionIssue, ...]


ActionRegistryBuildResult: TypeAlias = (
    ActionRegistryBuildSuccess | ActionRegistryBuildFailure
)


@dataclass(frozen=True, slots=True)
class ActionRegistryBuildError(RuntimeError):
    issues: tuple[ExecutionIssue, ...]

    def __str__(self) -> str:
        return "; ".join(issue.message for issue in self.issues)


def build_action_registry(
    sources: ActionCatalogSources,
    importer: ModuleImporter | None = None,
    *,
    plugin_context: PluginContext | None = None,
) -> ActionRegistryBuildResult:
    context = default_plugin_context() if plugin_context is None else plugin_context
    load_module = importlib.import_module if importer is None else importer
    plugin_sources = tuple(
        (path, f"{sources.built_in_package}.{path.stem}") for path in sources.built_in
    ) + tuple((path, path.stem) for path in sources.user)
    factories: dict[str, ActionFactory] = {}
    source_by_label: dict[str, Path] = {}
    fields_by_label: dict[str, FieldCollection] = {}
    issues: list[ExecutionIssue] = []

    for source, module_name in plugin_sources:
        try:
            module = load_module(module_name)
        except Exception as error:
            issues.append(
                ExecutionIssue(
                    stage=IssueStage.PLUGIN_IMPORT,
                    severity=IssueSeverity.ERROR,
                    message=f"Could not import action plugin '{module_name}'.",
                    source=source,
                    details=f"{type(error).__name__}: {error}",
                )
            )
            continue

        candidate = vars(module).get(sources.action_attribute)
        if candidate is None:
            continue
        if not isinstance(candidate, type):
            issues.append(
                ExecutionIssue(
                    stage=IssueStage.PLUGIN_IMPORT,
                    severity=IssueSeverity.ERROR,
                    message=(
                        f"Action plugin '{module_name}' exposes an invalid factory."
                    ),
                    source=source,
                    details=(
                        f"'{sources.action_attribute}' must be a zero-argument class."
                    ),
                )
            )
            continue

        label = getattr(candidate, "label", None)
        if not isinstance(label, str) or not label:
            issues.append(
                ExecutionIssue(
                    stage=IssueStage.PLUGIN_IMPORT,
                    severity=IssueSeverity.ERROR,
                    message=f"Action plugin '{module_name}' has an invalid label.",
                    source=source,
                    details="The action label must be a non-empty string.",
                )
            )
            continue
        if (signature_error := _action_signature_error(candidate)) is not None:
            issues.append(
                ExecutionIssue(
                    stage=IssueStage.PLUGIN_IMPORT,
                    severity=IssueSeverity.ERROR,
                    message=f"Action plugin '{module_name}' has an invalid contract.",
                    source=source,
                    action_label=label,
                    details=signature_error,
                )
            )
            continue
        try:
            action = construct_action(candidate, context)
            fields = getattr(action, "_fields", None)
        except Exception as error:
            issues.append(
                ExecutionIssue(
                    stage=IssueStage.ACTION_INITIALIZATION,
                    severity=IssueSeverity.ERROR,
                    message=(
                        f"Could not initialize action '{label}' from '{module_name}'."
                    ),
                    source=source,
                    action_label=label,
                    details=f"{type(error).__name__}: {error}",
                )
            )
            continue
        if not isinstance(fields, Mapping):
            issues.append(
                ExecutionIssue(
                    stage=IssueStage.ACTION_INITIALIZATION,
                    severity=IssueSeverity.ERROR,
                    message=(
                        f"Could not initialize action '{label}' from '{module_name}'."
                    ),
                    source=source,
                    action_label=label,
                    details="constructed action has no '_fields' mapping",
                )
            )
            continue

        factories[label] = candidate
        source_by_label[label] = source
        fields_by_label[label] = fields

    if issues:
        return ActionRegistryBuildFailure(tuple(issues))
    return ActionRegistryBuildSuccess(
        ImmutableActionRegistry(factories, source_by_label, fields_by_label, context)
    )
