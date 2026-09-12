"""Shared command-line option metadata and helpers for Phatch entry points."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Mapping
from typing import NotRequired, TypedDict, TypeVar

from phatch.lib.reverse_translation import _translate as _

DefaultValue = TypeVar("DefaultValue")


class CliOptionSpec(TypedDict):
    flags: tuple[str, ...]
    dest: str
    help: str
    action: NotRequired[str]
    default: NotRequired[str | bool | int]
    choices: NotRequired[tuple[str, ...]]
    type: NotRequired[Callable[[str], int]]


def _worker_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("max workers must be an integer") from error
    cpu_count = os.cpu_count() or 1
    if not 1 <= count <= cpu_count:
        raise argparse.ArgumentTypeError(
            f"max workers must be between 1 and available CPU count ({cpu_count})"
        )
    return count


CLI_DESCRIPTION_TEMPLATE = """\
%(name)s [actionlist]
%(name)s [options] [actionlist] [image folders/files/urls]
%(name)s --inspect [image files/urls]
%(name)s --droplet [actionlist/recent] [image files/urls]

%(examples_label)s:
  phatch action_list.phatch
  phatch --verbose --recursive action_list.phatch image_file.png image_folder
  phatch --inspect image_file.jpg
  phatch --droplet recent
"""


def get_cli_description_lines(info: Mapping[str, str]) -> list[str]:
    """Return the CLI usage/examples lines for the given ``info`` mapping."""

    return format_cli_description(info).strip().splitlines()


def format_cli_description(info: Mapping[str, str]) -> str:
    """Return the full CLI description string for argparse."""

    description_context = dict(info)
    description_context["examples_label"] = _("Examples")
    return CLI_DESCRIPTION_TEMPLATE % description_context


def get_cli_option_specs(info: Mapping[str, str]) -> list[CliOptionSpec]:
    """Return CLI option metadata dictionaries for building parsers."""

    return [
        {
            "flags": ("--max-workers",),
            "dest": "max_workers",
            "help": _("Maximum independent CPU image jobs (default: 1)"),
            "default": 1,
            "type": _worker_count,
        },
        {
            "flags": ("--dry-run",),
            "dest": "dry_run",
            "action": "store_true",
            "help": _("Build and report an execution plan without writing files"),
            "default": False,
        },
        {
            "flags": ("--report-format",),
            "dest": "report_format",
            "help": _("Select human-readable text or stable JSON output"),
            "default": "text",
            "choices": ("text", "json"),
        },
        {
            "flags": ("--resume",),
            "dest": "resume",
            "help": _("Resume from the specified recovery journal"),
            "default": "",
        },
        {
            "flags": ("--capabilities",),
            "dest": "capabilities",
            "action": "store_true",
            "help": _("Report optional capability availability"),
            "default": False,
        },
        {
            "flags": ("-c", "--console"),
            "dest": "console",
            "action": "store_true",
            "help": _("Run %s as console program without a gui") % info["name"],
        },
        {
            "flags": ("-d", "--droplet"),
            "dest": "droplet",
            "action": "store_true",
            "help": _("Run %s as a gui droplet") % info["name"],
        },
        {
            "flags": ("--desktop",),
            "dest": "desktop",
            "action": "store_true",
            "help": _("Always save on desktop"),
        },
        {
            "flags": ("-f", "--force"),
            "dest": "stop_for_errors",
            "action": "store_false",
            "help": _("Ignore errors"),
        },
        {
            "flags": ("--fonts",),
            "dest": "init_fonts",
            "action": "store_true",
            "help": _("Initialize fonts (only for installation scripts)"),
        },
        {
            "flags": ("-i", "--interactive"),
            "dest": "interactive",
            "action": "store_true",
            "help": _("Interactive"),
        },
        {
            "flags": ("-k", "--keep"),
            "dest": "overwrite_existing_images",
            "action": "store_false",
            "help": _("Keep existing images (don't overwrite)"),
        },
        {
            "flags": ("-l",),
            "dest": "locale",
            "help": _("Specify locale language (for example en or en_GB)"),
            "default": "default",
        },
        {
            "flags": ("-n", "--inspect"),
            "dest": "image_inspector",
            "action": "store_true",
            "help": _("Inspect metadata (requires exif & iptc plugin)"),
        },
        {
            "flags": ("--no-save",),
            "dest": "no_save",
            "action": "store_true",
            "help": _("No save action required at the end"),
        },
        {
            "flags": ("-r", "--recursive"),
            "dest": "recursive",
            "action": "store_true",
            "help": _("Include all subfolders"),
        },
        {
            "flags": ("-t", "--trust"),
            "dest": "check_images_first",
            "action": "store_false",
            "help": _("Do not check images first"),
        },
        {
            "flags": ("--unsafe",),
            "dest": "safe",
            "action": "store_false",
            "help": _("Allow Geek action and unsafe expressions"),
        },
        {
            "flags": ("-v", "--verbose"),
            "dest": "verbose",
            "action": "store_true",
            "help": _("Verbose"),
        },
    ]


def add_cli_options(
    parser: argparse.ArgumentParser,
    defaults: Mapping[str, DefaultValue],
    info: Mapping[str, str],
) -> None:
    """Add standard Phatch CLI options to ``parser`` using ``defaults``."""

    for spec in get_cli_option_specs(info):
        action = spec.get("action")
        if "default" in spec:
            default: str | bool | int | DefaultValue = spec["default"]
        else:
            default = defaults[spec["dest"]]
        choices = spec.get("choices")
        value_type = spec.get("type")
        if action is None and value_type is not None:
            parser.add_argument(
                *spec["flags"],
                dest=spec["dest"],
                help=spec["help"],
                default=default,
                choices=choices,
                type=value_type,
            )
        elif action is None:
            parser.add_argument(
                *spec["flags"],
                dest=spec["dest"],
                help=spec["help"],
                default=default,
                choices=choices,
            )
        else:
            parser.add_argument(
                *spec["flags"],
                dest=spec["dest"],
                action=action,
                help=spec["help"],
                default=default,
            )
