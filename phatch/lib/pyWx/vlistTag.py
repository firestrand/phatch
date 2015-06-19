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

"""Wraps vlist in a tag browser jacket."""

import wx
from vlist import Box
from tag import Browser, ContentMixin, extract_tags  # imported by dialogs.py


#---Test case
class TestContentBox(ContentMixin, Box):
    def SetTag(self, tag):
        self.SetVerticalGradient(tag == 'vertical')
        self.Refresh()

    def SetFilter(self, filter):
        try:
            n = int(filter)
        except ValueError:
            n = 0
        self.SetItemCount(n)
        if not self.CheckEmpty():
            self.RefreshAll()

    def IsEmpty(self):
        return not self.GetItemCount()


class TestBrowser(Browser):
    ContentCtrl = TestContentBox

    paint_message = "type a number"

    def _init(self):
        """Normally overwrite this."""
        self.CheckEmpty()


class TestFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Test Tag Browser",
            size=(640, 480))
        browser = TestBrowser(self, ['vertical', 'horizontal'], {})
        browser.EnableResize()


class Dialog(wx.Dialog):
    ContentBrowser = TestBrowser

    def __init__(self, parent, tags, *args, **kwds):
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        super(Dialog, self).__init__(parent, *args, **kwds)
        self._create_controls(tags)
        self._layout()
        self._events()

    def _create_controls(self, tags):
        self.browser = self.ContentBrowser(self, tags, {},
            style=wx.SUNKEN_BORDER)
        self.status = wx.StaticText(self, -1, "")
        self.cancel = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        self.ok = wx.Button(self, wx.ID_OK, _("&Add"))
        self.ok.SetDefault()

    def _layout(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        #browser
        main_sizer.Add(self.browser, 1, wx.ALL | wx.EXPAND, 4)
        #buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(self.status, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        btn_sizer.Add(self.cancel, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        btn_sizer.Add(self.ok, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND, 0)
        #layout
        self.SetSizer(main_sizer)
        self.Layout()

    def _events(self):
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.ok)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.OnDoubleClick,
            self.browser.content)
        self.browser.EnableResize()

    def OnOk(self, event):
        if not self.browser.content.IsEmpty():
            event.Skip()

    def OnDoubleClick(self, event):
        self.EndModal(wx.ID_OK)


class TestDialog(Dialog):
    ContentBox = TestContentBox
    content_ctrl_keyw = {'n': 5}


def example():
    #install translation function everywhwere _
    __builtins__._ = str
    #create test application & dialog
    app = wx.PySimpleApp()
    frame = TestFrame(None)
    frame.Show(True)
    dialog = TestDialog(frame, ['vertical', 'horizontal'])
    dialog.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    example()
