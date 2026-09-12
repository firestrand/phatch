import builtins
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from phatch.core import ct, translation
from phatch.lib import reverse_translation


def operational_reverse_cache() -> dict[str, str]:
    return translation._r.__globals__["REVERSE"]


def load_ct_for_platform(
    monkeypatch: pytest.MonkeyPatch, platform: str, frozen: bool
) -> ModuleType:
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(sys, "argv", ["/fixture/phatch"])
    if frozen:
        monkeypatch.setattr(sys, "frozen", True, raising=False)
    else:
        monkeypatch.delattr(sys, "frozen", raising=False)
    module_name = f"phatch.core._ct_decisions_{platform}_{frozen}"
    spec = importlib.util.spec_from_file_location(module_name, Path(ct.__file__))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_to_english_short_circuits_on_reverse_cache_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached = "Hello <filename>!"
    monkeypatch.setitem(operational_reverse_cache(), "Bonjour <fichier>!", cached)
    monkeypatch.setattr(
        translation,
        "_expr_to_english",
        lambda _match: pytest.fail("cache hit must preserve rendered expression"),
    )

    assert translation.to_english("Bonjour <fichier>!") == cached


def test_to_english_translates_expression_variables_and_preserves_attributes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(operational_reverse_cache(), "afbeelding", "image")
    monkeypatch.setitem(operational_reverse_cache(), "breedte", "width")

    assert translation.to_english("<afbeelding.breedte>") == "<image.breedte>"


def test_to_local_short_circuits_when_whole_text_has_translation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = "Hello <filename>"
    monkeypatch.setattr(
        builtins, "_", lambda phrase: "Bonjour complet" if phrase == source else phrase
    )
    monkeypatch.setattr(
        translation,
        "_expr_to_local",
        lambda _match: pytest.fail("whole-string translation must win"),
    )

    assert translation.to_local(source) == "Bonjour complet"


def test_to_local_translates_variable_and_preserves_attribute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    translations = {"image": "afbeelding", "width": "breedte"}
    monkeypatch.setattr(builtins, "_", lambda phrase: translations.get(phrase, phrase))

    assert translation.to_local("<image.width>") == "<afbeelding.width>"


def test_to_local_converts_non_string_choice_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builtins, "_", lambda phrase: phrase)

    assert translation.to_local(42) == "42"


def test_translation_module_dictionary_is_not_operational_reverse_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reverse_translation, "REVERSE", {})
    monkeypatch.setattr(translation, "REVERSE", {"local": "module-only"})

    assert translation.to_english("local") == "local"
    assert translation.REVERSE == {"local": "module-only"}


def test_reverse_translation_cache_preserves_lowercase_legacy_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    translations = {
        "True": "Waar",
        "False": "Onwaar",
        "true": "waar",
        "false": "onwaar",
    }
    monkeypatch.setattr(builtins, "_", lambda phrase: translations.get(phrase, phrase))
    monkeypatch.setattr(reverse_translation, "REVERSE", {})

    aliases = [reverse_translation._t(alias) for alias in ct.BOOLEANS]

    assert aliases == ["True", "False", "true", "false"]
    assert reverse_translation.REVERSE == {
        "Waar": "True",
        "Onwaar": "False",
        "waar": "true",
        "onwaar": "false",
    }


def test_reverse_translation_cache_collision_is_last_write_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builtins, "_", lambda _phrase: "same")
    monkeypatch.setattr(reverse_translation, "REVERSE", {})

    reverse_translation._t("first")
    reverse_translation._t("second")

    assert reverse_translation._r("same") == "second"


@pytest.mark.parametrize(
    ("platform", "frozen", "expected_platform", "flags", "command_path"),
    [
        ("win32", True, "windows", (False, True, False), "pythonw.exe"),
        ("linux", False, "linux", (True, False, False), "phatch"),
    ],
)
def test_ct_platform_and_command_decisions(
    platform: str,
    frozen: bool,
    expected_platform: str,
    flags: tuple[bool, bool, bool],
    command_path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as context:
        module = load_ct_for_platform(context, platform, frozen)

    assert expected_platform == module.PLATFORM
    assert flags == (module.LINUX, module.WINDOWS, module.MAC)
    assert command_path == module.COMMAND_PATH
    assert ("/fixture/phatch" if frozen else module.__file__) == module.FILE
    assert set(module.COMMAND) == {"DROP", "RECENT", "INSPECTOR"}
