from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from phatch.lib import formField
from phatch.services.field_presentation_data import (
    ACTION_FIELD_LABELS,
    PERCENTAGE_BASES,
)
from phatch.services.field_presentation_help import FIELD_HELP
from phatch.services.field_presentation_types import (
    CommitTrigger,
    EditorFamily,
    FieldPresentation,
    FieldPresentationError,
    PercentageBasis,
    PresetBehavior,
    ValidationKind,
)


@dataclass(frozen=True, slots=True)
class _FieldRule:
    editor: EditorFamily
    validation: ValidationKind
    strict: bool = False


_FIELD_RULE_GROUPS: Final = (
    (
        _FieldRule(EditorFamily.TEXT, ValidationKind.TEXT),
        ("CharField", "NotEmptyCharField", "FileNameField"),
    ),
    (
        _FieldRule(EditorFamily.NUMBER, ValidationKind.INTEGER),
        ("IntegerField", "DpiField"),
    ),
    (
        _FieldRule(EditorFamily.NUMBER, ValidationKind.POSITIVE_INTEGER),
        ("PositiveIntegerField",),
    ),
    (
        _FieldRule(EditorFamily.NUMBER, ValidationKind.POSITIVE_NON_ZERO_INTEGER),
        ("PositiveNonZeroIntegerField",),
    ),
    (_FieldRule(EditorFamily.NUMBER, ValidationKind.FLOAT), ("FloatField",)),
    (
        _FieldRule(EditorFamily.NUMBER, ValidationKind.POSITIVE_FLOAT),
        ("PositiveFloatField",),
    ),
    (
        _FieldRule(EditorFamily.NUMBER, ValidationKind.POSITIVE_NON_ZERO_FLOAT),
        ("PositiveNonZeroFloatField",),
    ),
    (_FieldRule(EditorFamily.BOOLEAN, ValidationKind.BOOLEAN), ("BooleanField",)),
    (
        _FieldRule(EditorFamily.CHOICE, ValidationKind.CHOICE, strict=True),
        (
            "ChoiceField",
            "ImageTypeField",
            "ImageReadTypeField",
            "ImageWriteTypeField",
            "ImageModeField",
            "ImageEffectField",
            "ImageFilterField",
            "ImageResampleField",
            "ImageResampleAutoField",
            "ImageTransposeField",
            "OptionalTransposeField",
            "OrientationField",
            "AlignHorizontalField",
            "AlignVerticalField",
            "RankSizeField",
            "TiffCompressionField",
        ),
    ),
    (
        _FieldRule(EditorFamily.FOLDER, ValidationKind.TEXT, strict=True),
        ("FolderField",),
    ),
    (
        _FieldRule(EditorFamily.FILE, ValidationKind.FILE),
        ("FileField", "EmptyFileField", "CsvFileField"),
    ),
    (
        _FieldRule(EditorFamily.FILE, ValidationKind.READ_FILE),
        ("ReadFileField", "GeoReadFileField", "DictionaryReadFileField"),
    ),
    (_FieldRule(EditorFamily.FONT_FILE, ValidationKind.READ_FILE), ("FontFileField",)),
    (
        _FieldRule(EditorFamily.IMAGE_FILE, ValidationKind.READ_FILE),
        (
            "ImageReadFileField",
            "ImageDictionaryReadFileField",
            "HighlightFileField",
            "MaskFileField",
            "WatermarkFileField",
        ),
    ),
    (
        _FieldRule(EditorFamily.IMAGE_CATALOG, ValidationKind.READ_FILE),
        (
            "ImageDictionaryField",
            "PerspectiveField",
            "BlenderField",
            "BlenderObjectField",
            "BlenderRotationField",
        ),
    ),
    (_FieldRule(EditorFamily.TEXT, ValidationKind.COMMAND), ("CommandLineField",)),
    (_FieldRule(EditorFamily.TEXT, ValidationKind.EXIF_IPTC), ("ExifItpcField",)),
    (_FieldRule(EditorFamily.COLOR, ValidationKind.COLOR), ("ColorField",)),
    (_FieldRule(EditorFamily.PIXEL, ValidationKind.INTEGER), ("PixelField",)),
    (_FieldRule(EditorFamily.FILE_SIZE, ValidationKind.INTEGER), ("FileSizeField",)),
    (_FieldRule(EditorFamily.SLIDER, ValidationKind.INTEGER), ("SliderField",)),
    (
        _FieldRule(EditorFamily.FLOAT_SLIDER, ValidationKind.FLOAT),
        ("FloatSliderField",),
    ),
)
_FIELD_RULES: Final = {
    class_name: rule
    for rule, class_names in _FIELD_RULE_GROUPS
    for class_name in class_names
}
_PIXEL_UNITS: Final = ("px", "%", "cm", "mm", "inch")
_FILE_SIZE_UNITS: Final = ("bt", "kb", "mb", "gb")


