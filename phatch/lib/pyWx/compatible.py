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

"""This library enables enhanced features based on wxPython versions."""

import sys
import wx

if hasattr(wx, 'SearchCtrl'):
    #wxPython 2.8+

    class SearchCtrl(wx.SearchCtrl):
        def __init__(self, *args, **keyw):
            super(SearchCtrl, self).__init__(*args, **keyw)
            self.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self.OnCancel)
            self.ShowCancelButton(True)

        def OnCancel(self, event):
            self.SetValue('')

else:
    #wxPython 2.6-
    SearchCtrl = wx.TextCtrl

if hasattr(wx, 'GCDC'):
    if sys.platform.startswith('win'):
        FONT_SIZE = 15
    else:
        FONT_SIZE = 20

    def GCDC(x):
        try:
            return wx.GCDC(x)
        except:
            return x
else:
    FONT_SIZE = 15

    def GCDC(x):
        return x
