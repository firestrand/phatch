from __future__ import annotations

import ast
from pathlib import Path

import pytest

from phatch.lib import formField
from phatch.services import field_presentation
from phatch.services.field_presentation import (
    CommitTrigger,
    EditorFamily,
    FieldPresentationError,
    PercentageBasis,
    PresetBehavior,
    ValidationKind,
    describe_action_fields,
    describe_field,
)
from phatch.services.field_presentation_audit import audit_builtin_presentations


@pytest.fixture(scope="module")
def presentation_audit(project_root: Path):
    return audit_builtin_presentations(project_root / "phatch" / "actions")


def test_runtime_inventory_has_every_audited_builtin_field(presentation_audit) -> None:
    assert presentation_audit.action_count == 55
    assert presentation_audit.field_count == 312
    assert presentation_audit.missing_descriptor_keys == ()
    assert presentation_audit.extra_descriptor_keys == ()


def test_runtime_inventory_covers_every_supported_field_alias(
    presentation_audit,
) -> None:
    assert presentation_audit.field_classes == frozenset(
        {
            "BlenderObjectField",
            "BlenderRotationField",
            "BooleanField",
            "CharField",
            "ChoiceField",
            "ColorField",
            "CommandLineField",
            "CsvFileField",
            "DpiField",
            "EmptyFileField",
            "ExifItpcField",
            "FileNameField",
            "FileSizeField",
            "FloatField",
            "FolderField",
            "FontFileField",
            "GeoReadFileField",
            "HighlightFileField",
            "ImageEffectField",
            "ImageFilterField",
            "ImageModeField",
            "ImageResampleAutoField",
            "ImageResampleField",
            "ImageTransposeField",
            "ImageWriteTypeField",
            "IntegerField",
            "MaskFileField",
            "OptionalTransposeField",
            "OrientationField",
            "PerspectiveField",
            "PixelField",
            "PositiveNonZeroIntegerField",
            "RankSizeField",
            "ReadFileField",
            "SliderField",
            "TiffCompressionField",
            "WatermarkFileField",
        }
    )


@pytest.mark.parametrize(
    ("action_id", "field_id", "editor"),
    [
        ("background", "mark", EditorFamily.IMAGE_FILE),
        ("blender", "object", EditorFamily.IMAGE_CATALOG),
        ("blender", "left_page", EditorFamily.FILE),
        ("geek", "command", EditorFamily.TEXT),
        ("geotag", "gps_data_gpx", EditorFamily.FILE),
        ("perspective", "projection", EditorFamily.IMAGE_CATALOG),
        ("save", "jpeg_size_maximum", EditorFamily.FILE_SIZE),
        ("scale", "canvas_width", EditorFamily.PIXEL),
        ("text", "font", EditorFamily.FONT_FILE),
    ],
)
def test_editor_family_is_explicit_for_runtime_aliases(
    presentation_audit, action_id: str, field_id: str, editor: EditorFamily
) -> None:
    assert presentation_audit.descriptors[(action_id, field_id)].editor is editor


def test_choices_distinguish_strict_enums_from_editable_presets(
    presentation_audit,
) -> None:
    descriptors = presentation_audit.descriptors

    assert descriptors[("convert_mode", "mode")].preset is PresetBehavior.STRICT
    assert descriptors[("common", "radius")].preset is PresetBehavior.STRICT
    assert descriptors[("save", "in")].preset is PresetBehavior.STRICT
    assert descriptors[("text", "text")].preset is PresetBehavior.EDITABLE
    assert descriptors[("scale", "canvas_width")].preset is PresetBehavior.EDITABLE
    assert descriptors[("save", "resolution")].preset is PresetBehavior.EDITABLE
    assert descriptors[("time_shift", "seconds")].preset is PresetBehavior.NONE


