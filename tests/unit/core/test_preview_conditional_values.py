from __future__ import annotations

import pytest

from phatch.actions import text

TEXT_FIELDS = {
    "Text": "<filename>",
    "Font": "",
    "Size": "20%",
    "Color": "#102030",
    "Orientation": "Normal",
    "Position": "Custom",
    "Offset": "5%",
    "Horizontal Offset": "25%",
    "Vertical Offset": "50%",
    "Horizontal Justification": "Left",
    "Vertical Justification": "Top",
}


def test_text_pixel_field_preserves_legacy_serialized_values() -> None:
    action = text.Action()

    invalid = action.load(TEXT_FIELDS)
    dumped = action.dump()["fields"]

    assert invalid == []
    assert type(action._fields["Size"]).__name__ == "PixelField"
    assert dumped == {"__enabled__": "yes", **TEXT_FIELDS}


def test_text_pixel_units_and_source_expression_use_independent_bases() -> None:
    action = text.Action()
    assert action.load(TEXT_FIELDS) == []

    values = action.values(
        {
            "dpi": 72,
            "filename": "known-source.png",
            "size": (40, 20),
        }
    )

    assert values == {
        "text": "known-source.png",
        "font": "",
        "size": 6,
        "color": "#102030",
        "orientation": None,
        "horizontal_offset": 10,
        "vertical_offset": 10,
        "horizontal_justification": "Left",
        "vertical_justification": "Top",
    }


@pytest.mark.parametrize(
    ("position", "expected"),
    [
        ("Center", (20, 10, "Middle", "Middle")),
        ("Bottom Left", (2, -1, "Left", "Bottom")),
        ("Bottom Right", (-2, -1, "Right", "Bottom")),
        ("Top Left", (2, 1, "Left", "Top")),
        ("Top Right", (-2, 1, "Right", "Top")),
        ("Custom", (10, 10, "Left", "Top")),
    ],
)
def test_text_position_modes_include_computed_offsets(
    position: str,
    expected: tuple[int, int, str, str],
) -> None:
    action = text.Action()
    fields = {**TEXT_FIELDS, "Text": "X", "Position": position}
    assert action.load(fields) == []

    values = action.values({"dpi": 72, "filename": "source.png", "size": (40, 20)})

    actual = (
        values["horizontal_offset"],
        values["vertical_offset"],
        values["horizontal_justification"],
        values["vertical_justification"],
    )
    assert actual == expected
