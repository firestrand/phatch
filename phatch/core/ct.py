# Phatch - Photo Batch Processor
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

try:
    _
except NameError:
    _ = unicode

import os
import sys
from data import license
from data.info import INFO
from lib.reverse_translation import _t
from config import USER_PATH, USER_DATA_PATH, USER_CONFIG_PATH,\
    USER_CACHE_PATH, USER_ACTIONLISTS_PATH, USER_ACTIONS_PATH,\
    USER_BIN_PATH, USER_FONTS_PATH, USER_HIGHLIGHTS_PATH, \
    USER_LOG_PATH, USER_MASKS_PATH, USER_SETTINGS_PATH, \
    USER_WATERMARKS_PATH

#---description
DESKTOP_ENTRY_COMMENT = _('Easily batch process images and edit metadata')
DESCRIPTION = _('Photo Batch Processor')
LICENSE = license.GPL
CONTACT = '%(author)s <%(author_email)s>' % INFO

TITLE = '%(name)s' % INFO
COPYRIGHT = '%(copyright)s (%(url)s)' % INFO
EXTENSION = '%(extension)s' % INFO
FRAME_TITLE = '%%s%%s - %s' % TITLE
SEND_MAIL = 'mailto:%(author_email)s?subject=%%s&body=%%s' % INFO

PLATFORM = sys.platform

if PLATFORM.startswith('darwin'):
    LINUX, WINDOWS, MAC = False, False, True
    PLATFORM = 'mac'
elif PLATFORM.startswith('win'):
    LINUX, WINDOWS, MAC = False, True, False
    PLATFORM = 'windows'
else:
    LINUX, WINDOWS, MAC = True, False, False
    PLATFORM = 'linux'

#---fields
ACTION = 'Action'

#i8n
BOOLEANS = [_t('True'), _t('False'), _t('true'), _t('false')]
UNKNOWN = _("Unsaved Action List")
WILDCARD = "%s (*%s)|*%s|%s|*" \
                            % (_("Action Lists"), EXTENSION, EXTENSION, \
                                _("All Files"))
ACTION_LIST_DESCRIPTION = _("Describe here the action list.")
SAVE_ACTION_NEEDED = _("There should be a 'Save' action at the end.")


#---paths
if hasattr(sys, "frozen"):
    FILE = sys.argv[0]
else:
    FILE = __file__
PATH = os.path.dirname(os.path.dirname(FILE))
PHATCH_ACTIONS_PATH = os.path.join(PATH, 'actions')

PATH_DELIMITER = ';'

LABEL_PHATCH_ACTIONLIST = '%s %s %%s...' % (INFO['name'], _('with'))
LABEL_PHATCH_RECENT = _('%s Recent') % INFO['name']
LABEL_PHATCH_INSPECTOR = _('Image Inspector')

INTEGRATE_PHATCH_ACTIONLIST = _("Associate Images with Action List in %s...")
INTEGRATE_PHATCH_RECENT = \
                    _("Associate Images with Recent Action Lists in %s...")
INTEGRATE_PHATCH_INSPECTOR = \
                    _("Associate Images with Image Inspector in %s...")
INTEGRATE_PHATCH_REMOVE = _("Remove Association from %s...")

DROPLET_PHATCH_ACTIONLIST = _("&Action List Droplet...")
DROPLET_PHATCH_RECENT = _("&Recent Droplet...")
DROPLET_PHATCH_INSPECTOR = _("&Image Inspector Droplet...")

#---droplets
if sys.platform.startswith('win'):
    COMMAND_PATH = 'pythonw.exe'
    COMMAND_ARGUMENTS_PREFIX = '"%s" ' % os.path.abspath(sys.argv[0])
    COMMAND_FILE = ''
else:
    COMMAND_PATH = 'phatch'
    COMMAND_ARGUMENTS_PREFIX = ''
    COMMAND_FILE = '%F'

#xubuntu doesn't handle %U
COMMAND_ARGUMENTS = {
                                'DROP': '-d "%s"',
                                'RECENT': '-d recent',
                                'INSPECTOR': '-n',
}
for key, value in COMMAND_ARGUMENTS.items():
    new_value = COMMAND_ARGUMENTS_PREFIX + value
    if COMMAND_FILE:
        if '%' in new_value:
            new_value += ' ' + COMMAND_FILE.replace('%', '%%')
        else:
            new_value += ' ' + COMMAND_FILE
    COMMAND_ARGUMENTS[key] = new_value

COMMAND = {}
for key, value in COMMAND_ARGUMENTS.items():
    COMMAND[key] = COMMAND_PATH + ' ' + COMMAND_ARGUMENTS[key]

##COMMAND_DROP = 'phatch -d "%s" %%F'
##COMMAND_RECENT = 'phatch -d recent %F'
##COMMAND_INSPECTOR = 'phatch -n %F'

DESCRIPTION_RECENT = _('Batch process with recent action lists')
DESCRIPTION_INSPECTOR = _('Inspect EXIF &amp; IPTC tags')
