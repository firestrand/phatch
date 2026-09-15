from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Final, Protocol

from phatch.services.preview_types import (
    PreviewAdmissionError,
    PreviewErrorCode,
    PreviewSize,
)


class DimensionAction(Protocol):
    def values(self, info: Mapping[str, object]) -> Mapping[str, object]: ...

    def get_field(self, label: str, info: Mapping[str, object]) -> object: ...

    def get_field_size(
        self,
        label: str,
        info: Mapping[str, object],
        reference: int,
        dpi: object,
    ) -> object: ...


_GROWING_ACTIONS: Final = frozenset(
    {
        "border",
        "canvas",
        "contour",
        "crop",
        "fit",
        "grid",
        "mirror",
        "reflection",
        "rotate",
        "scale",
        "shadow",
    }
)


def predict_preview_size(
    action_id: str,
    action: DimensionAction,
    info: Mapping[str, object],
    before: PreviewSize,
) -> PreviewSize:
    if action_id not in _GROWING_ACTIONS:
        return before
    if action_id == "scale":
        return _scale_size(action, info, before)
    values = action.values(info)
    match action_id:
        case "canvas":
            return _size(values["new_size"])
        case "fit":
            return _size(values["size"])
        case "border":
            return _border_size(values, before)
        case "contour":
            growth = 2 * (_int(values["size"]) + _int(values["offset"]))
            return PreviewSize(before.width + growth, before.height + growth)
        case "crop":
            return _crop_size(values, before)
        case "grid":
            return _grid_size(values, before)
        case "mirror":
            direction = str(values["direction"])
            return PreviewSize(
                before.width * (2 if direction in {"Both", "Horizontal"} else 1),
                before.height * (2 if direction in {"Both", "Vertical"} else 1),
            )
        case "reflection":
            depth = min(before.height, _int(values["depth"]))
            return PreviewSize(
                before.width,
                before.height + _int(values["gap"]) + depth,
            )
        case "rotate":
            if not bool(values["expand"]):
                return before
            angle = math.radians(_float(values["angle"]))
            width = (
                math.ceil(
                    abs(before.width * math.cos(angle))
                    + abs(before.height * math.sin(angle))
                )
                + 2
            )
            height = (
                math.ceil(
                    abs(before.width * math.sin(angle))
                    + abs(before.height * math.cos(angle))
                )
                + 2
            )
            return PreviewSize(width, height)
        case "shadow":
            return PreviewSize(
                before.width
                + abs(_int(values["horizontal_offset"]))
                + 2 * _int(values["border"]),
                before.height
                + abs(_int(values["vertical_offset"]))
                + 2 * _int(values["border"]),
            )
        case _:
            raise PreviewAdmissionError(
                PreviewErrorCode.PIXEL_LIMIT,
                f"preview cannot safely predict {action_id} output size",
                action_id,
            )


def _scale_size(
    action: DimensionAction,
    info: Mapping[str, object],
    before: PreviewSize,
) -> PreviewSize:
    dpi = action.get_field("Resolution", info)
    width = _int(action.get_field_size("Canvas Width", info, before.width, dpi))
    height = _int(action.get_field_size("Canvas Height", info, before.height, dpi))
    down_only = bool(action.get_field("Scale Down Only", info))
    if down_only and width >= before.width and height >= before.height:
        return before
    if bool(action.get_field("Constrain Proportions", info)):
        scale = min(width / before.width, height / before.height)
        return PreviewSize(round(before.width * scale), round(before.height * scale))
    return PreviewSize(width, height)


def _border_size(values: Mapping[str, object], before: PreviewSize) -> PreviewSize:
    if values["method"] == "Equal for all sides":
        sides = [_int(values["border_width"])] * 4
    else:
        sides = [_int(values[name]) for name in ("left", "right", "top", "bottom")]
    left, right, top, bottom = sides
    return PreviewSize(
        before.width + max(left, 0) + max(right, 0),
        before.height + max(top, 0) + max(bottom, 0),
    )


def _grid_size(values: Mapping[str, object], before: PreviewSize) -> PreviewSize:
    columns, rows = _integer_pair(values["grid"])
    width, height = before.width, before.height
    if bool(values["scale"]):
        factor = math.sqrt(columns * rows)
        width, height = int(width / factor), int(height / factor)
    column_line = _int(values["col_line_width"])
    row_line = _int(values["row_line_width"])
    return PreviewSize(
        columns * (width + column_line) - column_line,
        rows * (height + row_line) - row_line,
    )


def _crop_size(values: Mapping[str, object], before: PreviewSize) -> PreviewSize:
    match values["mode"]:
        case "All":
            border = _int(values["all"])
            return PreviewSize(
                before.width - 2 * border,
                before.height - 2 * border,
            )
        case "Custom":
            return PreviewSize(
                before.width - _int(values["left"]) - _int(values["right"]),
                before.height - _int(values["top"]) - _int(values["bottom"]),
            )
        case _:
            return before


def _size(value: object) -> PreviewSize:
    width, height = _integer_pair(value)
    return PreviewSize(width, height)


def _int(value: object) -> int:
    match value:
        case int() | float() | str():
            return int(value)
        case _:
            raise PreviewAdmissionError(
                PreviewErrorCode.INVALID_FIELD,
                "preview dimension value must be numeric",
            )


def _float(value: object) -> float:
    match value:
        case int() | float() | str():
            return float(value)
        case _:
            raise PreviewAdmissionError(
                PreviewErrorCode.INVALID_FIELD,
                "preview dimension value must be numeric",
            )


def _integer_pair(value: object) -> tuple[int, int]:
    match value:
        case (int() as first, int() as second):
            return first, second
        case _:
            raise PreviewAdmissionError(
                PreviewErrorCode.INVALID_FIELD,
                "preview dimension value must be an integer pair",
            )
