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

import contextlib
import gettext
import glob
import locale
import os
import subprocess
import sys
from pathlib import Path

from phatch.core.filesystem import atomic_write_bytes
from phatch.core.resource_config import direct_config_paths
from phatch.core.user_paths import (
    PathResolution,
    current_platform,
    initialize_user_paths,
    resolve_user_paths,
)
from phatch.lib.unicoding import ensure_unicode

# -- nosetests


class Paths:
    def __getitem__(self, key):
        return "path"


class StartupResourceError(RuntimeError):
    def __init__(self, resource, source, destination, error):
        self.resource = resource
        self.source = source
        self.destination = destination
        self.error = error
        super().__init__(
            f"Unable to initialize required resource {resource} from {source}: {error}"
        )


USER_PATH = ""
PATHS = Paths()
PHATCH_ACTIONLISTS_PATH = "."


def _wrap(path):
    return os.path.join(path, "phatch")


USER_CACHE_PATH = ""
USER_FONTS_CACHE_PATH = ""
USER_LOG_PATH = ""
USER_PREVIEW_PATH = ""
USER_CONFIG_PATH = ""
USER_SETTINGS_PATH = ""
USER_DATA_PATH = ""
USER_ACTIONS_PATH = ""
USER_ACTIONLISTS_PATH = ""
USER_BIN_PATH = ""
USER_FONTS_PATH = ""
USER_GEEK_PATH = ""
USER_MASKS_PATH = ""
USER_HIGHLIGHTS_PATH = ""
USER_WATERMARKS_PATH = ""
USER_PATHS = None

SYSTEM_INSTALL = False

# These will be set by check_config_paths()
PHATCH_DATA_PATH = None
PHATCH_FONTS_PATH = None
PHATCH_FONTS_CACHE_PATH = None
PHATCH_ACTIONLISTS_PATH = None


def verify_app_user_paths():
    """Create user path structure if it does not exist yet. If there
    are new action lists in the phatch library, copy them to the user
    folder.
    """
    if USER_PATHS is None:
        raise RuntimeError("User paths have not been initialized")
    if PHATCH_DATA_PATH is None:
        raise RuntimeError("Application data path has not been initialized")
    initialize_user_paths(USER_PATHS)
    if not USER_PATHS.geek.is_file():
        source = Path(PHATCH_DATA_PATH) / "geek.txt"
        try:
            atomic_write_bytes(USER_PATHS.geek, source.read_bytes())
        except OSError as error:
            raise StartupResourceError(
                "geek.txt", source, USER_PATHS.geek, error
            ) from error


def check_config_paths(config_paths):
    global SYSTEM_INSTALL
    global PHATCH_DATA_PATH
    global PHATCH_FONTS_PATH
    global PHATCH_FONTS_CACHE_PATH
    global PHATCH_ACTIONLISTS_PATH
    if config_paths:
        # Phatch is not installed system wide but is run from user folder
        SYSTEM_INSTALL = False
        PHATCH_DATA_PATH = config_paths["PHATCH_DATA_PATH"]
        PHATCH_FONTS_PATH = config_paths["PHATCH_FONTS_PATH"]
        PHATCH_FONTS_CACHE_PATH = config_paths["PHATCH_FONTS_CACHE_PATH"]
        PHATCH_ACTIONLISTS_PATH = config_paths["PHATCH_ACTIONLISTS_PATH"]
        return config_paths
    SYSTEM_INSTALL = True
    if sys.platform.startswith("win"):
        sys.stderr.write(
            "Sorry your platform is not yet supported.\n"
            + "The instructions for Windows are on the Phatch website."
        )
        sys.exit()
    packaged_paths = direct_config_paths()
    PHATCH_DATA_PATH = packaged_paths["PHATCH_DATA_PATH"]
    PHATCH_ACTIONLISTS_PATH = packaged_paths["PHATCH_ACTIONLISTS_PATH"]
    PHATCH_FONTS_PATH = packaged_paths["PHATCH_FONTS_PATH"]
    PHATCH_FONTS_CACHE_PATH = packaged_paths["PHATCH_FONTS_CACHE_PATH"]
    return packaged_paths


def _set_user_paths(user_paths):
    global USER_PATHS, USER_PATH, USER_CACHE_PATH, USER_FONTS_CACHE_PATH
    global USER_LOG_PATH, USER_PREVIEW_PATH, USER_CONFIG_PATH, USER_SETTINGS_PATH
    global USER_DATA_PATH, USER_ACTIONS_PATH, USER_ACTIONLISTS_PATH, USER_BIN_PATH
    global USER_FONTS_PATH, USER_GEEK_PATH, USER_MASKS_PATH
    global USER_HIGHLIGHTS_PATH, USER_WATERMARKS_PATH
    USER_PATHS = user_paths
    USER_PATH = str(user_paths.home)
    USER_CACHE_PATH = str(user_paths.cache)
    USER_FONTS_CACHE_PATH = str(user_paths.font_index)
    USER_LOG_PATH = str(user_paths.logs / "phatch.log")
    USER_PREVIEW_PATH = str(user_paths.previews)
    USER_CONFIG_PATH = str(user_paths.config)
    USER_SETTINGS_PATH = str(user_paths.settings)
    USER_DATA_PATH = str(user_paths.data)
    USER_ACTIONS_PATH = str(user_paths.actions)
    USER_ACTIONLISTS_PATH = str(user_paths.actionlists)
    USER_BIN_PATH = str(user_paths.binaries)
    USER_FONTS_PATH = str(user_paths.fonts)
    USER_GEEK_PATH = str(user_paths.geek)
    USER_MASKS_PATH = str(user_paths.masks)
    USER_HIGHLIGHTS_PATH = str(user_paths.highlights)
    USER_WATERMARKS_PATH = str(user_paths.watermarks)


