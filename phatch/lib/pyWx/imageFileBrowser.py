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

import os
import sys

import wx

if __name__ == '__main__':
    _ = unicode
    sys.path.insert(0, '..')
    sys.path.insert(0, '../..')

from lib.openImage import open_thumb
from lib.formField import IMAGE_READ_EXTENSIONS

import popup
from wxPil import pil_wxBitmap

ICON_SIZE = (64, 64)


def truncate(content, length=100, suffix='...'):
    if len(content) <= length:
        return content
    else:
        return content[:length].rsplit(' ', 1)[0] + suffix


class ListCtrl(wx.ListCtrl):
    def __init__(self, parent, files, icon_size=ICON_SIZE,
            checkboard=False, **keyw):
        super(ListCtrl, self).__init__(parent, -1,
            style=wx.LC_ICON | wx.LC_SINGLE_SEL, **keyw)
        #create image list
        self.image_list = wx.ImageList(*icon_size)
        self.icons = {}
        for file in files.values():
            self.icons[file] = self.image_list.Add(
                pil_wxBitmap(open_thumb(file, size=icon_size)))
        self.SetImageList(self.image_list, wx.IMAGE_LIST_NORMAL)
        #populate
        n = 10
        if type(files) is dict:
            labels_files = files.items()
            #labels_files = [(truncate(label,n),file)
             #   for label, file in files.items()]
        labels_files.sort()
        self._labels = [label for label, file in labels_files]
        self._files = [file for label, file in labels_files]
        self._files_to_labels = {}
        for label, file in labels_files:
            self._files_to_labels[file] = label
        for index, (label, file) in enumerate(labels_files):
            item = self.InsertImageStringItem(index, '', self.icons[file])
            self.SetItemData(item, index)

    def GetLabel(self, file):
        return self._files_to_labels.get(file, file)

    def GetItemFile(self, item):
        return self._files[item.GetData()]

    def GetItemLabel(self, item):
        return self._labels[item.GetData()]

    def Select(self, index):
        self.SetItemState(index, wx.LIST_STATE_SELECTED,
            wx.LIST_STATE_SELECTED)
        self.EnsureVisible(index)

    def Deselect(self, index):
        self.SetItemState(index, 0,
            wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)


class Dialog(wx.Dialog):
    def __init__(self, parent, files, icon_size=ICON_SIZE, **keyw):
        keyw["style"] = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER \
            | wx.MAXIMIZE_BOX
        super(Dialog, self).__init__(parent, -1, **keyw)
        #controls
        #this is a dialog, add first panel
        self.panel = wx.Panel(self, -1)
        self.image_path = popup.DictionaryFileCtrl(self.panel, value=' ',
            size=(200, 200), dictionary=files,
            extensions=IMAGE_READ_EXTENSIONS)
        self.image_list = ListCtrl(self.panel, files, icon_size)
        self.status = wx.StaticText(self.panel, -1, "")
        self.cancel = wx.Button(self.panel, wx.ID_CANCEL, _("&Cancel"))
        self.ok = wx.Button(self.panel, wx.ID_OK, _("&Select"))
        self.ok.SetDefault()
        #layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.image_path, 0, wx.ALL | wx.EXPAND, 0)
        sizer.Add(self.image_list, 1, wx.EXPAND)
        #buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        b = 6
        btn_sizer.Add(self.status, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, b)
        btn_sizer.Add(self.cancel, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, b)
        btn_sizer.Add(self.ok, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, b)
        sizer.Add(btn_sizer, 0, wx.EXPAND, 0)
        #panel
        self.panel.SetSizer(sizer)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.SetSizer(panel_sizer)
        self.Layout()
        #events
        self.selection = None
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected,
            self.image_list)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnActivated,
            self.image_list)
        self.Bind(wx.EVT_TEXT, self.OnText, self.image_path.path)

    def OnItemSelected(self, event):
        self.selection = event.GetIndex()
        value = self.image_list.GetItemLabel(event.GetItem())
        if value != self.image_path.GetValue():
            self.image_path.SetValue(value)
        event.Skip()

    def OnText(self, event):
        #print 'ontext',event.GetString()
        self.Select(event.GetString())

    def Select(self, value):
        li = self.image_list
        #if the file is in the library -> use label instead
        value = li.GetLabel(value)
        if value in li._labels:
            index = li._labels.index(value)
            item = li.GetItem(index)
            li.Select(index)
        elif not(self.selection is None):
            #print "deselect", self.selection
            #li.Deselect(self.selection) DO NOT ENABLE OR IT BLOCKS UI!
            self.selection = None

    def ShowPath(self, state):
        self.image_path.Show(state)
        self.Layout()

    def SetValue(self, value):
        self.image_path.SetValue(value)
        self.Select(value)

    def OnActivated(self, event):
        self.EndModal(wx.ID_OK)


def example():
    import glob
    images = {}
    for image in glob.glob('/usr/share/icons/hicolor/48x48/apps/*.png'):
        images[os.path.basename(image)] = image

    class App(wx.App):
        def OnInit(self, *args, **keyw):
            frame = wx.Frame(None, -1, 'image file test', size=(600, 400))
            image_list = ListCtrl(frame, images)
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(image_list, 1, flag=wx.EXPAND)
            frame.SetSizer(sizer)
            frame.Layout()
            frame.Show()
            self.SetTopWindow(frame)
            dialog = Dialog(frame, images, title='Select Image')
            if dialog.ShowModal() == wx.ID_OK:
                print(dialog.image_path.GetValue())
            if dialog.ShowModal() == wx.ID_OK:
                print(dialog.image_path.GetValue())
            dialog.Destroy()
            return True

    app = App(0)
    app.MainLoop()

if __name__ == '__main__':
    example()
