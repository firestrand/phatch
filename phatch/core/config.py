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

import gettext
import glob
import locale
import os
import subprocess
import shutil
import sys

from lib import desktop
from lib import system
from lib.unicoding import ensure_unicode

#-- nosetests


class Paths:

    def __getitem__(self, key):
        return 'path'

USER_PATH = desktop.USER_FOLDER
PATHS = Paths()
PHATCH_ACTIONLISTS_PATH = '.'


def _wrap(path):
    return os.path.join(path, 'phatch')


USER_CACHE_PATH = _wrap(desktop.USER_CACHE_FOLDER)
USER_FONTS_CACHE_PATH = os.path.join(USER_CACHE_PATH, 'fonts.cache')
USER_LOG_PATH = os.path.join(USER_CACHE_PATH, 'log')
USER_PREVIEW_PATH = os.path.join(USER_CACHE_PATH, 'preview')

USER_CONFIG_PATH = _wrap(desktop.USER_CONFIG_FOLDER)
USER_SETTINGS_PATH = os.path.join(USER_CONFIG_PATH, 'settings.py')

USER_DATA_PATH = _wrap(desktop.USER_DATA_FOLDER)
USER_ACTIONS_PATH = os.path.join(USER_DATA_PATH, 'actions')
USER_ACTIONLISTS_PATH = os.path.join(USER_DATA_PATH, 'actionlists')
USER_BIN_PATH = os.path.join(USER_DATA_PATH, 'bin')
USER_FONTS_PATH = os.path.join(USER_DATA_PATH, 'fonts')
USER_GEEK_PATH = os.path.join(USER_DATA_PATH, 'geek.txt')
USER_MASKS_PATH = os.path.join(USER_DATA_PATH, 'masks')
USER_HIGHLIGHTS_PATH = os.path.join(USER_DATA_PATH, 'highlights')
USER_WATERMARKS_PATH = os.path.join(USER_DATA_PATH, 'watermarks')

SYSTEM_INSTALL = False


def verify_app_user_paths():
    """Create user path structure if it does not exist yet. If there
    are new action lists in the phatch library, copy them to the user
    folder.
    """
    # fixme: better use setting, path retrieval should be cleaned
    for path in [USER_DATA_PATH, USER_CONFIG_PATH,
            USER_CACHE_PATH, USER_ACTIONLISTS_PATH,
            USER_ACTIONS_PATH, USER_BIN_PATH, USER_BIN_PATH,
            USER_FONTS_PATH, USER_MASKS_PATH,
            USER_HIGHLIGHTS_PATH, USER_WATERMARKS_PATH]:
        if 0:  # and path == USER_ACTIONLISTS_PATH:
            # DISABLED
            # copy action lists from the phatch root to user
            if os.path.exists(path):
                existing = os.listdir(path)
                for al in os.listdir(PHATCH_ACTIONLISTS_PATH):
                    if not (al in existing):
                        shutil.copyfile(
                            os.path.join(PHATCH_ACTIONLISTS_PATH, al),
                            os.path.join(path, al))
            else:
                shutil.copytree(PHATCH_ACTIONLISTS_PATH, path)
        else:
            #create when they don't exist
            system.ensure_path(path)
    geek = 'geek.txt'
    if not os.path.isfile(USER_GEEK_PATH):
        shutil.copyfile(os.path.join(PHATCH_DATA_PATH, geek),
            USER_GEEK_PATH)


def check_config_paths(config_paths):
    global SYSTEM_INSTALL
    global PHATCH_DATA_PATH
    global PHATCH_FONTS_PATH
    global PHATCH_FONTS_CACHE_PATH
    global PHATCH_ACTIONLISTS_PATH
    if config_paths:
        # Phatch is not installed system wide but is run from user folder
        SYSTEM_INSTALL = False
        PHATCH_DATA_PATH = config_paths['PHATCH_DATA_PATH']
        PHATCH_FONTS_PATH = config_paths['PHATCH_FONTS_PATH']
        PHATCH_FONTS_CACHE_PATH = config_paths['PHATCH_FONTS_CACHE_PATH']
        PHATCH_ACTIONLISTS_PATH = config_paths['PHATCH_ACTIONLISTS_PATH']
        return config_paths
    SYSTEM_INSTALL = True
    ROOT_SHARE_PATH = os.path.join(sys.prefix, "share")  # for win?
    PHATCH_SHARE_PATH = os.path.join(ROOT_SHARE_PATH, "phatch")
    PHATCH_DATA_PATH = os.path.join(PHATCH_SHARE_PATH, "data")
    PHATCH_ACTIONLISTS_PATH = os.path.join(PHATCH_DATA_PATH,
                                    'actionlists')
    PHATCH_BLENDER_PATH = os.path.join(PHATCH_DATA_PATH, "blender")
    PHATCH_FONTS_PATH = os.path.join(PHATCH_DATA_PATH, "fonts")
    PHATCH_FONTS_CACHE_PATH = os.path.join(PHATCH_SHARE_PATH,
                            "cache", "fonts")

    if sys.platform.startswith('win'):
        sys.stderr.write(
            'Sorry your platform is not yet supported.\n' \
            + 'The instructions for Windows are on the Phatch website.')
        sys.exit()
    else:
        return {
            'PHATCH_IMAGE_PATH': os.path.join(PHATCH_SHARE_PATH,
                                    'images'),
            'PHATCH_LOCALE_PATH': os.path.join(ROOT_SHARE_PATH,
                                    'locale'),
            'PHATCH_DOCS_PATH': os.path.join(ROOT_SHARE_PATH,
                                    'doc', 'phatch', 'html'),
            #cache
            'PHATCH_FONTS_CACHE_PATH': PHATCH_FONTS_CACHE_PATH,
            #data
            'PHATCH_DATA_PATH': PHATCH_DATA_PATH,
            'PHATCH_ACTIONLISTS_PATH': PHATCH_ACTIONLISTS_PATH,
            'PHATCH_BLENDER_PATH': PHATCH_BLENDER_PATH,
            'PHATCH_FONTS_PATH': PHATCH_FONTS_PATH,
            'PHATCH_HIGHLIGHTS_PATH': os.path.join(PHATCH_DATA_PATH,
                                    'highlights'),
            'PHATCH_MASKS_PATH': os.path.join(PHATCH_DATA_PATH,
                                    'masks'),
            'PHATCH_PERSPECTIVE_PATH': os.path.join(PHATCH_DATA_PATH,
                                    'perspective'),
        }


