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
#
# Follows PEP8

if __name__ == '__main__':
    import sys
    _ = unicode
    sys.path.insert(0, '../..')


END = '</actions>'

THUNAR_ACTION = \
'<action><icon>%(icon)s</icon><name>%(name)s</name>' +\
'<command>%(command)s</command>' +\
'<description>%(description)s</description>' +\
'<patterns>%(patterns)s</patterns>%(types)s</action>'

import os
import shutil
from core.ct import USER_PATH

THUNAR_USER_ACTIONS = os.path.join(USER_PATH, '.config', 'Thunar', 'uca.xml')
BACKUP = '.backup_before_phatch'


def thunar_exists():
    return os.path.isfile(THUNAR_USER_ACTIONS)


def create_thunar_action(name, command, description, types='<text-files/>',
        patterns='*', icon=''):
    if not thunar_exists():
        return False
    #action
    data = {'name': name, 'icon': icon, 'command': command,
        'description': description, 'types': types, 'patterns': patterns}
    action = THUNAR_ACTION % data
    #create actions string
    f = open(THUNAR_USER_ACTIONS, 'rb')
    actions = f.read()
    f.close()
    #check if already done
    if action in actions:
        return True
    actions = actions.replace(END, action + END)
    #write actions string
    f = open(THUNAR_USER_ACTIONS + '.phatch', 'wb')
    f.write(actions)
    f.close()
    #backup previous
    if not os.path.isfile(THUNAR_USER_ACTIONS + BACKUP):
        shutil.copy2(THUNAR_USER_ACTIONS, THUNAR_USER_ACTIONS + BACKUP)
    #overwrite with phatch actions
    os.rename(THUNAR_USER_ACTIONS + '.phatch', THUNAR_USER_ACTIONS)
    return True
