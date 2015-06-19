# Copyright (C) 2007-2008 www.stani.be
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
"""Cross platform library to locate the desktop folder."""

import os
import re
import sys

# user folder
USER_FOLDER = os.path.expanduser('~')
try:
    USER_FOLDER = USER_FOLDER.decode(sys.getfilesystemencoding())
except:
    pass


# desktop folder
if sys.platform.startswith('win'):
    # Windows
    try:
        from win32com.shell import shell, shellcon
        DESKTOP_FOLDER = shell.SHGetFolderPath(0,
            shellcon.CSIDL_DESKTOP, None, 0)
    except ImportError:
        #FIXME (Windows 7)
        DESKTOP_FOLDER = os.path.join(USER_FOLDER, 'Desktop')
        #DESKTOP_FOLDER = "C:\\"
elif sys.platform.startswith('darwin'):
    # Mac: verify this!
    DESKTOP_FOLDER = os.path.expanduser('~/Desktop')
else:
    # Linux
    DESKTOP_FOLDER = os.path.expanduser('~/Desktop')
    user_dirs = os.path.expanduser('~/.config/user-dirs.dirs')
    if os.path.exists(user_dirs):
        match = re.search('XDG_DESKTOP_DIR="(.*?)"',
                    open(user_dirs).read())
        if match:
            DESKTOP_FOLDER = os.path.expanduser(
                match.group(1).replace('$HOME', '~'))
    del user_dirs


if not os.path.isdir(DESKTOP_FOLDER):
    DESKTOP_FOLDER = USER_FOLDER


def _env(var, *paths):
    paths = (USER_FOLDER, ) + paths
    return os.environ.get(var, os.path.join(*paths))


# free desktop specifcation (xdg folders)
if sys.platform.startswith('linux'):
    USER_DATA_FOLDER = _env('XDG_DATA_HOME',
                            USER_FOLDER, '.local', 'share')
    USER_CONFIG_FOLDER = _env('XDG_CONFIG_HOME', '.config')
    USER_CACHE_FOLDER = _env('XDG_CACHE_HOME', '.cache')
else:
    #TODO: what would be the best user path for these platforms?
    USER_DATA_FOLDER = USER_CONFIG_FOLDER = USER_CACHE_FOLDER =\
        USER_FOLDER


# thumbnail folder
USER_THUMBNAILS_NORMAL_FOLDER = os.path.join(USER_FOLDER,
    '.thumbnails', 'normal')
if not os.path.isdir(USER_THUMBNAILS_NORMAL_FOLDER):
    USER_THUMBNAILS_NORMAL_FOLDER = None


if __name__ == '__main__':
    sys.stdout.write('Your desktop is: %s\n' % DESKTOP_FOLDER)
