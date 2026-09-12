import re

import pytest

from phatch.lib import formField


class DecisionForm(formField.Form):
    label = "Decision form"

    def interface(self, fields: formField.Fields) -> None:
        fields["Title"] = formField.CharField("photo")
        fields["Width"] = formField.PixelField("50%")
        fields["Implicit Pixel"] = formField.PixelField("2px")
        fields["Flag"] = formField.BooleanField(True)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("2.6", 3), ("-2.6", -3), ("1 / 2", 0)],
)
def test_integer_field_evaluates_and_rounds(raw: str, expected: int) -> None:
    assert formField.IntegerField(raw).get(label="Count") == expected


@pytest.mark.parametrize("raw", ["'abc'", "[]"])
def test_integer_field_reports_invalid_values(raw: str) -> None:
    with pytest.raises(
        formField.ValidationError,
        match=re.escape(f'invalid literal "{raw}" for integer'),
    ):
        formField.IntegerField(raw).get(label="Count")


def test_numeric_runtime_error_is_not_hidden_as_invalid_syntax() -> None:
    with pytest.raises(ZeroDivisionError):
        formField.FloatField("1 / 0").get(label="Ratio")


def test_float_field_evaluates_expression_and_reports_bad_literal() -> None:
    assert formField.FloatField("1 / 2").get(label="Ratio") == 0.5
    with pytest.raises(formField.ValidationError, match="invalid literal"):
        formField.FloatField("'abc'").get(label="Ratio")


@pytest.mark.parametrize(
    ("field", "raw", "message"),
    [
        (formField.PositiveIntegerField, "-1", "is negative"),
        (formField.PositiveNonZeroIntegerField, "0", "is zero"),
        (formField.PositiveFloatField, "-0.5", "is negative"),
        (formField.PositiveNonZeroFloatField, "0", "is zero"),
    ],
)
def test_positive_fields_reject_out_of_domain_values(
    field: type[formField.Field], raw: str, message: str
) -> None:
    with pytest.raises(formField.ValidationError, match=message):
        field(raw).get(label="Value")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("YES", True),
        ("False", False),
        ("0", False),
    ],
)
def test_boolean_field_accepts_legacy_aliases(raw: str, expected: bool) -> None:
    assert formField.BooleanField(raw).get(label="Enabled") is expected


def test_boolean_field_serializes_and_rejects_unknown_alias() -> None:
    assert formField.BooleanField(True).get_as_string() == "yes"
    assert formField.BooleanField(False).get_as_string() == "no"
    with pytest.raises(formField.ValidationError, match='invalid literal "maybe"'):
        formField.BooleanField("maybe").get(label="Enabled")


def test_char_defaults_empty_values_and_dirty_state() -> None:
    selected = formField.CharField(None, choices=["first", "second"])
    empty = formField.CharField("")

    assert selected.get() == "first"
    assert empty.value_as_string == " "
    assert empty.get() == " "
    selected.set_as_string("second")
    assert selected.dirty is False
    selected.set_as_string_dirty("third")
    assert selected.get() == "third"
    assert selected.dirty is True


def test_field_empty_and_invalid_interpolation_report_context() -> None:
    with pytest.raises(formField.ValidationError, match="Name: can not be empty"):
        formField.Field("value").get(info={}, value_as_string="   ", label="Name")
    with pytest.raises(formField.ValidationError) as error:
        formField.Field("value").get(info={}, value_as_string="<missing>", label="Name")
    assert error.value.expected == "<?>"
    assert error.value.details == formField.USE_INSPECTOR
    assert "missing" in str(error.value)


def test_field_without_info_uses_stored_value_and_safe_state_roundtrips() -> None:
    field = formField.Field("stored")
    original = formField.get_safe()
    try:
        formField.set_safe(False)
        assert field.get(info=None, value_as_string="ignored") == "stored"
        assert formField.get_safe() is False
    finally:
        formField.set_safe(original)


def test_field_safe_assertion_globals_and_invalid_formula_errors() -> None:
    original_globals = formField.Field._globals
    field = formField.Field("<width + 1>")
    try:
        formField.Field.set_globals({"width": 2})
        field.assert_safe("Width", {})
        assert field.get({}) == "3"
    finally:
        formField.Field.set_globals(original_globals)

    with pytest.raises(formField.ValidationError, match="invalid syntax"):
        field.eval("1 +", "Formula")
    with pytest.raises(formField.safe.UnsafeError, match="unknown_name"):
        field.eval("unknown_name", "Formula")


def test_choice_replacement_only_marks_invalid_current_value_dirty() -> None:
    unchanged = formField.ChoiceField("a", ["a", "b"])
    unchanged.set_choices(["a", "c"])
    replaced = formField.ChoiceField("a", ["a", "b"])
    replaced.set_choices(["b", "c"])

    assert unchanged.get_as_string() == "a"
    assert unchanged.dirty is False
    assert replaced.get_as_string() == "b"
    assert replaced.dirty is True


