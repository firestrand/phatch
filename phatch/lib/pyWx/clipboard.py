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

import wx


def copy_text(text):
    """Copies text to the clipboard.

    :param text: text to copy
    :type text: string
    :returns: if the operation was succesfull
    :rtype: bool
    """
    if wx.TheClipboard.Open():
        text_data = wx.TextDataObject(text)
        wx.TheClipboard.SetData(text_data)
        wx.TheClipboard.Close()
        return True
    return False


def get_text():
    """Gets text from the clipboard.

    :returns: text from the clipboard or an empty string
    :rtype: string
    """
    if wx.TheClipboard.Open():
        text_data = wx.TextDataObject()
        wx.TheClipboard.GetData(text_data)
        wx.TheClipboard.Close()
        return text_data.GetText()
    return ''
