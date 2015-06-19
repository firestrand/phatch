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
# Follow PEP8

try:
    _
except NameError:
    _ = unicode

import time

import __main__

import wx
import wx.py

TRANSLATE = _


class Frame(wx.Frame):
    def __init__(self, parent, title='Shell', intro='', values={}, icon=None,
            **kw):
        wx.Frame.__init__(self, parent, -1, title=title, **kw)
        self.shell = wx.py.crust.Crust(self, -1, intro=intro)
        pp = self.shell.shell.interp.locals['pp']
        self.shell.shell.interp.locals.clear()
        self.shell.shell.interp.locals.update(values)
        self.shell.shell.interp.locals['pp'] = pp
        if icon:
            self.SetIcon(icon)
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

        shell = self.shell.shell
        shell.Unbind(wx.EVT_IDLE)
        shell.Bind(wx.EVT_IDLE, self.OnIdle)

    def OnIdle(self, event):
        """Free the CPU to do other things."""
        __main__._ = TRANSLATE
        event.Skip()
        if self.shell.shell.waiting:
            time.sleep(0.05)

    def on_close(self, event):
        parent = self.GetParent()
        parent.menu_tools.Check(parent.menu_tools_python_shell.GetId(), False)
        parent.shell = None
        event.Skip()
