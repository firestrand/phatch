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

import codecs
import os
from core.ct import USER_PATH
from lib.unicoding import ENCODING

TEMPLATE = """
from urllib import unquote
from subprocess import call
import nautilus
%(preload)s

class %(name)s_extension(nautilus.MenuProvider):
    def __init__(self):
        pass

    def menu_activate_cb(self, menu, files):
        for file in files:
            if file.is_gone():
                return
        files = ["'%%s'"%%unquote(file.get_uri()[7:]) for file in files]
        call('%(command)s'%%' '.join(files),shell=True)

    def get_file_items(self, window, files):
        #only directories and readable image files are accepted
        files = [file for file in files \
            if (file.get_uri_scheme() == 'file' and
            file.get_mime_type() in %(mimetypes)s)]
        #return if nothing to do
        if not files: return
        #install menu
        item = nautilus.MenuItem('NautilusPython::%(name)s',
                                 %(label)s,
                                 %(tooltip)s)
        #bind/connect menu item with method
        item.connect('activate', self.menu_activate_cb, files)
        #return menu item
        return item,
"""

NAUTILUS_USER_PYTHON_EXTENSIONS = os.path.join(USER_PATH, '.nautilus',
    'python-extensions')


def nautilus_exists():
    return os.path.isdir(NAUTILUS_USER_PYTHON_EXTENSIONS)


def create_nautilus_extension(name, label, command, mimetypes, tooltip='',
        preload='', encoding=ENCODING):
    params = {
        'name': name,
        'label': label,
        'command': command,
        'mimetypes': mimetypes,
        'tooltip': tooltip,
        'preload': preload, }
    script = TEMPLATE % params
    filename = os.path.join(NAUTILUS_USER_PYTHON_EXTENSIONS, name + '.py')
    extension = codecs.open(filename, 'wb', encoding=ENCODING)
    extension.write(script)
    extension.close()
