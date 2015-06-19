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

try:
    import _winreg
except ImportError:
    _winreg = None


class RegistryApplication:
    name = ''
    filename = ''

    def get_path(self, reg):
        pass


class Blender(RegistryApplication):
    name = 'blender'
    filename = 'blendfile'

    def get_path(self, reg):
        return _winreg.QueryValue(reg, 'DefaultIcon').rsplit(',', 1)[0]


class Inkscape(RegistryApplication):
    name = 'inkscape'
    filename = 'svgfile\\shell\edit'

    def get_path(self, reg):
        return _winreg.QueryValue(reg, 'command').rsplit(' ', 1)[0].strip('"')


class Applications(dict):

    def __init__(self):
        apps = (Blender(), Inkscape())

        for app in apps:
            self[app.name] = app


apps = Applications()


def find_exe(app_name):
    if app_name in apps:
        app = apps[app_name]

        try:
            reg = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, app.filename)
            value = app.get_path(reg)
            _winreg.CloseKey(reg)

            return value
        except:
            pass
    return None
