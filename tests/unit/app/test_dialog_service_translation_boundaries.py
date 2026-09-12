from __future__ import annotations

import builtins
import importlib
import subprocess
import sys

import pytest

from phatch.core import cli
from phatch.lib import reverse_translation
from phatch.pyWx import dialog_service


def test_reverse_translation_import_repairs_non_callable_gettext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builtins, "_", None, raising=False)

    reloaded = importlib.reload(reverse_translation)

    assert builtins.__dict__["_"] is str
    assert reloaded._translate("phrase") == "phrase"


def test_cli_and_dialog_work_after_list_data_doctests() -> None:
    script = """
import builtins
import doctest

from phatch.lib import listData

failures, attempted = doctest.testmod(listData)
assert (failures, attempted) == (0, 42)
assert builtins._ is None

from phatch.core.cli import format_cli_description
from phatch.pyWx.dialog_service import _

description = format_cli_description({"name": "phatch"})
assert "Examples:" in description
assert _("message") == "message"
"""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("translator", [None, 7, "not callable"])
def test_translation_boundaries_use_identity_for_non_callable_gettext(
    translator: int | str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builtins, "_", translator, raising=False)

    description = cli.format_cli_description({"name": "phatch"})

    assert "Examples:" in description
    assert dialog_service._("message") == "message"
    assert reverse_translation._translate("phrase") == "phrase"


def test_translation_boundaries_preserve_callable_gettext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        builtins,
        "_",
        lambda message: f"translated:{message}",
        raising=False,
    )

    description = cli.format_cli_description({"name": "phatch"})

    assert "translated:Examples:" in description
    assert dialog_service._("message") == "translated:message"
    assert reverse_translation._translate("phrase") == "translated:phrase"


def test_translation_boundaries_use_identity_when_gettext_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(builtins, "_", raising=False)

    description = cli.format_cli_description({"name": "phatch"})

    assert "Examples:" in description
    assert dialog_service._("message") == "message"
    assert reverse_translation._translate("phrase") == "phrase"
