from __future__ import annotations

from collections.abc import Mapping

import pytest

from phatch.services.preview_dimensions import predict_preview_size
from phatch.services.preview_types import (
    PreviewAdmissionError,
    PreviewErrorCode,
    PreviewSize,
)


class FakeAction:
    def __init__(
        self,
        values: Mapping[str, object],
        fields: Mapping[str, object] | None = None,
    ):
        self._values = values
        self._field_values = fields or {}

    def values(self, info):
        return self._values

    def get_field(self, label, info):
        return self._field_values[label]

    def get_field_size(self, label, info, reference, dpi):
        return self._field_values[label]


@pytest.mark.parametrize(
    ("action_id", "values", "expected"),
    [
        ("contrast", {}, (100, 50)),
        ("canvas", {"new_size": (120, 80)}, (120, 80)),
        ("fit", {"size": (75, 60)}, (75, 60)),
        (
            "border",
            {"method": "Equal for all sides", "border_width": 3},
            (106, 56),
        ),
        (
            "border",
            {"method": "Different", "left": -2, "right": 4, "top": 5, "bottom": 6},
            (104, 61),
        ),
        ("contour", {"size": 2, "offset": 3}, (110, 60)),
        ("crop", {"mode": "All", "all": -3}, (106, 56)),
        (
            "crop",
            {"mode": "Custom", "left": -2, "right": 4, "top": -5, "bottom": 6},
            (98, 49),
        ),
        ("crop", {"mode": "Auto"}, (100, 50)),
        (
            "grid",
            {"grid": (2, 3), "scale": False, "col_line_width": 1, "row_line_width": 2},
            (201, 154),
        ),
        (
            "grid",
            {"grid": (2, 2), "scale": True, "col_line_width": 0, "row_line_width": 0},
            (100, 50),
        ),
        ("mirror", {"direction": "Both"}, (200, 100)),
        ("mirror", {"direction": "Horizontal"}, (200, 50)),
        ("mirror", {"direction": "Vertical"}, (100, 100)),
        ("reflection", {"depth": 20, "gap": 4}, (100, 74)),
        ("rotate", {"expand": False, "angle": 30}, (100, 50)),
        ("rotate", {"expand": True, "angle": 90}, (53, 102)),
        (
            "shadow",
            {"horizontal_offset": -4, "vertical_offset": 5, "border": 2},
            (108, 59),
        ),
    ],
)
def test_predict_preview_size(
    action_id: str,
    values: dict[str, object],
    expected: tuple[int, int],
) -> None:
    result = predict_preview_size(
        action_id, FakeAction(values), {}, PreviewSize(100, 50)
    )
    assert (result.width, result.height) == expected


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        (
            {
                "Resolution": 72,
                "Canvas Width": 200,
                "Canvas Height": 200,
                "Scale Down Only": False,
                "Constrain Proportions": True,
            },
            (200, 100),
        ),
        (
            {
                "Resolution": 72,
                "Canvas Width": 200,
                "Canvas Height": 200,
                "Scale Down Only": False,
                "Constrain Proportions": False,
            },
            (200, 200),
        ),
        (
            {
                "Resolution": 72,
                "Canvas Width": 200,
                "Canvas Height": 200,
                "Scale Down Only": True,
                "Constrain Proportions": True,
            },
            (100, 50),
        ),
    ],
)
def test_predict_scale(
    fields: dict[str, int | bool], expected: tuple[int, int]
) -> None:
    result = predict_preview_size(
        "scale", FakeAction({}, fields), {}, PreviewSize(100, 50)
    )
    assert (result.width, result.height) == expected


@pytest.mark.parametrize(
    ("action_id", "values"),
    [
        ("canvas", {"new_size": "120x80"}),
        ("grid", {"grid": (2, "3"), "scale": False}),
        ("contour", {"size": object(), "offset": 3}),
    ],
)
def test_invalid_dimension_values_raise_typed_admission_error(
    action_id: str,
    values: dict[str, object],
) -> None:
    with pytest.raises(PreviewAdmissionError) as captured:
        predict_preview_size(action_id, FakeAction(values), {}, PreviewSize(100, 50))

    assert captured.value.code is PreviewErrorCode.INVALID_FIELD
