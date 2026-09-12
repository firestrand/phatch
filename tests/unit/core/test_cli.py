import builtins
from argparse import ArgumentParser

import pytest

from phatch.core import cli
from phatch.core.settings import DEFAULT_SETTINGS

if not hasattr(builtins, "_"):
    builtins._ = lambda x: x


INFO = {"name": "phatch", "version": "1.0"}


def test_get_cli_description_lines_contains_examples():
    lines = cli.get_cli_description_lines(INFO)
    assert lines[0] == f"{INFO['name']} [actionlist]"
    assert any("phatch --inspect image_file.jpg" in line for line in lines)


def test_get_cli_option_specs_has_console_flag():
    specs = cli.get_cli_option_specs(INFO)
    console_spec = next(spec for spec in specs if "--console" in spec["flags"])
    assert console_spec["dest"] == "console"


def test_add_cli_options_uses_defaults():
    parser = ArgumentParser()
    cli.add_cli_options(parser, DEFAULT_SETTINGS, INFO)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args([])
    assert args.console is DEFAULT_SETTINGS["console"]
    assert args.verbose is DEFAULT_SETTINGS["verbose"]
    assert args.max_workers == 1


def test_max_workers_rejects_nonpositive_values():
    parser = ArgumentParser()
    cli.add_cli_options(parser, DEFAULT_SETTINGS, INFO)

    with pytest.raises(SystemExit):
        parser.parse_args(["--max-workers", "0"])


def test_add_cli_options_supports_structured_automation_flags():
    parser = ArgumentParser()
    cli.add_cli_options(parser, DEFAULT_SETTINGS, INFO)
    parser.add_argument("paths", nargs="*")

    args = parser.parse_args(
        ["--dry-run", "--report-format", "json", "--resume", "journal.jsonl"]
    )

    assert args.dry_run is True
    assert args.report_format == "json"
    assert args.resume == "journal.jsonl"
    assert args.capabilities is False
