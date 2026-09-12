from __future__ import annotations

import pytest

from phatch.core.windows_names import (
    WindowsNameError,
    windows_collision_key,
    validate_windows_name,
)


@pytest.mark.parametrize(
    "name", ["CON", "con.txt", "PRN .jpg", "LPT9... ", "aux", "NUL.tar.gz"]
)
def test_reserved_dos_device_basenames_are_rejected(name: str) -> None:
    with pytest.raises(WindowsNameError):
        validate_windows_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "COM¹",
        "com².txt",
        "CoM³.tar.gz",
        "LPT¹",
        "lpt².txt",
        "LpT³.tar.gz",
    ],
)
def test_superscript_dos_device_basenames_are_rejected(name: str) -> None:
    with pytest.raises(WindowsNameError):
        validate_windows_name(name)


@pytest.mark.parametrize(
    "name", ["holiday photo.jpg", "雪景.png", f"{'long-' * 80}.jpg"]
)
def test_spaces_unicode_and_long_names_are_supported(name: str) -> None:
    assert validate_windows_name(name) == name


@pytest.mark.parametrize("name", ["trailing. ", "bad?.jpg", "bad\x00.jpg", ""])
def test_invalid_windows_names_are_rejected(name: str) -> None:
    with pytest.raises(WindowsNameError):
        validate_windows_name(name)


def test_collision_key_models_case_and_trailing_dot_space_semantics() -> None:
    assert windows_collision_key("Résumé.JPG") == windows_collision_key("résumé.jpg. ")


@pytest.mark.parametrize(
    "name", ["CONSOLE.txt", "COM0.txt", "LPT10", "NULled", "COM⁰", "LPT⁴"]
)
def test_reserved_name_near_misses_remain_valid(name: str) -> None:
    assert validate_windows_name(name) == name


def test_collision_key_preserves_name_without_mutating_policy_input() -> None:
    name = "Report Final.JPG"

    key = windows_collision_key(name)

    assert key == "report final.jpg"
    assert name == "Report Final.JPG"


def test_collision_key_does_not_expand_sharp_s_to_ascii_letters() -> None:
    assert windows_collision_key("straße.txt") != windows_collision_key("strasse.txt")