def add_user_paths(config_paths):
    config_paths.update({
        'USER_PATH': USER_PATH,
        'USER_ACTIONS_PATH': USER_ACTIONS_PATH,
        'USER_BIN_PATH': USER_BIN_PATH,
        'USER_DATA_PATH': USER_DATA_PATH,
        'USER_FONTS_PATH': USER_FONTS_PATH,
        'USER_GEEK_PATH': USER_GEEK_PATH,
        'USER_LOG_PATH': USER_LOG_PATH,
        'USER_FONTS_CACHE_PATH': USER_FONTS_CACHE_PATH,
        'USER_MASKS_PATH': USER_MASKS_PATH,
        'USER_HIGHLIGHTS_PATH': USER_HIGHLIGHTS_PATH,
        'USER_PREVIEW_PATH': USER_PREVIEW_PATH,
        'USER_SETTINGS_PATH': USER_SETTINGS_PATH,
        'USER_WATERMARKS_PATH': USER_WATERMARKS_PATH,
    })


def fix_python_path(phatch_python_path=None):
    if not phatch_python_path:
        phatch_python_path = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
    if not(phatch_python_path in [ensure_unicode(x) for x in sys.path]):
        sys.path.insert(0, phatch_python_path)
    return phatch_python_path


def load_locale(app, path, canonical='default', unicode=True):
    locale.setlocale(locale.LC_ALL, '')
    #get default canonical if necessary
    if canonical == 'default':
        canonical = locale.getdefaultlocale(envvars=('LC_ALL', 'LANG'))[0]
        if canonical is None:
            #for mac
            canonical = 'en'
    #canonical = 'zh' #to test unicode languages
    #expand with similar translations
    base = canonical.split('_')[0]  # eg pt_BR -> pt
    base_path = os.path.join(path, base)
    languages = [base_path] + \
        [os.path.basename(x) for x in glob.glob(base_path + '_*')]
    #ensure canonical is the first element (base the second)
    if canonical in languages:
        languages.remove(canonical)
    languages.insert(0, canonical)
    #install
    i18n = gettext.translation(app, path, languages=languages, fallback=1)
    i18n.install(unicode=unicode)


def init_config_paths(config_paths=None):
    if config_paths is None:
        config_paths = {}
    #check paths
    config_paths = check_config_paths(config_paths)
    add_user_paths(config_paths)
    #configure sys.path
    phatch_path = fix_python_path(config_paths.get('PHATCH_PYTHON_PATH', None))
    #patches for pil <= 1.1.6 (ImportError=skip during build process)
    try:
        import Image
        if Image.VERSION < '1.1.7':
            fix_python_path(os.path.join(phatch_path, 'other', 'pil_1_1_6'))
    except ImportError:
        pass
    #user actions
    fix_python_path(USER_ACTIONS_PATH)
    #set font cache
    from lib.fonts import set_font_cache
    set_font_cache(USER_FONTS_PATH, PHATCH_FONTS_PATH,
        USER_FONTS_CACHE_PATH, PHATCH_FONTS_CACHE_PATH)
    #register paths
    global PATHS
    PATHS = config_paths
    #return values
    return config_paths


def load_locale_only(config_paths=None):
    if config_paths is None:
        config_paths = {}
    config_paths = check_config_paths(config_paths)
    load_locale('phatch', config_paths['PHATCH_LOCALE_PATH'])


def check_fonts(force=False):
    from core.config import USER_FONTS_CACHE_PATH, PHATCH_FONTS_CACHE_PATH
    if force or not(os.path.exists(USER_FONTS_CACHE_PATH) or \
            os.path.exists(PHATCH_FONTS_CACHE_PATH)):
        subprocess.Popen([sys.executable,
            os.path.abspath(sys.argv[0]), '--fonts'])
