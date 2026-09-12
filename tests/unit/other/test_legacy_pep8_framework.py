from pathlib import Path

import pytest

from phatch.other import pep8


@pytest.fixture(autouse=True)
def isolate_legacy_pep8_globals(monkeypatch):
    monkeypatch.setattr(pep8, "options", pep8.options)
    monkeypatch.setattr(pep8, "args", pep8.args)
    pep8.process_options(["--ignore", "", "fixture.py"])


def run_checker(tmp_path: Path, source: str, name: str = "fixture.py"):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    checker = pep8.Checker(str(path))
    return path, checker, checker.check_all()


def test_checker_reports_exact_codes_positions_and_count(tmp_path, capsys):
    path, _, count = run_checker(
        tmp_path,
        "import os, sys\nvalue=1 #bad\n",
    )

    lines = capsys.readouterr().out.splitlines()
    assert count == 3
    assert lines == [
        f"{path}:1:10: E401 multiple imports on one line",
        f"{path}:2:6: E225 missing whitespace around operator",
        f"{path}:2:8: E261 at least two spaces before inline comment",
    ]


def test_checker_maps_multiline_logical_error_to_physical_position(
        tmp_path, capsys):
    path, _, count = run_checker(tmp_path, "result = (\n    1+2\n)\n")

    output = capsys.readouterr().out
    assert count == 1
    assert output == f"{path}:2:6: E225 missing whitespace around operator\n"


def test_checker_ignores_operator_text_inside_strings_and_comments(tmp_path):
    _, _, count = run_checker(
        tmp_path,
        'value = "left=right"  # operator text is inert\n',
    )

    assert count == 0


def test_checker_handles_blank_lines_decorators_and_definitions(tmp_path):
    _, _, count = run_checker(
        tmp_path,
        "def first():\n    pass\n\ndef second():\n    pass\n\n\n\n"
        "@decorator\n\ndef third():\n    pass\n",
    )

    assert count == 3
    assert pep8.options.counters == {
        "physical lines": 12,
        "logical lines": 7,
        "E302": 1,
        "E303": 1,
        "E304": 1,
    }


def test_checker_decodes_invalid_utf8_with_replacement(tmp_path):
    path = tmp_path / "encoded.py"
    path.write_bytes(b"value = '\xff'\n")

    checker = pep8.Checker(str(path))

    assert checker.lines == ["value = '\ufffd'\n"]
    assert checker.check_all() == 0


def test_quiet_repeat_source_and_pep8_reporting(tmp_path, capsys):
    pep8.process_options(["--repeat", "--show-source", "--show-pep8",
                          "fixture.py"])
    path, _, count = run_checker(tmp_path, "a=1\nb=2\n")

    output = capsys.readouterr().out
    assert count == 2
    assert output.count("E225 missing whitespace around operator") == 2
    assert "a=1\n ^\n" in output
    assert "Always surround these binary operators" in output
    assert str(path) in output


def test_quiet_levels_report_filename_once_then_nothing(tmp_path, capsys):
    pep8.process_options(["-q", "fixture.py"])
    path, _, count = run_checker(tmp_path, "a=1\nb=2\n")
    first_output = capsys.readouterr().out

    pep8.process_options(["-qq", "fixture.py"])
    _, _, silent_count = run_checker(tmp_path, "a=1\nb=2\n", "silent.py")

    assert count == 2
    assert first_output == f"{path}\n"
    assert silent_count == 2
    assert capsys.readouterr().out == ""


def test_repeat_controls_duplicate_diagnostic_output(tmp_path, capsys):
    path, _, count = run_checker(tmp_path, "a=1\nb=2\n")

    assert count == 2
    assert capsys.readouterr().out == (
        f"{path}:1:2: E225 missing whitespace around operator\n"
    )


def test_statistics_partition_and_print_sorted_results(tmp_path, capsys):
    run_checker(tmp_path, "import os, sys\nvalue=1\nvalue = 1  \n")
    capsys.readouterr()

    assert pep8.get_error_statistics() == [
        "1       E225 missing whitespace around operator",
        "1       E401 multiple imports on one line",
    ]
    assert pep8.get_warning_statistics() == [
        "1       W291 trailing whitespace",
    ]
    assert pep8.get_count("E") == 2
    assert pep8.get_count("W") == 1

    pep8.print_statistics()
    assert capsys.readouterr().out.splitlines() == [
        "1       E225 missing whitespace around operator",
        "1       E401 multiple imports on one line",
        "1       W291 trailing whitespace",
    ]


