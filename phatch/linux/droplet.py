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
import wx
from core import ct
from lib.reverse_translation import _t
from core.config import SYSTEM_INSTALL
from lib import system
from lib.linux.desktop import create_droplet
from lib.unicoding import exception_to_unicode
from lib.formField import IMAGE_READ_MIMETYPES

try:
    from thunar import thunar_exists, create_thunar_action
except ImportError:

    def thunar_exists():
        return False

try:
    from lib.linux.nautilusExtension import nautilus_exists, \
                                                create_nautilus_extension
except ImportError:

    def nautilus_exists():
        return False

WX_ENCODING = wx.GetDefaultPyEncoding()


#---general
def menu_action(self, program, comment, method, *args, **keyw):
    try:
        success = method(*args, **keyw)
        self.show_info(_('If you restart %s, '
            'the action will appear in the context menu.') % program + comment)
    except Exception, details:
        reason = exception_to_unicode(details, WX_ENCODING)
        self.show_error(_('Phatch could not install the action in %s:')\
            % program + '\n\n' + reason)

#---droplet


def create_phatch_droplet(actionlist, folder, icon='phatch'):
    """"""
    create_droplet(
        name=system.filename_to_title(actionlist),
        command=ct.COMMAND['DROP'] % actionlist,
        folder=folder,
        icon=icon,
    )


def create_phatch_recent_droplet(folder, icon='phatch'):
    """"""
    create_droplet(
        name=ct.LABEL_PHATCH_RECENT,
        command=ct.COMMAND['RECENT'],
        folder=folder,
        icon=icon,
    )


def create_phatch_inspector_droplet(folder, icon='phatch'):
    """"""
    create_droplet(
        name=ct.LABEL_PHATCH_INSPECTOR,
        command=ct.COMMAND['INSPECTOR'],
        folder=folder,
        icon=icon,
    )


def on_menu_file_export_droplet_actionlist(self, event):
    if self.is_save_not_ok():
        return
    self.menu_file_export_droplet(create_phatch_droplet, self.filename)


def on_menu_file_export_droplet_recent(self, event):
    self.menu_file_export_droplet(create_phatch_recent_droplet)


def on_menu_file_export_droplet_inspector(self, event):
    self.menu_file_export_droplet(create_phatch_inspector_droplet)

#---thunar


def create_phatch_thunar_action(actionlist, description='', icon='phatch'):
    """"""
    return create_thunar_action(
        name=ct.LABEL_PHATCH_ACTIONLIST % system.filename_to_title(actionlist),
        description=description,
        command=ct.COMMAND['DROP'] % actionlist,
        icon=icon,
        types='<directories/><image-files/>',
    )


def create_phatch_recent_thunar_action(icon='phatch'):
    """"""
    return create_thunar_action(
        name=ct.LABEL_PHATCH_RECENT + '...',
        description=ct.DESCRIPTION_RECENT,
        command=ct.COMMAND['RECENT'],
        icon=icon,
        types='<directories/><image-files/>',
    )


def create_phatch_inspect_thunar_action(icon='phatch'):
    """"""
    return create_thunar_action(
        name=ct.INFO['name'] + ' ' + ct.LABEL_PHATCH_INSPECTOR + '...',
        description=ct.DESCRIPTION_INSPECTOR,
        command=ct.COMMAND['INSPECTOR'],
        icon=icon,
        types='<image-files/>',
    )


def on_menu_file_export_thunar_actionlist(self, event):
    if self.is_save_not_ok():
        return
    menu_action(self, 'Thunar', '', create_phatch_thunar_action, self.filename,
        description='')


def on_menu_file_export_thunar_recent(self, event):
    menu_action(self, 'Thunar', '', create_phatch_recent_thunar_action)


def on_menu_file_export_thunar_inspector(self, event):
    menu_action(self, 'Thunar', '', create_phatch_inspect_thunar_action)

#---nautilus
REQUIRES_PYTHON_NAUTILUS = '\n\n(%s)' % \
    _('This requires also that the python-nautilus package is installed.')
TOOLTIP = '_("%s")' % _t('Batch process images with Phatch')
PRELOAD = """
from phatch.core.config import load_locale_only
load_locale_only()"""


def create_phatch_nautilus_action(actionlist):
    name = os.path.splitext(os.path.basename(actionlist))[0]
    title = system.title(name)
    create_nautilus_extension(
        name='phatch_actionlist_' + \
                        name.encode('ascii', 'ignore'),
        label='_("%s") + "..."' % _t('Phatch with %s') % title,
        command='phatch -d "%s" %%s &' % actionlist,
        mimetypes=IMAGE_READ_MIMETYPES,
        tooltip=TOOLTIP,
        preload=PRELOAD,
    )