def test_form_converts_labels_sizes_exclusions_and_raw_state() -> None:
    form = DecisionForm()

    values = form.get_fields(
        {"dpi": 254}, convert=True, pixel_fields={"Width": 200}, exclude=["Flag"]
    )

    assert values == {"title": "photo", "width": 100, "implicit_pixel": 2}
    assert form.get_field_labels()[0] == "__enabled__"
    assert form.is_enabled() is True
    assert form.is_field_true("Flag") is True
    assert form.load({"Title": "renamed", "Unknown": "x"}) == ["Unknown"]
    assert form.dump()["fields"]["Title"] == "renamed"


def test_form_uses_explicit_pixel_dpi_and_mutator_return_values() -> None:
    form = DecisionForm()

    assert (
        form.get_fields({"dpi": 72}, pixel_fields={"Width": (100, 254)})["Width"] == 50
    )
    assert form.set_field("Title", "new") is form
    assert form.set_field_as_string("Title", "raw") is form
    assert form.set_field_as_string_dirty("Title", "dirty") is form
    assert form.get_field_string("Title") == "dirty"
    assert form._get_field("Title").dirty is True


def test_form_default_field_options_and_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    form = DecisionForm()
    monkeypatch.setattr(formField.system, "ensure_path", lambda path: f"ready:{path}")
    monkeypatch.setattr(formField.system, "find_exe", lambda _program: "/bin/tool")

    assert form.get_fields({"dpi": 72}) == {
        "Title": "photo",
        "Width": 0,
        "Implicit Pixel": 2,
        "Flag": True,
    }
    assert form.ensure_path("folder") == "ready:folder"
    assert form.find_exe("tool") is None
    assert form.exe["tool"] == "/bin/tool"


def test_form_find_exe_reports_missing_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(formField.system, "find_exe", lambda _program: None)

    with pytest.raises(Exception, match="install"):
        DecisionForm().find_exe("missing", name="Fixture Tool")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("2cm", 200), ("50%", 50), ("2px", 2)],
)
def test_pixel_field_converts_units(raw: str, expected: int) -> None:
    assert formField.PixelField(raw).get_size({}, 100, 254, "Width") == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("5bt", 5), ("5kb", 5120), ("5mb", 5242880), ("1gb", 1073741824)],
)
def test_file_size_field_converts_units(raw: str, expected: int) -> None:
    assert formField.FileSizeField(raw).get(label="Size") == expected


def test_image_choice_fields_convert_legacy_values() -> None:
    assert formField.ImageEffectField("edge enhance more").get() == "EDGE_ENHANCE_MORE"
    assert formField.ImageResampleField("antialias").get() == "LANCZOS"
    assert formField.ImageFilterField("linear").get() == "BILINEAR"
    assert formField.ImageModeField(formField.IMAGE_MODES[3]).get() == "RGB"
    assert formField.OrientationField("Normal").get() is None
    assert formField.OrientationField("Rotate 90").get() == "ROTATE_90"


def test_image_type_fixing_and_specialized_choice_constructors() -> None:
    assert formField.ImageTypeField("jpg").fix_string(".jpg") == "jpg"
    assert formField.ImageTypeField("jpg").fix_string("") == ""
    assert "jpg" in formField.ImageReadTypeField("jpg").choices
    assert "<type>" in formField.ImageWriteTypeField("<type>").choices
    assert "automatic" in formField.ImageResampleAutoField("automatic").choices
    assert "Orientation" in formField.ImageTransposeField("Orientation").choices
    assert "None" in formField.OptionalTransposeField("None").choices
    assert formField.AlignHorizontalField("left").choices == formField.ALIGN_HORIZONTAL
    assert formField.AlignVerticalField("top").choices == formField.ALIGN_VERTICAL
    assert formField.RankSizeField(3).get() == 3
    assert formField.SliderField(5, 0, 10).min == 0
    assert formField.TiffCompressionField("none").get() == "none"


def test_metadata_field_fixes_rendered_tag_and_validates_namespace() -> None:
    field = formField.ExifItpcField("Exif_Image_Artist")

    assert field.fix_string("<Exif_Image_Artist>") == "Exif_Image_Artist"
    assert field.fix_string("<broken") == "<broken"
    assert field.get() == "Exif_Image_Artist"
    with pytest.raises(formField.ValidationError) as error:
        field.get(info={}, value_as_string="Artist", label="Tag")
    assert error.value.details == formField.USE_INSPECTOR
    assert str(error.value) == 'Tag should start with "Exif_" or "Iptc_"'


def test_validation_error_unicode_includes_details_only_when_present() -> None:
    detailed = formField.ValidationError("expected", "message", "details")
    plain = formField.ValidationError("expected", "message")

    assert str(detailed) == "message"
    assert detailed.__unicode__() == "message\ndetails"
    assert plain.__unicode__() == "message"
