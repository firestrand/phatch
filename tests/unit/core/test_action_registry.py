from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

from phatch.core.action_registry import (
    ActionCatalogSources,
    ActionRegistryBuildFailure,
    ActionRegistryBuildSuccess,
    ImmutableActionRegistry,
    build_action_registry,
)
from phatch.core.execution_types import ExecutionIssue, IssueSeverity, IssueStage


class PluginModule(ModuleType):
    Action: type | int


@dataclass(frozen=True, slots=True)
class PluginConstructionError(RuntimeError):
    reason: str

    def __str__(self) -> str:
        return self.reason


class RecordingImporter:
    __slots__ = ("calls", "modules")

    def __init__(self, modules: dict[str, ModuleType]) -> None:
        self.modules = modules
        self.calls: list[str] = []

    def __call__(self, module_name: str) -> ModuleType:
        self.calls.append(module_name)
        try:
            return self.modules[module_name]
        except KeyError as error:
            raise ImportError(f"missing {module_name}") from error


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


def plugin(module_name: str, action: type | None = None) -> ModuleType:
    module = PluginModule(module_name)
    if action is not None:
        module.Action = action
    return module


def successful_registry(
    sources: ActionCatalogSources, importer: RecordingImporter
) -> ImmutableActionRegistry:
    result = build_action_registry(sources, importer)
    assert isinstance(result, ActionRegistryBuildSuccess)
    return result.registry


class AlphaAction(ValidAction):
    label = "Alpha"

    def __init__(self) -> None:
        self._fields = {"alpha": "field"}


class ZuluAction(ValidAction):
    label = "Zulu"

    def __init__(self) -> None:
        self._fields = {"zulu": "field"}


class BuiltInDuplicateAction(ValidAction):
    label = "Duplicate"

    def __init__(self) -> None:
        self._fields = {"origin": "built-in"}


class UserDuplicateAction(ValidAction):
    label = "Duplicate"

    def __init__(self) -> None:
        self._fields = {"origin": "user"}


def test_build_preserves_source_order_and_user_precedence() -> None:
    sources = ActionCatalogSources(
        built_in=(Path("zulu.py"), Path("duplicate.py"), Path("alpha.py")),
        user=(Path("duplicate.py"),),
    )
    importer = RecordingImporter(
        {
            "actions.zulu": plugin("actions.zulu", ZuluAction),
            "actions.duplicate": plugin("actions.duplicate", BuiltInDuplicateAction),
            "actions.alpha": plugin("actions.alpha", AlphaAction),
            "duplicate": plugin("duplicate", UserDuplicateAction),
        }
    )

    registry = successful_registry(sources, importer)

    assert importer.calls == [
        "actions.zulu",
        "actions.duplicate",
        "actions.alpha",
        "duplicate",
    ]
    assert registry.labels() == ("Alpha", "Duplicate", "Zulu")
    assert list(registry.fields) == ["Zulu", "Duplicate", "Alpha"]
    assert registry.factories["Duplicate"] is UserDuplicateAction
    assert registry.fields["Duplicate"] == {"origin": "user"}


def test_duplicate_built_in_label_keeps_last_factory() -> None:
    sources = ActionCatalogSources(
        built_in=(Path("first.py"), Path("second.py")), user=()
    )
    importer = RecordingImporter(
        {
            "actions.first": plugin("actions.first", BuiltInDuplicateAction),
            "actions.second": plugin("actions.second", UserDuplicateAction),
        }
    )

    registry = successful_registry(sources, importer)

    assert tuple(registry.factories) == ("Duplicate",)
    assert registry.factories["Duplicate"] is UserDuplicateAction


def test_helper_module_without_action_is_ignored() -> None:
    sources = ActionCatalogSources(
        built_in=(Path("helper.py"), Path("alpha.py")), user=()
    )
    importer = RecordingImporter(
        {
            "actions.helper": plugin("actions.helper"),
            "actions.alpha": plugin("actions.alpha", AlphaAction),
        }
    )

    registry = successful_registry(sources, importer)

    assert registry.labels() == ("Alpha",)


class MissingLabelAction:
    def __init__(self) -> None:
        self._fields = {}


class EmptyLabelAction:
    label = ""

    def __init__(self) -> None:
        self._fields = {}


class NonStringLabelAction:
    label = 7

    def __init__(self) -> None:
        self._fields = {}


@pytest.mark.parametrize(
    "candidate",
    [MissingLabelAction, EmptyLabelAction, NonStringLabelAction],
)
def test_invalid_action_label_returns_plugin_import_issue(candidate: type) -> None:
    sources = ActionCatalogSources(built_in=(Path("invalid.py"),), user=())
    importer = RecordingImporter(
        {"actions.invalid": plugin("actions.invalid", candidate)}
    )

    result = build_action_registry(sources, importer)

    assert isinstance(result, ActionRegistryBuildFailure)
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.stage is IssueStage.PLUGIN_IMPORT
    assert issue.severity is IssueSeverity.ERROR
    assert issue.source == Path("invalid.py")
    assert issue.message
    assert issue.details


