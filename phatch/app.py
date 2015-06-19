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

import os
import optparse
import sys
import urllib

from data.info import INFO
from core import config

VERSION = "%(name)s %(version)s" % INFO


def fix_path(path):
    #TODO: move me to lib/system.py
    if path.startswith('file://'):
        return urllib.unquote(path[7:])
    return path


def parse_locale(config_paths):
    if '-l' in sys.argv:
        index = sys.argv.index('-l') + 1
        if index >= len(sys.argv):
            sys.exit('Please specify locale language after "-l".')
        canonical = sys.argv[index]
    else:
        canonical = 'default'
    config.load_locale('phatch', config_paths["PHATCH_LOCALE_PATH"], canonical)


def parse_options():

    parser = optparse.OptionParser(
        usage="""
  %(name)s [actionlist]
  %(name)s [options] [actionlist] [image folders/files/urls]
  %(name)s --inspect [image files/urls]
  %(name)s --droplet [actionlist/recent] [image files/urls]""" % INFO + """

%s:
  phatch action_list.phatch
  phatch --verbose --recursive action_list.phatch image_file.png image_folder
  phatch --inspect image_file.jpg
  phatch --droplet recent""" % _('Examples'),
        version=VERSION,
    )
    parser.add_option("-c", "--console", action="store_true",
        dest="console",
        default=False,
        help=_("Run %s as console program without a gui") % INFO['name'])
    parser.add_option("-d", "--droplet", action="store_true",
        dest="droplet",
        default=False,
        help=_("Run %s as a gui droplet") % INFO['name'])
    parser.add_option("--desktop", action="store_true",
        dest="desktop",
        default=False,
        help=_("Always save on desktop"))
    parser.add_option("-f", "--force", action="store_false",
        dest="stop_for_errors",
        default=True,
        help=_("Ignore errors"))
    parser.add_option("--fonts", action="store_true",
        dest="init_fonts",
        default=False,
        help=_("Initialize fonts (only for installation scripts)"))
    parser.add_option("-i", "--interactive", action="store_true",
        dest="interactive",
        default=False,
        help=_("Interactive"))
    parser.add_option("-k", "--keep", action="store_false",
        dest="overwrite_existing_images",
        default=True,
        help=_("Keep existing images (don't overwrite)"))
    parser.add_option("-l", action="store",
        dest="locale",
        default='default',
        type="string",
        help=_("Specify locale language (for example en or en_GB)"))
    parser.add_option("-n", "--inspect", action="store_true",
        dest="image_inspector",
        default=False,
        help=_("Inspect metadata (requires exif & iptc plugin)"))
    parser.add_option("--no-save", action="store_true",
        dest="no_save",
        default=False,
        help=_("No save action required at the end"))
    parser.add_option("-r", "--recursive", action="store_true",
        dest="recursive",
        default=False,
        help=_("Include all subfolders"))
    parser.add_option("-t", "--trust", action="store_false",
        dest="check_images_first",
        default=True,
        help=_("Do not check images first"))
    parser.add_option("--unsafe", action="store_false",
        dest="safe",
        default=True,
        help=_("Allow Geek action and unsafe expressions"))
    parser.add_option("-v", "--verbose", action="store_true",
        dest="verbose",
        default=False,
        help=_("Verbose"))
    options, paths = parser.parse_args()
    paths = [fix_path(path) for path in paths if path and path[0] != '%']
    return options, paths


def reexec_with_pythonw(f=None):
    """'pythonw' needs to be called for any wxPython app
    to run from the command line on Mac Os X."""
    if sys.version.split(' ')[0] < '2.5' and sys.platform == 'darwin' and\
           not (sys.executable.endswith('/Python') or hasattr(sys, 'frozen')):
        sys.stderr.write('re-executing using pythonw')
        if not f:
            f = __file__
        os.execvp('pythonw', ['pythonw', f] + sys.argv[1:])


def console(config_paths):
    main(config_paths, app_file=None, gui=True)


PYWX_ERROR = """\
Only the command line package 'phatch-cli' seems to be installed.
Please install the graphical user interface package 'phatch' as well.
"""


def import_pyWx():
    try:
        from pyWx import gui
    except ImportError:
        sys.exit(PYWX_ERROR)
    return gui


def _gui(app_file, paths, settings):
    reexec_with_pythonw(app_file)  # ensure pythonw for mac
    gui = import_pyWx()
    if paths:
        actionlist = paths[0]
    else:
        actionlist = ''
    gui.main(settings, actionlist)


def _init_fonts():
    config.verify_app_user_paths()
    from lib.fonts import font_dictionary
    font_dictionary(force=True)


def _inspect(app_file, paths):
    reexec_with_pythonw(app_file)  # ensure pythonw for mac
    gui = import_pyWx()
    gui.inspect(paths)


def _droplet(app_file, paths, settings):
    reexec_with_pythonw(app_file)  # ensure pythonw for mac
    gui = import_pyWx()
    gui.drop(actionlist=paths[0], paths=paths[1:], settings=settings)


def has_ext(path, ext):
    return path.lower().endswith(ext)


def _console(paths, settings):
    from core.api import init
    init()
    from console import console
    if paths and has_ext(paths[0], INFO['extension']):
        console.main(actionlist=paths[0], paths=paths[1:], settings=settings)
    else:
        console.main(actionlist='', paths=paths, settings=settings)


def main(config_paths, app_file):
    """init should be called first!"""
    parse_locale(config_paths)
    options, paths = parse_options()
    from core.settings import create_settings
    settings = create_settings(config_paths, options)
    if settings['verbose']:
        from lib import system
        system.VERBOSE = True
    if 'safe' in settings:
        from lib import formField
        formField.set_safe(settings['safe'])
        del settings['safe']
    if settings['image_inspector']:
        _inspect(app_file, paths)
        return
    if settings['init_fonts']:
        _init_fonts()
        return
    else:
        config.check_fonts()
    if paths and not (paths[0] == 'recent' or \
            has_ext(paths[0], INFO['extension'])):
        settings['droplet'] = True
        paths.insert(0, 'recent')
    if settings['droplet']:
        if not paths:
            paths = ['recent']
        _droplet(app_file, paths, settings)
    elif len(paths) > 1 or settings['console'] or settings['interactive']:
        _console(paths, settings)
    else:
        _gui(app_file, paths, settings)

if __name__ == '__main__':
    main()
