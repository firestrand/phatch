from argparse import ArgumentParser

import builtins

from phatch.core import cli
from phatch.core.settings import DEFAULT_SETTINGS


if not hasattr(builtins, '_'):
    builtins._ = lambda x: x


INFO = {'name': 'phatch', 'version': '1.0'}


def test_get_cli_description_lines_contains_examples():
    lines = cli.get_cli_description_lines(INFO)
    assert lines[0] == '%(name)s [actionlist]' % INFO
    assert any('phatch --inspect image_file.jpg' in line for line in lines)


def test_get_cli_option_specs_has_console_flag():
    specs = cli.get_cli_option_specs(INFO)
    console_spec = next(spec for spec in specs if '--console' in spec['flags'])
    assert console_spec['dest'] == 'console'


def test_add_cli_options_uses_defaults():
    parser = ArgumentParser()
    cli.add_cli_options(parser, DEFAULT_SETTINGS, INFO)
    parser.add_argument('paths', nargs='*')
    args = parser.parse_args([])
    assert args.console is DEFAULT_SETTINGS['console']
    assert args.verbose is DEFAULT_SETTINGS['verbose']
