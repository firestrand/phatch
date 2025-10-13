import builtins

import pytest

from phatch.core import api, config
from phatch.services.action_list import ActionListService


if "_" not in builtins.__dict__:
    builtins.__dict__["_"] = str


@pytest.fixture(scope="module", autouse=True)
def _init_phatch_runtime():
    """Initialise configuration and action registry once for the workflow tests."""

    config.init_config_paths()
    api.init()


@pytest.fixture
def saved_actionlist_path(tmp_path):
    border = api.ACTIONS["Border"]()
    save = api.ACTIONS["Save"]()
    actionlist_path = tmp_path / "workflow.phatch"

    payload = ActionListService().save(
        str(actionlist_path),
        "Test from GUI workflow",
        [border, save],
    )
    return actionlist_path, payload


def test_action_list_round_trip(saved_actionlist_path):
    path, payload = saved_actionlist_path

    assert path.exists()
    assert payload["description"] == "Test from GUI workflow"
    assert "actions" in payload and len(payload["actions"]) == 2

    loaded = ActionListService(safe_mode_checker=lambda: False).load(str(path))

    assert loaded.description == "Test from GUI workflow"
    assert len(loaded.actions) == 2
    assert loaded.data.get("format_version") is not None


def test_action_list_loads_with_safe_mode(saved_actionlist_path):
    path, _payload = saved_actionlist_path

    loaded = ActionListService(safe_mode_checker=lambda: True).load(str(path))

    # No warning means safe mode accepts the action list
    assert loaded.warning == ""
