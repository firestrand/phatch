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
#
# Follows PEP8

import os
import wx
from core import ct, config
from lib import system
from lib.windows.register import register_extensions, deregister_extensions
from lib.formField import IMAGE_READ_EXTENSIONS

WX_ENCODING = wx.GetDefaultPyEncoding()
ICON = os.path.join(config.PATHS['PHATCH_IMAGE_PATH'], 'phatch.ico')
EXTENSIONS_INSTALL_SUCCESFUL =\
    _("These extensions have been succesfully installed:\n\n")
EXTENSIONS_INSTALL_UNSUCCESFUL = \
    _("Phatch did not succeed to install the requested feature.")
EXTENSIONS_UNINSTALL =\
    _("Phatch tried to uninstall itself from the Windows Explorer.")


RECENT = ct.LABEL_PHATCH_RECENT + '...'
INSPECTOR = ct.INFO['name'] + ' ' + ct.LABEL_PHATCH_INSPECTOR + '...'

_IMAGE_READ_EXTENSIONS = ['.' + ext for ext in IMAGE_READ_EXTENSIONS]
#warning win32


def win32_missing(self):
    "imports shortcut"
    global shortcut
    try:
        import lib.windows.shortcut as shortcut
        return False
    except ImportError:
        self.show_info(
        _('You need to install the Python Win32 Extensions for this feature.'))
        return True

#---droplets


def create_droplet(name, arguments, folder, description=None):
    if description is None:
        description = name
    shortcut.create(
        save_as=os.path.join(folder, name + '.lnk'),
        path=ct.COMMAND_PATH,
        arguments=arguments,
        description=description,
        icon_path=ICON,
    )

#droplet


def create_phatch_droplet(actionlist, folder):
    """"""
    name = os.path.splitext(os.path.basename(actionlist))[0]
    create_droplet(
        name=name,
        arguments=ct.COMMAND_ARGUMENTS['DROP'] % actionlist,
        folder=folder,
        description=ct.LABEL_PHATCH_ACTIONLIST % \
                    system.filename_to_title(name))


def create_phatch_recent_droplet(folder, icon=ICON):
    """"""
    create_droplet(
        name=ct.LABEL_PHATCH_RECENT,
        arguments=ct.COMMAND_ARGUMENTS['RECENT'],
        folder=folder,
    )


def create_phatch_inspector_droplet(folder, icon=ICON):
    """"""
    create_droplet(
        name=ct.LABEL_PHATCH_INSPECTOR,
        arguments=ct.COMMAND_ARGUMENTS['INSPECTOR'],
        folder=folder,
        description=ct.INFO['name'] + ' ' + ct.LABEL_PHATCH_INSPECTOR,
    )


#wx dependent


def on_menu_file_export_droplet_actionlist(self, event):
    if self.is_save_not_ok():
        return
    if win32_missing(self):
        return
    self.menu_file_export_droplet(create_phatch_droplet, self.filename)


def on_menu_file_export_droplet_recent(self, event):
    if win32_missing(self):
        return
    self.menu_file_export_droplet(create_phatch_recent_droplet)


def on_menu_file_export_droplet_inspector(self, event):
    if win32_missing(self):
        return
    self.menu_file_export_droplet(create_phatch_inspector_droplet)

#---windows explorer

#register


def register_phatch(label, arguments, extensions, folder):
    return ', '.join([x.replace('.', '') for x in register_extensions(
        label=label,
        action=arguments,
        extensions=extensions,
        folder=folder,
    )])


def create_phatch_explorer_action(actionlist):
    """"""
    return register_phatch(
        label=ct.LABEL_PHATCH_ACTIONLIST % \
                        system.filename_to_title(actionlist),
        arguments=ct.COMMAND_ARGUMENTS['DROP'] % actionlist,
        extensions=_IMAGE_READ_EXTENSIONS,
        folder=True,
    )


def create_phatch_recent_explorer_action():
    """"""
    return register_phatch(
        label=RECENT,
        arguments=ct.COMMAND_ARGUMENTS['RECENT'],
        extensions=_IMAGE_READ_EXTENSIONS,
        folder=True,
    )


def create_phatch_inspect_explorer_action():
    """"""
    return register_phatch(
        label=INSPECTOR,
        arguments=ct.COMMAND_ARGUMENTS['INSPECTOR'],
        extensions=_IMAGE_READ_EXTENSIONS,
        folder=False,
    )


def remove_phatch_explorer_actions(actionlist):
    for label in [RECENT, INSPECTOR,
            ct.LABEL_PHATCH_ACTIONLIST % system.filename_to_title(actionlist)]:
        deregister_extensions(label, _IMAGE_READ_EXTENSIONS, folder=True)

#wx dependent


def menu_file_export_explorer(self, method, *arg, **keyw):
    result = method(*arg, **keyw)
    if result:
        self.show_info(EXTENSIONS_INSTALL_SUCCESFUL + result)
    else:
        self.show_error(EXTENSIONS_INSTALL_UNSUCCESFUL)


def on_menu_file_export_explorer_actionlist(self, event):
    if self.is_save_not_ok():
        return
    menu_file_export_explorer(self, create_phatch_explorer_action, \
                                                    self.filename)


def on_menu_file_export_explorer_recent(self, event):
    menu_file_export_explorer(self, create_phatch_recent_explorer_action)


def on_menu_file_export_explorer_inspector(self, event):
    menu_file_export_explorer(self, create_phatch_inspect_explorer_action)


def on_menu_file_export_explorer_remove(self, event):
    remove_phatch_explorer_actions(self.filename)
    self.show_info(EXTENSIONS_UNINSTALL)


#---install menus


def install_menu_item(self, menu, name, label, tooltip="",
        style=wx.ITEM_NORMAL):
    method = globals()['on_' + name]
    return self.install_menu_item(menu, name, label, method, tooltip, style)


def install(self):
    #install menu items in reverse order

    #explorer
    install_menu_item(self, self.menu_file_export,
        name='menu_file_export_explorer_remove',
        label=ct.INTEGRATE_PHATCH_REMOVE % "Windows Explore&r",)
    install_menu_item(self, self.menu_file_export,
        name='menu_file_export_explorer_inspector',
        label=ct.INTEGRATE_PHATCH_INSPECTOR % "Windows Explore&r",)
    install_menu_item(self, self.menu_file_export,
        name='menu_file_export_explorer_recent',
        label=ct.INTEGRATE_PHATCH_RECENT % "Windows &Explorer",)
    self.menu_item.append((self.menu_file_export,
        [install_menu_item(self, self.menu_file_export,
            name='menu_file_export_explorer_actionlist',
            label=ct.INTEGRATE_PHATCH_ACTIONLIST % "&Windows Explorer",)]))
    self.menu_file_export.InsertSeparator(4)

    #droplet
    install_menu_item(self, self.menu_file_export,
        name='menu_file_export_droplet_inspector',
        label=ct.DROPLET_PHATCH_INSPECTOR,)
    install_menu_item(self, self.menu_file_export,
        name='menu_file_export_droplet_recent',
        label=ct.DROPLET_PHATCH_RECENT,)
    self.menu_item.append((self.menu_file_export,
        [install_menu_item(self, self.menu_file_export,
            name='menu_file_export_droplet_actionlist',
            label=ct.DROPLET_PHATCH_ACTIONLIST,)]))
    self.menu_file_export.InsertSeparator(3)


if __name__ == '__main__':
    create_phatch_droplet(
        actionlist='/home/stani/sync/python/phatch/action \
lists/tutorials/thumb round 3d reflect.phatch',
        folder='/home/stani/sync/Desktop',)
