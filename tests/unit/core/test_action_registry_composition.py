from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType

from phatch.core import api
from phatch.core.action_registry import (
    ActionCatalogSources,
    ActionRegistryBuildSuccess,
    ImmutableActionRegistry,
    build_action_registry,
)
from phatch.services.action_list import ActionListService


class PluginModule(ModuleType):
    Action: type[CatalogAction]


class CatalogAction:
    label = "Shared"
    tags: tuple[str, ...] = ()
    metadata: tuple[str, ...] = ()
    valid_last = False
    catalog = "base"

    def __init__(self) -> None:
        self._fields = {}

    def load(self, fields: dict[str, str]) -> list[str]:
        return []

    def _get_fields(self) -> dict[str, str]:
        return self._fields

    def is_enabled(self) -> bool:
        return True


class FirstCatalogAction(CatalogAction):
    catalog = "first"


class SecondCatalogAction(CatalogAction):
    catalog = "second"


def registry_for(action: type[CatalogAction]) -> ImmutableActionRegistry:
    module = PluginModule(action.catalog)
    module.Action = action
    result = build_action_registry(
        ActionCatalogSources(built_in=(Path(f"{action.catalog}.py"),), user=()),
        lambda module_name: module,
    )
    assert isinstance(result, ActionRegistryBuildSuccess)
    return result.registry


def write_action_list(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "format_version": "2.0",
                "description": "isolated",
                "actions": [{"label": "Shared", "fields": {}}],
            }
        ),
        encoding="utf-8",
    )


def test_two_injected_catalogs_load_independently_without_mutating_globals(
    tmp_path: Path,
    monkeypatch,
) -> None:
    action_list = tmp_path / "isolated.phatch"
    write_action_list(action_list)
    compatibility_actions = {"Compatibility": FirstCatalogAction}
    monkeypatch.setattr(api, "ACTIONS", compatibility_actions)
    first = ActionListService(
        registry=registry_for(FirstCatalogAction), safe_mode_checker=lambda: False
    ).load(str(action_list))
    second = ActionListService(
        registry=registry_for(SecondCatalogAction), safe_mode_checker=lambda: False
    ).load(str(action_list))

    assert first.actions[0].catalog == "first"
    assert second.actions[0].catalog == "second"
    assert api.ACTIONS is compatibility_actions
