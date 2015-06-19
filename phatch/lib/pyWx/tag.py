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

import wx
import paint
from compatible import SearchCtrl


def extract_tags(items):
    tags = []
    for item in items:
        for tag in item.tags:
            tag = _(tag)
            if tag not in tags:
                tags.append(tag)
    return tags


class ContentMixin(object):
    def GetBrowser(self):
        return self.GetParent()

    def GetFilter(self):
        return self.GetBrowser().filter

    def GetTag(self):
        return self.GetBrowser().tag

    def CheckEmpty(self):
        self.GetBrowser().CheckEmpty()

    def GetEmpty(self):
        return self.GetBrowser().empty

    def SetTag(self, tag):
        #check tag ctrl in parent
        tag_ctrl = self.GetTag()
        if tag_ctrl.GetStringSelection() != tag:
            tag_ctrl.SetStringSelection(tag)


class Browser(paint.Mixin, wx.Panel):
    """ContentCtrl needs to be a class which implements these methods:
    - content.SetTag    <- browser.OnTag
    - content.SetFilter <- browser.OnFilter"""

    ContentCtrl = wx.Panel

    paint_message = "nothing found"
    paint_logo = None  # "ART_TIP"

    def __init__(self, parent, tags, content_ctrl_keyw, *args, **keyw):
        """At least four arguments should be passed:
        Browser(['foo', 'bar'], TestContentCtrl, {}, parent)"""
        super(Browser, self).__init__(parent, *args, **keyw)
        self._create_controls(tags, content_ctrl_keyw)
        self._layout()
        self._events()
        self._init()

    def _init(self):
        pass

    def _create_controls(self, tags, content_ctrl_keyw):
        #save tags
        self._tags = tags
        #search box
        self.filter = SearchCtrl(self, -1, "")
        #tag choice ctrl
        self.tag = wx.Choice(self, -1, choices=tags)
        if tags:
            self.tag.SetSelection(0)
        #empty ctrl
        self.empty = wx.Panel(self)
        #content ctrl
        self.content = self.ContentCtrl(self, **content_ctrl_keyw)
        self.is_empty = -1

    def _layout(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        #horizontal browse sizer = search & tag control
        browse_sizer = wx.BoxSizer(wx.HORIZONTAL)
        browse_sizer.Add(self.filter, 1,
            wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        browse_sizer.Add(self.tag, 0,
            wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND, 4)
        main_sizer.Add(browse_sizer, 0, wx.EXPAND, 0)
        #content control
        main_sizer.Add(self.content, 1, wx.ALL | wx.EXPAND, 4)
        #empty control
        main_sizer.Add(self.empty, 1, wx.ALL | wx.EXPAND, 4)
        #layout
        self.SetSizer(main_sizer)
        self.Layout()

    def _events(self):
        self.Bind(wx.EVT_TEXT, self.OnFilter, self.filter)
        self.Bind(wx.EVT_CHOICE, self.OnTag, self.tag)
        self.EnableBackgroundPainting(self.empty)

    def OnTag(self, event):
        self.content.SetTag(event.GetString())

    def OnFilter(self, event):
        self.content.SetFilter(self.filter.GetValue())

    def GetItemTags(self, item):
        """Can be overwritten."""
        return item.tags

    def GetTags(self, items):
        return self._tags

    def GetContent(self):
        return self.content

    def CheckEmpty(self):
        is_empty = self.IsEmpty()
        if self.is_empty != is_empty:
            #update is needed
            self.empty.Show(is_empty)
            self.content.Show(not is_empty)
            self.is_empty = is_empty
        self.empty.Refresh()
        self.Layout()
        return is_empty

    def IsEmpty(self):
        return self.content.IsEmpty()

    def OnSize(self, event):
        event.Skip()
        if self.IsEmpty():
            self.empty.Refresh()

    def EnableResize(self, state=True, object=None):
        if object is None:
            object = wx.GetTopLevelParent(self)
        if state:
            object.Bind(wx.EVT_SIZE, self.OnSize)
        else:
            object.Unbind(wx.EVT_SIZE)


class TestContentCtrl(ContentMixin, wx.TextCtrl):
    def __init__(self, *args, **keyw):
        super(TestContentCtrl, self).__init__(*args, **keyw)
        self.filter = ''

    def SetTag(self, tag):
        self.SetValue('You selected tag: %s.' % tag)

    def SetFilter(self, filter):
        self.filter = filter
        if not self.CheckEmpty():
            self.SetValue('You selected filter: %s.' % filter)

    def IsEmpty(self):
        return not self.filter


class TestBrowser(Browser):
    ContentCtrl = TestContentCtrl

    def _init(self):
        self.CheckEmpty()


class TestFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Test Tag Browser",
            size=(640, 480))
        self.browser = TestBrowser(self, ['foo', 'bar'], {})
        self.browser.EnableResize()


def example():
    import sys
    sys.path.extend(['..'])
    #test app
    app = wx.PySimpleApp()
    frame = TestFrame(None)
    frame.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    example()