def test_units_and_crop_percentage_bases_preserve_runtime_geometry(
    presentation_audit,
) -> None:
    descriptors = presentation_audit.descriptors

    assert descriptors[("crop", "all")].percentage_basis is PercentageBasis.AVERAGE
    assert descriptors[("crop", "left")].percentage_basis is PercentageBasis.WIDTH
    assert descriptors[("crop", "right")].percentage_basis is PercentageBasis.WIDTH
    assert descriptors[("crop", "top")].percentage_basis is PercentageBasis.HEIGHT
    assert descriptors[("crop", "bottom")].percentage_basis is PercentageBasis.HEIGHT
    assert descriptors[("crop", "all")].units == ("px", "%", "cm", "mm", "inch")
    assert descriptors[("save", "jpeg_size_maximum")].units == (
        "bt",
        "kb",
        "mb",
        "gb",
    )


def test_every_descriptor_has_machine_key_translatable_help_and_validation(
    presentation_audit, project_root: Path
) -> None:
    source = project_root / "phatch" / "services" / "field_presentation_help.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    marked_help = {
        call.args[0].value
        for call in ast.walk(tree)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "_t"
        and len(call.args) == 1
        and isinstance(call.args[0], ast.Constant)
        and isinstance(call.args[0].value, str)
    }

    for (action_id, field_id), descriptor in presentation_audit.descriptors.items():
        assert descriptor.help_key == f"field_help.{action_id}.{field_id}"
        assert descriptor.help_text in marked_help
        assert descriptor.validation is not ValidationKind.UNSUPPORTED
        expected_trigger = (
            CommitTrigger.ON_CHANGE
            if descriptor.preset is PresetBehavior.STRICT
            or descriptor.editor is EditorFamily.BOOLEAN
            else CommitTrigger.ON_CONFIRM
        )
        assert descriptor.commit_trigger is expected_trigger


def test_unknown_action_field_and_unknown_runtime_class_fail_closed() -> None:
    class UnknownField(formField.Field):
        description = "fixture"

    with pytest.raises(FieldPresentationError, match=r"custom\.value"):
        describe_field("custom", "value", "Value", formField.CharField("x"))
    with pytest.raises(FieldPresentationError, match=r"crop\.all.*UnknownField"):
        describe_field("crop", "all", "All", UnknownField("x"))


def test_missing_or_extra_runtime_fields_fail_before_descriptor_use() -> None:
    with pytest.raises(FieldPresentationError, match=r"crop.*missing"):
        describe_action_fields("crop", {"Mode": formField.ChoiceField("All", ("All",))})
    with pytest.raises(FieldPresentationError, match=r"crop.*extra"):
        describe_action_fields(
            "crop",
            {
                "Mode": formField.ChoiceField("All", ("All",)),
                "All": formField.PixelField("1px"),
                "Left": formField.PixelField("1px"),
                "Right": formField.PixelField("1px"),
                "Top": formField.PixelField("1px"),
                "Bottom": formField.PixelField("1px"),
                "Surprise": formField.CharField("x"),
            },
        )


def test_non_sequence_choices_are_not_treated_as_presets() -> None:
    field = formField.CharField("x")
    field.choices = 1

    descriptor = describe_field("write_tag", "value", "Value", field)

    assert descriptor.preset is PresetBehavior.NONE


def test_strict_choice_without_values_fails_closed() -> None:
    field = formField.ChoiceField("", ())

    with pytest.raises(FieldPresentationError, match="strict choice has no values"):
        describe_field("convert_mode", "mode", "Mode", field)


def test_pixel_descriptor_without_percentage_basis_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(field_presentation, "PERCENTAGE_BASES", {})

    with pytest.raises(FieldPresentationError, match="missing percentage basis"):
        describe_field("crop", "all", "All", formField.PixelField("1px"))


def test_descriptor_without_translated_help_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(field_presentation, "FIELD_HELP", {})

    with pytest.raises(FieldPresentationError, match="missing translated help"):
        describe_field("write_tag", "value", "Value", formField.CharField("x"))


def test_unknown_action_descriptor_fails_closed() -> None:
    with pytest.raises(FieldPresentationError, match=r"custom\.\*"):
        describe_action_fields("custom", {})
