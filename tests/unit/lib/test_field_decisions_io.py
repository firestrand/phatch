from pathlib import Path

import pytest

from phatch.lib import formField


def jpeg_file_field(value: str) -> formField.FileField:
    field = formField.FileField(value)
    field.extensions = ["jpg"]
    return field


class OptionalReadFileField(formField.ReadFileField):
    allow_empty = True


def test_files_dictionary_uses_injected_paths_extensions_and_titles(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.list"
    second = tmp_path / "second.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")

    result = formField.files_dictionary(
        [str(tmp_path), "", str(tmp_path / "missing")],
        [".list"],
        title_parser=lambda path: Path(path).stem.upper(),
    )

    assert result == {"FIRST": str(first)}


def test_rotation_title_parser_uses_filename_only() -> None:
    assert (
        formField.rotation_title_parser(None, "/tmp/rotate_left.png") == "Rotate Left"
    )


def test_file_field_strips_value_and_checks_extension_case_insensitively() -> None:
    assert jpeg_file_field(" photo.JPG ").get(label="Image") == "photo.JPG"
    with pytest.raises(formField.ValidationError, match='extension "png" is invalid'):
        jpeg_file_field("photo.png").get(label="Image")
    with pytest.raises(formField.ValidationError, match="valid extension was expected"):
        jpeg_file_field("photo").get(label="Image")


def test_optional_file_fields_accept_empty_and_csv_enforces_extension() -> None:
    assert formField.EmptyFileField("").get() == ""
    assert formField.CsvFileField("").get() == ""
    assert formField.CsvFileField("data.CSV").get() == "data.CSV"
    with pytest.raises(formField.ValidationError, match='extension "txt" is invalid'):
        formField.CsvFileField("data.txt").get(label="Data")


def test_read_file_accepts_existing_path_and_rejects_missing_path(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "photo.jpg"
    existing.write_bytes(b"jpeg fixture")

    assert formField.ReadFileField(str(existing)).get(label="Image") == str(existing)
    with pytest.raises(formField.ValidationError, match="does not exist"):
        formField.ReadFileField(str(tmp_path / "missing.jpg")).get(label="Image")


def test_read_file_test_mode_accepts_changed_interpolated_path_without_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    field = formField.ReadFileField("<path> ")
    monkeypatch.setattr(
        formField.system,
        "is_file",
        lambda _path: pytest.fail("test interpolation must bypass filesystem lookup"),
    )

    assert field.get({"path": "/virtual/photo.jpg"}, label="Image", test=True) == (
        "/virtual/photo.jpg"
    )


def test_optional_read_file_returns_empty_without_filesystem_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        formField.system,
        "is_file",
        lambda _path: pytest.fail("empty value must bypass filesystem lookup"),
    )
    assert OptionalReadFileField("").get(label="Optional") == ""


def test_dictionary_read_file_resolves_display_name_and_initializes_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = tmp_path / "photo.jpg"
    existing.write_bytes(b"jpeg fixture")
    field = formField.DictionaryReadFileField("Display")
    calls = 0

    def initialize() -> None:
        nonlocal calls
        calls += 1
        field.dictionary = {"Display": str(existing)}

    monkeypatch.setattr(field, "init_dictionary", initialize)

    assert field.get(label="Image") == str(existing)
    assert field.get(label="Image") == str(existing)
    assert calls == 1


def test_font_file_uses_injected_dictionary_and_no_real_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    font = tmp_path / "Fixture.ttf"
    font.write_bytes(b"font fixture")
    monkeypatch.setattr(
        "phatch.lib.fonts.font_dictionary", lambda: {"Fixture Font": str(font)}
    )

    field = formField.FontFileField("Fixture Font")

    assert field.get(label="Font") == str(font)
    assert formField.FontFileField("").get(label="Font") == ""


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("missing file_in.jpg file_out.png", "can not be found"),
        ("tool file_out.png", 'Parameter "file_in.\\*" is missing'),
        ("tool file_in.jpg", 'Parameter "file_out.\\*" is missing'),
    ],
)
def test_command_line_reports_missing_requirements(
    command: str,
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        formField.system,
        "find_exe",
        lambda program: None if program == "missing" else "/bin/tool",
    )

    with pytest.raises(formField.ValidationError, match=message):
        formField.CommandLineField(command).get(label="Command")


def test_command_line_requirement_flags_bypass_optional_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    field = formField.CommandLineField("unresolved")
    field.needs_exe = False
    field.needs_in = False
    field.needs_out = False
    monkeypatch.setattr(
        formField.system,
        "find_exe",
        lambda _program: pytest.fail("disabled executable check must not run"),
    )

    assert field.get(label="Command") == "unresolved"


def test_command_line_accepts_existing_executable_without_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "tool"
    executable.write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(
        formField.system,
        "find_exe",
        lambda _program: pytest.fail("existing executable needs no lookup"),
    )

    command = f"{executable} file_in.jpg file_out.png"
    assert formField.CommandLineField(command).get(label="Command") == command


def test_command_line_reports_duplicate_output_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    field = formField.CommandLineField("tool file_in.jpg file_out.png file_out.gif")
    monkeypatch.setattr(formField.system, "find_exe", lambda _program: "/bin/tool")

    # When / Then
    with pytest.raises(
        formField.ValidationError,
        match=r'Maximum one parameter "file_out\.\*" is allowed',
    ):
        field.get(label="Command")