def add_user_paths(config_paths, user_paths=None):
    if user_paths is None:
        user_paths = resolve_user_paths(PathResolution(os.environ, current_platform()))
    _set_user_paths(user_paths)
    config_paths.update(
        {
            "USER_PATH": USER_PATH,
            "USER_ACTIONS_PATH": USER_ACTIONS_PATH,
            "USER_BIN_PATH": USER_BIN_PATH,
            "USER_DATA_PATH": USER_DATA_PATH,
            "USER_CONFIG_PATH": USER_CONFIG_PATH,
            "USER_FONTS_PATH": USER_FONTS_PATH,
            "USER_GEEK_PATH": USER_GEEK_PATH,
            "USER_LOG_PATH": USER_LOG_PATH,
            "USER_FONTS_CACHE_PATH": USER_FONTS_CACHE_PATH,
            "USER_MASKS_PATH": USER_MASKS_PATH,
            "USER_HIGHLIGHTS_PATH": USER_HIGHLIGHTS_PATH,
            "USER_PREVIEW_PATH": USER_PREVIEW_PATH,
            "USER_SETTINGS_PATH": USER_SETTINGS_PATH,
            "USER_WATERMARKS_PATH": USER_WATERMARKS_PATH,
        }
    )


def fix_python_path(phatch_python_path=None):
    if not phatch_python_path:
        phatch_python_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if phatch_python_path not in [ensure_unicode(x) for x in sys.path]:
        sys.path.insert(0, phatch_python_path)
    return phatch_python_path


def _detect_default_locale():
    # First, honour environment variables
    for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(key)
        if value:
            return value.split(".")[0]

    # locale.getlocale can return (None, None) if unset; guard accordingly
    def _safe_get_locale(category=None):
        try:
            lang, _ = (
                locale.getlocale(category)
                if category is not None
                else locale.getlocale()
            )
        except (AttributeError, TypeError, ValueError):
            return None
        return lang

    for category in (None, getattr(locale, "LC_MESSAGES", None), locale.LC_CTYPE):
        lang = _safe_get_locale(category)
        if lang:
            return lang
    return None


def load_locale(app, path, canonical="default", str=True):
    with contextlib.suppress(locale.Error):
        locale.setlocale(locale.LC_ALL, "")
    # get default canonical if necessary
    if canonical == "default":
        canonical = _detect_default_locale() or "en"
    if not canonical:
        canonical = "en"
    # canonical = 'zh' # to test unicode languages
    # expand with similar translations
    base = canonical.split("_")[0]  # eg pt_BR -> pt
    base_path = os.path.join(path, base)
    languages = [base_path] + [os.path.basename(x) for x in glob.glob(base_path + "_*")]
    # ensure canonical is the first element (base the second)
    if canonical in languages:
        languages.remove(canonical)
    languages.insert(0, canonical)
    # install
    i18n = gettext.translation(app, path, languages=languages, fallback=True)
    # Python 3: install() no longer takes unicode parameter
    i18n.install()


def init_config_paths(config_paths=None, user_paths=None):
    if config_paths is None:
        config_paths = {}
    # check paths
    config_paths = check_config_paths(config_paths)
    if user_paths is None:
        add_user_paths(config_paths)
    else:
        add_user_paths(config_paths, user_paths)
    # configure sys.path
    fix_python_path(config_paths.get("PHATCH_PYTHON_PATH", None))
    # user actions
    fix_python_path(USER_ACTIONS_PATH)
    # set font cache
    from phatch.lib.fonts import set_font_cache

    set_font_cache(
        USER_FONTS_PATH,
        PHATCH_FONTS_PATH,
        USER_FONTS_CACHE_PATH,
        PHATCH_FONTS_CACHE_PATH,
    )
    # register paths
    global PATHS
    PATHS = config_paths
    legacy_constants = sys.modules.get("phatch.core.ct")
    if legacy_constants is not None:
        for name, value in config_paths.items():
            if name.startswith("USER_") and hasattr(legacy_constants, name):
                setattr(legacy_constants, name, value)
    # return values
    return config_paths


def load_locale_only(config_paths=None):
    if config_paths is None:
        config_paths = {}
    config_paths = check_config_paths(config_paths)
    load_locale("phatch", config_paths["PHATCH_LOCALE_PATH"])


def check_fonts(force=False):
    # These globals are already defined by check_config_paths()
    if PHATCH_FONTS_CACHE_PATH is None:
        raise RuntimeError("Application font cache path has not been initialized")
    if force or not (
        os.path.exists(USER_FONTS_CACHE_PATH) or os.path.exists(PHATCH_FONTS_CACHE_PATH)
    ):
        subprocess.Popen([sys.executable, os.path.abspath(sys.argv[0]), "--fonts"])
