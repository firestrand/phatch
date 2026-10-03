"""Shared command-line option metadata and helpers for Phatch entry points."""

from __future__ import annotations

from typing import Dict, List, MutableMapping, Sequence


try:
    _
except NameError:  # pragma: no cover - ensures translation fallback
    __builtins__['_'] = str


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


def get_cli_description_lines(info: MutableMapping[str, str]) -> List[str]:
    """Return the CLI usage/examples lines for the given ``info`` mapping."""

    return format_cli_description(info).strip().splitlines()


def format_cli_description(info: MutableMapping[str, str]) -> str:
    """Return the full CLI description string for argparse."""

    description_context = dict(info)
    description_context['examples_label'] = _('Examples')
    return CLI_DESCRIPTION_TEMPLATE % description_context


def get_cli_option_specs(info: MutableMapping[str, str]) -> List[Dict[str, object]]:
    """Return CLI option metadata dictionaries for building parsers."""

    return [
        {'flags': ('--workers',), 'dest': 'workers', 'type': int, 'default': 1,
         'help': _("Bounded independent process workers (default: 1)")},
        {'flags': ('--memory-budget-mb',), 'dest': 'memory_budget_mb', 'type': int, 'default': 2048,
         'help': _("Total worker address-space budget in MiB (default: 2048)")},
        {'flags': ('--animation-policy',), 'dest': 'animation_policy',
         'choices': ('reject', 'first', 'extract', 'preserve'),
         'help': _("Explicit animation frame policy (default: reject)")},
        {'flags': ('--page-policy',), 'dest': 'page_policy',
         'choices': ('reject', 'first', 'extract', 'preserve'),
         'help': _("Explicit multipage document policy (default: reject)")},
        {'flags': ('--manifest',), 'dest': 'manifest_path',
         'help': _("Record a fingerprinted atomic batch journal")},
        {'flags': ('--resume',), 'dest': 'resume', 'action': 'store_true',
         'help': _("Resume only verified matching entries in --manifest")},
        {'flags': ('--capabilities',), 'dest': 'capabilities',
         'action': 'store_true', 'help': _("Report runtime codecs and optional tools as JSON")},
        {'flags': ('--dry-run',), 'dest': 'dry_run',
         'action': 'store_true', 'help': _("Plan outputs without processing")},
        {'flags': ('--report',), 'dest': 'report_path',
         'help': _("Write an atomic JSON batch report")},
        {'flags': ('--report-paths',), 'dest': 'report_paths',
         'action': 'store_true', 'help': _("Include full paths in the report")},
        {'flags': ('--collision-policy',), 'dest': 'collision_policy',
         'choices': ('skip', 'fail', 'replace', 'rename'),
         'help': _("Policy for existing or colliding output files")},
        {
            'flags': ('-c', '--console'),
            'dest': 'console',
            'action': 'store_true',
            'help': _("Run %s as console program without a gui") % info['name'],
        },
        {
            'flags': ('-d', '--droplet'),
            'dest': 'droplet',
            'action': 'store_true',
            'help': _("Run %s as a gui droplet") % info['name'],
        },
        {
            'flags': ('--desktop',),
            'dest': 'desktop',
            'action': 'store_true',
            'help': _("Always save on desktop"),
        },
        {
            'flags': ('-f', '--force'),
            'dest': 'stop_for_errors',
            'action': 'store_false',
            'help': _("Ignore errors"),
        },
        {
            'flags': ('--fonts',),
            'dest': 'init_fonts',
            'action': 'store_true',
            'help': _("Initialize fonts (only for installation scripts)"),
        },
        {
            'flags': ('-i', '--interactive'),
            'dest': 'interactive',
            'action': 'store_true',
            'help': _("Interactive"),
        },
        {
            'flags': ('-k', '--keep'),
            'dest': 'overwrite_existing_images',
            'action': 'store_false',
            'help': _("Keep existing images (don't overwrite)"),
        },
        {
            'flags': ('-l',),
            'dest': 'locale',
            'help': _("Specify locale language (for example en or en_GB)"),
            'default': 'default',
        },
        {
            'flags': ('-n', '--inspect'),
            'dest': 'image_inspector',
            'action': 'store_true',
            'help': _("Inspect metadata (requires exif & iptc plugin)"),
        },
        {
            'flags': ('--no-save',),
            'dest': 'no_save',
            'action': 'store_true',
            'help': _("No save action required at the end"),
        },
        {
            'flags': ('-r', '--recursive'),
            'dest': 'recursive',
            'action': 'store_true',
            'help': _("Include all subfolders"),
        },
        {
            'flags': ('-t', '--trust'),
            'dest': 'check_images_first',
            'action': 'store_false',
            'help': _("Do not check images first"),
        },
        {
            'flags': ('--unsafe',),
            'dest': 'safe',
            'action': 'store_false',
            'help': _("Allow Geek action and unsafe expressions"),
        },
        {
            'flags': ('-v', '--verbose'),
            'dest': 'verbose',
            'action': 'store_true',
            'help': _("Verbose"),
        },
    ]


def add_cli_options(parser, defaults: MutableMapping[str, object], info: MutableMapping[str, str]) -> None:
    """Add standard Phatch CLI options to ``parser`` using ``defaults``."""

    for spec in get_cli_option_specs(info):
        flags: Sequence[str] = spec['flags']  # type: ignore[assignment]
        kwargs: Dict[str, object] = {
            key: spec[key] for key in ('dest', 'action', 'help', 'metavar', 'choices', 'type') if key in spec
        }
        default_key = spec.get('default_key', spec.get('dest'))
        if 'default' in spec:
            kwargs['default'] = spec['default']
        elif default_key in defaults:
            kwargs['default'] = defaults[default_key]  # type: ignore[index]
        parser.add_argument(*flags, **kwargs)
