from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from phatch.release_inventory import (
    RuntimeInventory,
    RuntimeInventoryError,
    RuntimeResourceRecord,
)
from scripts import runtime_inventory


def _inventory() -> RuntimeInventory:
    return RuntimeInventory(
        ("phatch.services.preview",),
        (RuntimeResourceRecord("data/example", 3, "abc"),),
        (("action-lists", 1),),
    )


@pytest.mark.parametrize("arguments", [(), ("--json",)])
def test_runtime_inventory_reports_human_and_json_formats(
    arguments: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(runtime_inventory, "collect_runtime_inventory", _inventory)

    assert runtime_inventory.main(arguments) == 0

    output = capsys.readouterr().out
    if arguments:
        assert json.loads(output)["modules"] == ["phatch.services.preview"]
    else:
        assert output == "runtime inventory: 1 modules, 1 required resources\n"


@pytest.mark.parametrize(
    "error", [RuntimeInventoryError("inventory failed"), OSError("disk failed")]
)
def test_runtime_inventory_reports_collection_errors(
    error: RuntimeInventoryError | OSError,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail() -> RuntimeInventory:
        raise error

    monkeypatch.setattr(runtime_inventory, "collect_runtime_inventory", fail)

    assert runtime_inventory.main(()) == 1
    assert str(error) in capsys.readouterr().err


def test_runtime_inventory_script_exits_through_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = Path(runtime_inventory.__file__)
    monkeypatch.setattr(sys, "argv", [str(script), "--help"])

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(script), run_name="__main__")

    assert exit_info.value.code == 0