def test_selection_overrides_ignore_and_unselected_checks_stay_silent(
        tmp_path, capsys):
    pep8.process_options(["--select", "E241", "fixture.py"])
    path, _, count = run_checker(tmp_path, "items = (1,  2)\nvalue=1\n")

    assert count == 1
    assert capsys.readouterr().out == (
        f"{path}:1:12: E241 multiple spaces after ','\n"
    )
    assert pep8.ignore_code("E241") is False
    assert pep8.ignore_code("E225") is True


def test_file_and_directory_filters_use_real_paths(tmp_path, capsys):
    included = tmp_path / "included.py"
    skipped = tmp_path / "skipped.txt"
    excluded_dir = tmp_path / ".git"
    excluded_dir.mkdir()
    included.write_text("value=1\n", encoding="utf-8")
    skipped.write_text("value=1\n", encoding="utf-8")
    (excluded_dir / "hidden.py").write_text("value=1\n", encoding="utf-8")

    pep8.input_dir(str(tmp_path))

    assert capsys.readouterr().out == (
        f"{included}:1:6: E225 missing whitespace around operator\n"
    )
    assert pep8.options.counters["directories"] == 1
    assert pep8.options.counters["files"] == 1


def test_testsuite_reports_missing_expected_code(tmp_path, capsys):
    pep8.process_options(["--testsuite", str(tmp_path)])
    path = tmp_path / "E401.py"
    path.write_text("import os\n", encoding="utf-8")

    pep8.input_file(str(path))

    assert capsys.readouterr().out == f"{path}: error E401 not found\n"


def test_verbose_checker_and_benchmark_report_activity(tmp_path, capsys):
    pep8.process_options(["-vvv", "fixture.py"])
    path = tmp_path / "fixture.py"
    path.write_text("value = 1\n", encoding="utf-8")

    pep8.input_file(str(path))
    pep8.print_benchmark(0.5)

    output = capsys.readouterr().out
    assert f"checking {path}" in output
    assert "value = 1" in output
    assert "missing_whitespace_around_operator" in output
    assert "0.50    seconds elapsed" in output
    assert "2       physical lines per second (1 total)" in output


def test_in_memory_checker_and_discovery_public_apis(capsys):
    checker = pep8.Checker(None)
    checker.lines = ["value=1\n"]

    assert checker.check_all() == 1
    assert capsys.readouterr().out == (
        "stdin:1:6: E225 missing whitespace around operator\n"
    )
    assert len(pep8.find_checks("physical_line")) == 6
    assert len(pep8.find_checks("logical_line")) == 15


def test_selftest_runs_embedded_examples(capsys):
    pep8.process_options(["--doctest", "-v"])

    pep8.selftest()

    output = capsys.readouterr().out
    assert "passed and 0 failed." in output
    assert output.endswith("Test passed.\n")


def test_option_boundaries_and_empty_filename_filter(tmp_path):
    with pytest.raises(SystemExit) as error:
        pep8.process_options([])

    assert error.value.code == 2
    parsed, arguments = pep8.process_options(
        ["--filename", "", "--ignore", "E1,W", "fixture.py"])
    assert arguments == ["fixture.py"]
    assert parsed.filename == ""
    assert parsed.ignore == ["E1", "W"]
    assert pep8.filename_match("anything.txt") is True
    assert pep8.input_file(str(tmp_path / ".git")) == {}


def test_testsuite_suppresses_expected_and_unrelated_errors(tmp_path, capsys):
    pep8.process_options(["--testsuite", str(tmp_path)])
    expected = tmp_path / "E225.py"
    negative = tmp_path / "E401not.py"
    expected.write_text("value=1\n", encoding="utf-8")
    negative.write_text("value=1\n", encoding="utf-8")

    pep8.input_file(str(expected))
    pep8.input_file(str(negative))

    assert capsys.readouterr().out == ""