def create_phatch_recent_nautilus_action():
    create_nautilus_extension(
        name='phatch_recent',
        label='_("%s") + "..."' % \
                        _t('Process with recent Phatch action list'),
        command='phatch -d recent %s &',
        mimetypes=IMAGE_READ_MIMETYPES,
        tooltip=TOOLTIP,
        preload=PRELOAD,
    )


def create_phatch_inspect_nautilus_action():
    create_nautilus_extension(
        name='phatch_image_inspector',
        label='_("%s") + "..."' % \
                        _t('Inspect with Phatch'),
        command='phatch -n %s &',
        mimetypes=IMAGE_READ_MIMETYPES,
        tooltip='_("%s")' % _t('Inspect EXIF & IPTC tags'),
        preload=PRELOAD,
    )


def on_menu_file_export_nautilus_actionlist(self, event):
    if self.is_save_not_ok():
        return
    menu_action(self, 'Nautilus', REQUIRES_PYTHON_NAUTILUS,
        create_phatch_nautilus_action, self.filename)


def on_menu_file_export_nautilus_recent(self, event):
    menu_action(self, 'Nautilus', REQUIRES_PYTHON_NAUTILUS,
    create_phatch_recent_nautilus_action)


def on_menu_file_export_nautilus_inspector(self, event):
    menu_action(self, 'Nautilus', REQUIRES_PYTHON_NAUTILUS,
    create_phatch_inspect_nautilus_action)

#---install


def install_menu_item(self, menu, name, label, tooltip="",
        style=wx.ITEM_NORMAL):
    method = globals()['on_' + name]
    return self.install_menu_item(menu, name, label, method, tooltip, style)


def install(self):
    #install menu items in reverse order

    #thunar
    if thunar_exists():
        install_menu_item(self, self.menu_file_export,
            name='menu_file_export_thunar_inspector',
            label=ct.INTEGRATE_PHATCH_INSPECTOR % "Thuna&r",
        )
        install_menu_item(self, self.menu_file_export,
            name='menu_file_export_thunar_recent',
            label=ct.INTEGRATE_PHATCH_RECENT % "T&hunar",
        )
        self.menu_item.append((self.menu_file_export,
            [install_menu_item(self, self.menu_file_export,
                name='menu_file_export_thunar_actionlist',
                label=ct.INTEGRATE_PHATCH_ACTIONLIST % "&Thunar",
            )]))
        self.menu_file_export.InsertSeparator(3)

    #nautilus
    if nautilus_exists():
        if not SYSTEM_INSTALL:
            install_menu_item(self, self.menu_file_export,
                name='menu_file_export_nautilus_inspector',
                label=ct.INTEGRATE_PHATCH_INSPECTOR % "Nautil&us",
            )
            install_menu_item(self, self.menu_file_export,
                name='menu_file_export_nautilus_recent',
                label=ct.INTEGRATE_PHATCH_RECENT % "Nauti&lus",
            )
        self.menu_item.append((self.menu_file_export,
            [install_menu_item(self, self.menu_file_export,
                name='menu_file_export_nautilus_actionlist',
                label=ct.INTEGRATE_PHATCH_ACTIONLIST % "Nautilu&s",
            )]))
        if SYSTEM_INSTALL:
            separator = 1
        else:
            separator = 3
        self.menu_file_export.InsertSeparator(separator)

    #droplet
    install_menu_item(self, self.menu_file_export,
        name='menu_file_export_droplet_inspector',
        label=ct.DROPLET_PHATCH_INSPECTOR,
    )
    install_menu_item(self, self.menu_file_export,
        name='menu_file_export_droplet_recent',
        label=ct.DROPLET_PHATCH_RECENT,
    )
    self.menu_item.append((self.menu_file_export,
        [install_menu_item(self, self.menu_file_export,
            name='menu_file_export_droplet_actionlist',
            label=ct.DROPLET_PHATCH_ACTIONLIST,
        )]))
    self.menu_file_export.InsertSeparator(3)


if __name__ == '__main__':
    create_phatch_droplet(
        actionlist=''.join('/home/stani/sync/python/phatch/action ',
            'lists/tutorials/thumb round 3d reflect.phatch'),
        folder='/home/stani/sync/Desktop',
    )