def test_non_class_action_candidate_returns_plugin_import_issue() -> None:
    module = plugin("actions.invalid")
    assert isinstance(module, PluginModule)
    module.Action = 7
    importer = RecordingImporter({"actions.invalid": module})

    result = build_action_registry(
        ActionCatalogSources(built_in=(Path("invalid.py"),), user=()), importer
    )

    assert isinstance(result, ActionRegistryBuildFailure)
    assert result.issues[0].stage is IssueStage.PLUGIN_IMPORT
    assert "factory" in result.issues[0].message.lower()


def test_import_failure_is_structured_and_retains_details() -> None:
    result = build_action_registry(
        ActionCatalogSources(built_in=(Path("broken.py"),), user=()),
        RecordingImporter({}),
    )

    assert isinstance(result, ActionRegistryBuildFailure)
    assert result.issues == (
        ExecutionIssue(
            stage=IssueStage.PLUGIN_IMPORT,
            severity=IssueSeverity.ERROR,
            message="Could not import action plugin 'actions.broken'.",
            source=Path("broken.py"),
            details="ImportError: missing actions.broken",
        ),
    )


class ConstructorFailureAction(ValidAction):
    label = "Broken"

    def __init__(self) -> None:
        raise PluginConstructionError("constructor exploded")


class MissingFieldsAction(ValidAction):
    label = "Missing Fields"


class FailsAfterBuildAction(ValidAction):
    label = "Fails Later"
    constructions = 0

    def __init__(self) -> None:
        type(self).constructions += 1
        if self.constructions > 1:
            raise PluginConstructionError("later construction failed")
        self._fields = {}


@pytest.mark.parametrize(
    ("candidate", "expected_label", "detail"),
    [
        (
            ConstructorFailureAction,
            "Broken",
            "PluginConstructionError: constructor exploded",
        ),
        (
            MissingFieldsAction,
            "Missing Fields",
            "constructed action has no '_fields' mapping",
        ),
    ],
)
def test_field_construction_failure_is_initialization_issue(
    candidate: type, expected_label: str, detail: str
) -> None:
    importer = RecordingImporter(
        {"actions.broken": plugin("actions.broken", candidate)}
    )

    result = build_action_registry(
        ActionCatalogSources(built_in=(Path("broken.py"),), user=()), importer
    )

    assert isinstance(result, ActionRegistryBuildFailure)
    issue = result.issues[0]
    assert issue.stage is IssueStage.ACTION_INITIALIZATION
    assert issue.severity is IssueSeverity.ERROR
    assert issue.action_label == expected_label
    assert issue.details == detail


def test_create_returns_fresh_instances_and_unknown_label_issue() -> None:
    registry = successful_registry(
        ActionCatalogSources(built_in=(Path("alpha.py"),), user=()),
        RecordingImporter({"actions.alpha": plugin("actions.alpha", AlphaAction)}),
    )

    first = registry.create("Alpha")
    second = registry.create("Alpha")
    missing = registry.create("Missing")

    assert isinstance(first, AlphaAction)
    assert isinstance(second, AlphaAction)
    assert first is not second
    assert isinstance(missing, ExecutionIssue)
    assert missing.stage is IssueStage.ACTION_INITIALIZATION
    assert missing.action_label == "Missing"


def test_fields_reuse_build_snapshot_without_reconstructing_plugins() -> None:
    FailsAfterBuildAction.constructions = 0
    registry = successful_registry(
        ActionCatalogSources(built_in=(Path("later.py"),), user=()),
        RecordingImporter(
            {"actions.later": plugin("actions.later", FailsAfterBuildAction)}
        ),
    )

    assert registry.fields["Fails Later"] == {}
    assert registry.fields["Fails Later"] == {}
    assert FailsAfterBuildAction.constructions == 1


def test_create_maps_later_constructor_failure_to_structured_issue() -> None:
    FailsAfterBuildAction.constructions = 0
    registry = successful_registry(
        ActionCatalogSources(built_in=(Path("later.py"),), user=()),
        RecordingImporter(
            {"actions.later": plugin("actions.later", FailsAfterBuildAction)}
        ),
    )

    result = registry.create("Fails Later")

    assert isinstance(result, ExecutionIssue)
    assert result.stage is IssueStage.ACTION_INITIALIZATION
    assert result.source == Path("later.py")
    assert result.details == "PluginConstructionError: later construction failed"
