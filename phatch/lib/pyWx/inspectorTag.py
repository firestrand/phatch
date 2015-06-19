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


import wx
import inspector
from tag import Browser, ContentMixin, extract_tags

TEST_DATA = {
    'decimal':   [[str((row, col)) for col in range(inspector.NUMBER_COLS)]
                        for row in range(100)],
    'hexadecimal':  [[str((hex(row), hex(col))) for col in \
                                    range(inspector.NUMBER_COLS)]
                        for row in range(100)],
}


class Grid(ContentMixin, inspector.Grid):
    def SetData(self, data, tag):
        self.all_data = data
        self.SetTag(tag)

    def IsEmpty(self):
        return not self.data


class TestContentGrid(Grid):
    def SetTag(self, tag, filter=None):
        self.tag_data = self.all_data[tag]
        self.SetFilter()

    def SetFilter(self, filter=None):
        if filter is None:
            filter = self.GetFilter().GetValue()
        if filter.strip():
            self.data = [row for row in self.tag_data
                            if filter in unicode(row)]
        else:
            self.data = self.tag_data
        if not self.CheckEmpty():
            self.RefreshAll()

    def SetData(self, data):
        self.all_data = data
        self.SetTag(_('decimal'))


class TestBrowser(Browser):
    ContentCtrl = TestContentGrid

    paint_message = "nothing found"

    def _init(self):
        self.content.SetTag('decimal')


class TestFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Test Tag Browser",
            size=(640, 480))
        browser = TestBrowser(self, TEST_DATA.keys(), {'data': TEST_DATA})
        browser.EnableResize()


class Frame(wx.Frame):
    Browser = TestBrowser

    def __init__(self, parent, data, tags, icon=None, *args, **kwds):
        if  'style' in kwds:
            kwds["style"] = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        if parent:
            kwds["style"] |= wx.FRAME_FLOAT_ON_PARENT
        if parent:
            kwds["style"] |= wx.FRAME_NO_TASKBAR
        super(Frame, self).__init__(parent, *args, **kwds)
        if icon:
            self.SetIcon(icon)
        self._create_controls(data, tags)
        self._layout()
        self._events()

    def _create_controls(self, data, tags):
        self.panel = wx.Panel(self, -1)
        self.browser = self.Browser(self.panel, tags, {'data': data})
        self.status = wx.StaticText(self.panel, -1, "")
        self.close = wx.Button(self.panel, wx.ID_CLOSE, "")  # _("&Close"))
        self.close.SetDefault()

    def _layout(self):
        # main_sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self._layout_top(main_sizer)
        # browser
        main_sizer.Add(self.browser, 1, wx.ALL | wx.EXPAND, 4)
        # buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._layout_buttons(btn_sizer)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND, 0)
        # layout
        self.panel.SetSizer(main_sizer)
        # panel_sizer
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(self.panel, 1, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(panel_sizer)
        # layout
        self.Layout()

    def _layout_top(self, main_sizer):
        pass

    def _layout_buttons(self, btn_sizer):
        btn_sizer.Add(self.status, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        btn_sizer.Add(self.close, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)

    def GetGrid(self):
        return self.browser.GetContent()

    def _events(self):
        self.Bind(wx.EVT_BUTTON, self.OnClose)

    def OnClose(self, event):
        self.Destroy()

    def CreateBitmapButton(self, id, tooltip, size=(24, 24), \
                                            style=wx.NO_BORDER):
        bmp = wx.ArtProvider_GetBitmap(id, wx.ART_OTHER, size=size)
        btn = wx.BitmapButton(self.panel, -1, bmp, style=style)
        btn.SetToolTipString(tooltip)
        return btn

if __name__ == '__main__':
    __builtins__._ = str
    app = wx.PySimpleApp()
    frame = TestFrame(None)
    frame.Show(True)
    dialog = Frame(frame, TEST_DATA, TEST_DATA.keys())
    dialog.Show(True)
    app.MainLoop()
