import os
import subprocess
import sys
from pathlib import Path


def run_cli(project_root: Path, arguments: list[str], env: dict[str, str]):
    module = project_root / "phatch" / "other" / "pep8.py"
    return subprocess.run(
        [sys.executable, str(module), *arguments],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_help_is_available_without_source_execution(
        project_root, isolated_runtime):
    result = run_cli(project_root, ["--help"], isolated_runtime.env)

    assert result.returncode == 0
    assert "Usage: pep8.py [options] input ..." in result.stdout
    assert "--show-source" in result.stdout
    assert result.stderr == ""


def test_cli_requires_an_input_file(project_root, isolated_runtime):
    result = run_cli(project_root, [], isolated_runtime.env)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "pep8.py: error: input not specified" in result.stderr


def test_cli_checks_real_valid_and_invalid_files(
        project_root, isolated_runtime):
    valid = isolated_runtime.root / "valid.py"
    invalid = isolated_runtime.root / "invalid.py"
    valid.write_text("value = 1\n", encoding="utf-8")
    invalid.write_text("import os, sys\nvalue=1 #bad\n", encoding="utf-8")

    valid_result = run_cli(project_root, [str(valid)], isolated_runtime.env)
    invalid_result = run_cli(
        project_root,
        ["--repeat", "--show-source", "--count", str(invalid)],
        isolated_runtime.env,
    )

    assert valid_result.returncode == 0
    assert valid_result.stdout == ""
    assert invalid_result.returncode == 1
    assert f"{invalid}:1:10: E401" in invalid_result.stdout
    assert f"{invalid}:2:6: E225" in invalid_result.stdout
    assert "value=1 #bad\n     ^" in invalid_result.stdout
    assert invalid_result.stderr == "3\n"


def test_cli_directory_filters_statistics_and_benchmark(
        project_root, isolated_runtime):
    sources = isolated_runtime.root / "sources"
    excluded = sources / "generated"
    excluded.mkdir(parents=True)
    (sources / "checked.py").write_text("value=1\n", encoding="utf-8")
    (sources / "ignored.txt").write_text("value=1\n", encoding="utf-8")
    (excluded / "hidden.py").write_text("value=1\n", encoding="utf-8")

    result = run_cli(
        project_root,
        ["--exclude", "generated", "--statistics", "--benchmark",
         str(sources)],
        isolated_runtime.env,
    )

    assert result.returncode == 0
    assert "checked.py:1:6: E225 missing whitespace around operator" in result.stdout
    assert "1       E225 missing whitespace around operator" in result.stdout
    assert "seconds elapsed" in result.stdout
    assert "1 total" in result.stdout
    assert "hidden.py" not in result.stdout
    assert result.stderr == ""


def test_cli_quiet_and_selection_are_isolated_between_processes(
        project_root, isolated_runtime):
    source = isolated_runtime.root / "spacing.py"
    source.write_text("items = (1,  2)\nvalue=1\n", encoding="utf-8")

    selected = run_cli(
        project_root,
        ["--select", "E241", str(source)],
        isolated_runtime.env,
    )
    quiet = run_cli(project_root, ["-q", str(source)], isolated_runtime.env)

    assert selected.stdout == (
        f"{source}:1:12: E241 multiple spaces after ','\n"
    )
    assert quiet.stdout == f"{source}\n"
    assert selected.returncode == quiet.returncode == 0
    assert os.environ.get("COVERAGE_PROCESS_START") is None
