from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, unique


@unique
class EditorFamily(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    FILE = "file"
    FOLDER = "folder"
    FONT_FILE = "font_file"
    IMAGE_FILE = "image_file"
    IMAGE_CATALOG = "image_catalog"
    COLOR = "color"
    PIXEL = "pixel"
    FILE_SIZE = "file_size"
    SLIDER = "slider"
    FLOAT_SLIDER = "float_slider"


@unique
class PresetBehavior(StrEnum):
    NONE = "none"
    STRICT = "strict"
    EDITABLE = "editable"


@unique
class CommitTrigger(StrEnum):
    ON_CHANGE = "on_change"
    ON_CONFIRM = "on_confirm"


@unique
class ValidationKind(StrEnum):
    UNSUPPORTED = "unsupported"
    TEXT = "text"
    INTEGER = "integer"
    POSITIVE_INTEGER = "positive_integer"
    POSITIVE_NON_ZERO_INTEGER = "positive_non_zero_integer"
    FLOAT = "float"
    POSITIVE_FLOAT = "positive_float"
    POSITIVE_NON_ZERO_FLOAT = "positive_non_zero_float"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    FILE = "file"
    READ_FILE = "read_file"
    COMMAND = "command"
    EXIF_IPTC = "exif_iptc"
    COLOR = "color"


@unique
class PercentageBasis(StrEnum):
    NONE = "none"
    WIDTH = "width"
    HEIGHT = "height"
    AVERAGE = "average"
    AXIS = "axis"
    WIDTH_PLUS_HALF_HEIGHT = "width_plus_half_height"


@dataclass(frozen=True, slots=True)
class FieldPresentation:
    action_id: str
    field_id: str
    label_key: str
    editor: EditorFamily
    preset: PresetBehavior
    choices: tuple[str, ...]
    units: tuple[str, ...]
    help_key: str
    help_text: str
    commit_trigger: CommitTrigger
    validation: ValidationKind
    percentage_basis: PercentageBasis


@dataclass(frozen=True, slots=True)
class FieldPresentationError(ValueError):
    action_id: str
    field_id: str
    reason: str

    def __str__(self) -> str:
        return f"{self.action_id}.{self.field_id}: {self.reason}"
