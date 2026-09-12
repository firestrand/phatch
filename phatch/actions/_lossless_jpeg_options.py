from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from core import models
from lib.reverse_translation import _t

from phatch.lib.external_capability_probes import EXIFTRAN, JPEGTRAN

AUTOMATIC = _t("Automatic (use exif orientation)")
COPY = _t("Copy")
CROP = _t("Crop")
ROTATE = _t("Rotate")
FLIP = _t("Flip")
GRAYSCALE = _t("Grayscale")
THUMB = _t("Regenerate thumbnail")
TRANSPOSE = _t("Transpose")
TRANSVERSE = _t("Transverse")
ROTATE_AMOUNTS = ("90 degrees", "180 degrees", "270 degrees")
HORIZONTAL = _t("Horizontal")
VERTICAL = _t("Vertical")
FLIP_DIRECTIONS = (HORIZONTAL, VERTICAL)


class Arguments(list[str]):
    def __str__(self) -> str:
        return " ".join(self)

    def append(self, option: str, *values: str) -> None:
        super().append(f"-{option}")
        self.extend(values)


class Exiftran:
    name = "Exiftran (with exif support)"
    capability = EXIFTRAN
    angles: ClassVar[dict[str, str]] = {
        "90 degrees": "9",
        "180 degrees": "1",
        "270 degrees": "2",
    }
    directions: ClassVar[dict[str, str]] = {HORIZONTAL: "F", VERTICAL: "f"}
    transformations = (AUTOMATIC, ROTATE, FLIP, THUMB, TRANSPOSE, TRANSVERSE)

    def interface(self, action, fields) -> None:
        fields[_t("Transformation")] = action.ChoiceField(
            self.transformations[0], choices=self.transformations
        )
        fields[_t("Angle")] = action.ChoiceField(
            ROTATE_AMOUNTS[0], choices=ROTATE_AMOUNTS
        )
        fields[_t("Direction")] = action.ChoiceField(
            FLIP_DIRECTIONS[0], choices=FLIP_DIRECTIONS
        )
        fields[_t("Preserve Timestamp")] = action.BooleanField(True)
        fields[_t("Show Advanced Options")] = action.BooleanField(False)
        fields[_t("Update JPEG")] = action.BooleanField(True)
        fields[_t("Update Exif Thumbnail")] = action.BooleanField(True)
        fields[_t("Update Orientation Tag")] = action.BooleanField(True)

    def get_relevant_field_labels(self, action) -> list[str]:
        advanced = action.get_field_string("Show Advanced Options") in ("yes", "true")
        relevant = ["Transformation"]
        transformation = action.get_field_string("Transformation")
        field = {ROTATE: "Angle", FLIP: "Direction"}.get(transformation)
        if field is not None:
            relevant.append(field)
        if transformation == THUMB:
            relevant.append("Preserve Timestamp")
        else:
            relevant.append("Show Advanced Options")
            if advanced:
                relevant.extend(
                    ["Update JPEG", "Update Exif Thumbnail", "Update Orientation Tag"]
                )
        return relevant

    def get_command_line_args(self, action, photo) -> Arguments:
        values = action.values(photo.info)
        arguments = Arguments()
        transformation = values["transformation"]
        option = {AUTOMATIC: "a", THUMB: "g", TRANSPOSE: "t", TRANSVERSE: "T"}.get(
            transformation
        )
        if option is not None:
            arguments.append(option)
        elif transformation == ROTATE:
            arguments.append(self.angles[values["angle"]])
        elif transformation == FLIP:
            arguments.append(self.directions[values["direction"]])
        if not values["update_jpeg"]:
            arguments.append("ni")
        if not values["update_exif_thumbnail"]:
            arguments.append("nt")
        if not values["update_orientation_tag"]:
            arguments.append("no")
        if values["preserve_timestamp"]:
            arguments.append("p")
        return arguments

    def build_argv(
        self, executable: Path, action, photo, source: Path, output: Path
    ) -> tuple[str, ...]:
        return (
            str(executable),
            "-i",
            str(source),
            *self.get_command_line_args(action, photo),
            "-o",
            str(output),
        )

    def preserves_timestamp(self, action, photo) -> bool:
        return bool(action.values(photo.info)["preserve_timestamp"])


class Jpegtran:
    name = "Jpegtran (without exif support)"
    capability = JPEGTRAN
    transformations = (COPY, CROP, FLIP, GRAYSCALE, ROTATE, TRANSPOSE, TRANSVERSE)
    copy_choices = (_t("None"), _t("Comments"), _t("All"))
    directions: ClassVar[dict[str, str]] = {
        HORIZONTAL: "horizontal",
        VERTICAL: "vertical",
    }
    angles: ClassVar[dict[str, str]] = {
        "90 degrees": "90",
        "180 degrees": "180",
        "270 degrees": "270",
    }

    def __init__(self) -> None:
        self._crop = models.CropMixin()

    def interface(self, action, fields) -> None:
        fields[_t("Transformation ")] = action.ChoiceField(
            self.transformations[1], choices=self.transformations
        )
        fields[_t("Copy")] = action.ChoiceField(
            self.copy_choices[1], choices=self.copy_choices
        )
        fields[_t("Angle ")] = action.ChoiceField(
            ROTATE_AMOUNTS[0], choices=ROTATE_AMOUNTS
        )
        fields[_t("Direction ")] = action.ChoiceField(
            FLIP_DIRECTIONS[0], choices=FLIP_DIRECTIONS
        )
        self._crop.interface(fields, action)

    def get_relevant_field_labels(self, action) -> list[str]:
        transformation = action.get_field_string("Transformation ")
        fields = {
            COPY: ["Copy"],
            CROP: self._crop.get_relevant_field_labels(action),
            ROTATE: ["Angle "],
            FLIP: ["Direction "],
        }
        return ["Transformation ", *fields.get(transformation, [])]

    def get_command_line_args(self, action, photo) -> Arguments:
        values = self._crop.values(photo.info, action=action)
        arguments = Arguments()
        transformation = values["transformation_"]
        if transformation == COPY:
            arguments.append("copy", values["copy"].lower())
        elif transformation == CROP:
            mode = values["mode"]
            if mode == "Auto":
                bounds = photo.get_flattened_image().getbbox()
                (
                    values["left"],
                    values["top"],
                    values["width"],
                    values["height"],
                ) = bounds
            else:
                if mode == "All":
                    for name in ("left", "top", "right", "bottom"):
                        values[name] = values["all"]
                values["width"], values["height"] = photo.info["size"]
                values["width"] -= values["right"] + values["left"] + 1
                values["height"] -= values["bottom"] + values["top"] + 1
            geometry = "{width}x{height}+{left}+{top}".format_map(values)
            arguments.append("crop", geometry)
        elif transformation == ROTATE:
            arguments.append("rotate", self.angles[values["angle_"]])
        elif transformation == FLIP:
            arguments.append("flip", self.directions[values["direction_"]])
        else:
            arguments.append(transformation.lower())
        return arguments

    def build_argv(
        self, executable: Path, action, photo, source: Path, output: Path
    ) -> tuple[str, ...]:
        return (
            str(executable),
            *self.get_command_line_args(action, photo),
            "-outfile",
            str(output),
            str(source),
        )

    def preserves_timestamp(self, action, photo) -> bool:
        return False


def utilities_dict(*utilities) -> dict[str, Exiftran | Jpegtran]:
    return {utility.name: utility for utility in utilities}
