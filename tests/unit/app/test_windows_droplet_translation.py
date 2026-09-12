from __future__ import annotations

import builtins
import importlib
import sys
from collections.abc import Callable

import pytest

Translator = Callable[[str], str]


def _identity(message: str) -> str:
    return message


def _translated(message: str) -> str:
    return f"translated:{message}"


@pytest.mark.parametrize(
    "states",
    [
        (None, 7, "not callable", _translated, _identity),
        (_identity, _translated, "not callable", 7, None),
    ],
)
def test_droplet_translation_is_independent_of_import_order(
    states: tuple[Translator | int | str | None, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = "Phatch did not succeed to install the requested feature."

    for translator in states:
        monkeypatch.setattr(builtins, "_", translator, raising=False)
        sys.modules.pop("phatch.windows.droplet", None)

        module = importlib.import_module("phatch.windows.droplet")
        reloaded = importlib.reload(module)

        expected = translator(message) if callable(translator) else message
        assert expected == module.EXTENSIONS_INSTALL_UNSUCCESFUL
        assert expected == reloaded.EXTENSIONS_INSTALL_UNSUCCESFUL


def test_droplet_translation_uses_identity_when_gettext_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(builtins, "_", raising=False)
    sys.modules.pop("phatch.windows.droplet", None)

    module = importlib.import_module("phatch.windows.droplet")

    assert (
        module.EXTENSIONS_INSTALL_UNSUCCESFUL
        == "Phatch did not succeed to install the requested feature."
    )