def descriptor_keys() -> frozenset[tuple[str, str]]:
    return frozenset(
        (action_id, field_id)
        for action_id, fields in ACTION_FIELD_LABELS.items()
        for field_id, _label in fields
    )


def _field_choices(field: formField.Field) -> tuple[str, ...]:
    choices = getattr(field, "choices", ())
    if not isinstance(choices, Sequence) or isinstance(choices, str):
        return ()
    return tuple(str(choice) for choice in choices)


def describe_field(
    action_id: str,
    field_id: str,
    label: str,
    field: formField.Field,
) -> FieldPresentation:
    expected = dict(ACTION_FIELD_LABELS.get(action_id, ())).get(field_id)
    if expected is None or expected != label:
        raise FieldPresentationError(action_id, field_id, "unknown descriptor mapping")
    class_name = type(field).__name__
    rule = _FIELD_RULES.get(class_name)
    if rule is None:
        raise FieldPresentationError(
            action_id, field_id, f"unsupported field class {class_name}"
        )
    choices = _field_choices(field)
    if rule.strict and not choices:
        raise FieldPresentationError(action_id, field_id, "strict choice has no values")
    preset = (
        PresetBehavior.STRICT
        if rule.strict
        else (PresetBehavior.EDITABLE if choices else PresetBehavior.NONE)
    )
    units = (
        _PIXEL_UNITS
        if rule.editor is EditorFamily.PIXEL
        else (_FILE_SIZE_UNITS if rule.editor is EditorFamily.FILE_SIZE else ())
    )
    basis_name = PERCENTAGE_BASES.get((action_id, field_id))
    if rule.editor is EditorFamily.PIXEL and basis_name is None:
        raise FieldPresentationError(action_id, field_id, "missing percentage basis")
    basis = PercentageBasis.NONE if basis_name is None else PercentageBasis(basis_name)
    help_text = FIELD_HELP.get(label.strip())
    if help_text is None:
        raise FieldPresentationError(action_id, field_id, "missing translated help")
    commit = (
        CommitTrigger.ON_CHANGE
        if preset is PresetBehavior.STRICT or rule.editor is EditorFamily.BOOLEAN
        else CommitTrigger.ON_CONFIRM
    )
    return FieldPresentation(
        action_id,
        field_id,
        label,
        rule.editor,
        preset,
        choices,
        units,
        f"field_help.{action_id}.{field_id}",
        help_text,
        commit,
        rule.validation,
        basis,
    )


def describe_action_fields(
    action_id: str,
    fields: Mapping[str, formField.Field],
) -> Mapping[str, FieldPresentation]:
    expected = ACTION_FIELD_LABELS.get(action_id)
    if expected is None:
        raise FieldPresentationError(action_id, "*", "unknown action descriptor")
    visible = {label: field for label, field in fields.items() if field.visible}
    expected_labels = {label for _field_id, label in expected}
    missing = sorted(expected_labels - visible.keys())
    extra = sorted(visible.keys() - expected_labels)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"extra {', '.join(extra)}")
        raise FieldPresentationError(action_id, "*", "; ".join(details))
    return MappingProxyType(
        {
            field_id: describe_field(action_id, field_id, label, visible[label])
            for field_id, label in expected
        }
    )
