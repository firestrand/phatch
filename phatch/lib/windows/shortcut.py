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

import win32com.client


def create(save_as, path, arguments="", working_dir="",
        description="", icon_path=None, icon_index=0):
    # initialize shortcut
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(save_as)

    # set shortcut parameters
    shortcut.Targetpath = path
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = working_dir
    shortcut.Description = description
    if icon_path:
        shortcut.IconLocation = icon_path

    # save shortcut
    shortcut.save()
