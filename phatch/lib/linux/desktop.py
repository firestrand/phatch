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

DROPLET = \
"""#!/usr/bin/env xdg-open
[Desktop Entry]
Version=1.0
Type=Application
Name=%(name)s
Terminal=false
Exec=%(command)s
Icon=%(icon)s"""


def create_droplet(name, command, folder='~/Desktop',
        icon='gnome-panel-launcher.svg'):
    filename = os.path.join(folder, name + '.desktop')
    data = {'name': name, 'icon': icon, 'command': command}
    droplet = open(filename, 'w')
    droplet.write(DROPLET % data)
    droplet.close()
    os.chmod(filename, 0755)
