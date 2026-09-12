# -*- coding: UTF-8 -*-

# Phatch - Photo Batch Processor
# Copyright (C) 2007-2008  www.stani.be
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/

# Follows PEP8

import argparse
import builtins
import os
import sys
from collections.abc import MutableMapping
from typing import cast

from .core import config
from .core.cli import add_cli_options, format_cli_description
from .core.file_references import parse_file_reference
from .core.settings import DEFAULT_SETTINGS
from .core.user_paths import current_platform
from .data.info import INFO

CLI_INFO = cast(MutableMapping[str, str], INFO)
_ = getattr(builtins, "_", str)

VERSION = "{name} {version}".format(**INFO)


def fix_path(path):
    return os.fspath(parse_file_reference(path, current_platform()))


def parse_locale(config_paths):
    if "-l" in sys.argv:
        index = sys.argv.index("-l") + 1
        if index >= len(sys.argv):
            sys.exit('Please specify locale language after "-l".')
        canonical = sys.argv[index]
    else:
        canonical = "default"
    config.load_locale("phatch", config_paths["PHATCH_LOCALE_PATH"], canonical)


def parse_options():

    description = format_cli_description(CLI_INFO)

    parser = argparse.ArgumentParser(
        prog=CLI_INFO["name"],
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_cli_options(parser, DEFAULT_SETTINGS, CLI_INFO)
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("paths", nargs="*")

    options = parser.parse_args()
    paths = [fix_path(path) for path in options.paths if path and path[0] != "%"]
    options.paths = paths

    return options, paths


def reexec_with_pythonw(f=None):
    """'pythonw' needs to be called for any wxPython app
    to run from the command line on Mac Os X."""
    if (
        sys.version.split(" ")[0] < "2.5"
        and sys.platform == "darwin"
        and not (sys.executable.endswith("/Python") or hasattr(sys, "frozen"))
    ):
        sys.stderr.write("re-executing using pythonw")
        if not f:
            f = __file__
        os.execvp("pythonw", ["pythonw", f, *sys.argv[1:]])


def console(config_paths):
    main(config_paths=config_paths, app_file=None, force_console=True)


PYWX_ERROR = """\
Only the command line package 'phatch-cli' seems to be installed.
Please install the graphical user interface package 'phatch' as well.
"""


def import_pyWx():
    try:
        from .pyWx import gui
    except ModuleNotFoundError as error:
        if error.name != "wx":
            raise
        sys.exit(PYWX_ERROR)
    return gui


def _gui(app_file, paths, settings):
    reexec_with_pythonw(app_file)  # ensure pythonw for mac
    gui = import_pyWx()
    from .core import api
    from .pyWx.frame_dependencies import FrameDependencies

    registry = api.init()
    dependencies = FrameDependencies.for_action_registry(registry)
    actionlist = paths[0] if paths else ""
    gui.main(settings, actionlist, dependencies)


def _init_fonts():
    config.verify_app_user_paths()
    from .lib.fonts import font_dictionary

    font_dictionary(force=True)


def _inspect(app_file, paths):
    reexec_with_pythonw(app_file)  # ensure pythonw for mac
    gui = import_pyWx()
    gui.inspect(paths)


def _droplet(app_file, paths, settings):
    reexec_with_pythonw(app_file)  # ensure pythonw for mac
    gui = import_pyWx()
    from .core import api
    from .pyWx.frame_dependencies import FrameDependencies

    registry = api.init()
    dependencies = FrameDependencies.for_action_registry(registry)
    gui.drop(
        actionlist=paths[0],
        paths=paths[1:],
        settings=settings,
        dependencies=dependencies,
    )


def has_ext(path, ext):
    return path.lower().endswith(ext)


def _console(paths, settings):
    from .core.api import init

    registry = init()
    from .console import console

    if paths and has_ext(paths[0], INFO["extension"]):
        console.main(
            actionlist=paths[0], paths=paths[1:], settings=settings, registry=registry
        )
    else:
        console.main(actionlist="", paths=paths, settings=settings, registry=registry)


def main(config_paths=None, app_file=None, force_console=False):
    """Entry point for both GUI and console front-ends."""
    if config_paths is None:
        config_paths = config.init_config_paths()
    if app_file is None:
        app_file = __file__
    parse_locale(config_paths)
    options, paths = parse_options()
    from .core.settings import create_settings

    settings = create_settings(config_paths, options)
    if force_console:
        settings["console"] = True
    if settings["verbose"]:
        from .lib import system

        system.VERBOSE = True
    if "safe" in settings:
        from .lib import formField

        formField.set_safe(settings["safe"])
        del settings["safe"]
    if settings["image_inspector"]:
        _inspect(app_file, paths)
        return
    if settings["init_fonts"]:
        _init_fonts()
        return
    else:
        config.check_fonts()
    if paths and not (paths[0] == "recent" or has_ext(paths[0], INFO["extension"])):
        settings["droplet"] = True
        paths.insert(0, "recent")
    if settings["droplet"]:
        if not paths:
            paths = ["recent"]
        _droplet(app_file, paths, settings)
    elif len(paths) > 1 or settings["console"] or settings["interactive"]:
        _console(paths, settings)
    else:
        _gui(app_file, paths, settings)


if __name__ == "__main__":
    main()
