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

#standard modules
import types

#gui-dependent
import wx


def fix_paths(paths):
    if isinstance(paths, (types.ListType, types.TupleType)) \
        and len(paths) == 1:
        paths = paths[0]
    if isinstance(paths, types.StringTypes):
        paths = paths.strip().split('\n')
    for index, path in enumerate(paths):
        if path.startswith('file://'):
            paths[index] = path[7:]
    return paths


class FileDropTarget(wx.FileDropTarget):
    def __init__(self, method):
        super(FileDropTarget, self).__init__()
        self.method = method

    def OnDropFiles(self, x, y, filenames):
        self.method(fix_paths(filenames), x, y)


class Mixin:
    def SetAsFileDropTarget(self, object, method):
        dt = FileDropTarget(method)
        object.SetDropTarget(dt)


class Frame(Mixin, wx.Frame):
    def __init__(self, parent, title, bitmap, method=None, label='',
            label_color=wx.BLACK, label_angle=0, label_pos=(0, 0), auto=False,
            pos=(0, 0), OnShow=None, splash=False, tooltip=''):
        wx.Frame.__init__(self, parent, -1, title,
            pos=pos,
            style=wx.FRAME_SHAPED | wx.SIMPLE_BORDER | wx.FRAME_NO_TASKBAR \
                | wx.STAY_ON_TOP)

        self.label = label
        self.label_color = label_color
        self.label_x, self.label_y = label_pos
        self.label_angle = label_angle
        if OnShow:
            self.OnShow = OnShow

        self.hasShape = False
        self.delta = (0, 0)

        self.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.bmp = bitmap
        w, h = self.bmp.GetWidth(), self.bmp.GetHeight()
        self.SetClientSize((w, h))

        if wx.Platform != "__WXMAC__" and tooltip:
            #wxMac clips the tooltip to the window shape, YUCK!!!
            self.SetToolTipString(tooltip)
        if wx.Platform == "__WXGTK__":
            #wxGTK requires that the window be created before you can
            #set its shape, so delay the call to SetWindowShape until
            #this event.
            self.Bind(wx.EVT_WINDOW_CREATE, self.SetWindowShape)
        else:
            #On wxMSW and wxMac the window has already been created,
            #so go for it.
            self.SetWindowShape()

        dc = wx.ClientDC(self)
        dc.DrawBitmap(self.bmp, 0, 0, True)

        self.SetAsFileDropTarget(self, method)

        if auto:
            self.show()

    def show(self, bool=True):
        self.GetParent().Show(not bool)
        if bool:
            self.Show()
        else:
            self.Destroy()
        self.OnShow(bool)

    def SetWindowShape(self, *evt):
        # Use the bitmap's mask to determine the region
        r = wx.RegionFromBitmap(self.bmp)
        self.hasShape = self.SetShape(r)

    def OnDoubleClick(self, evt):
        self.show(False)

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0, True)
        font = wx.Font(7, wx.NORMAL, wx.NORMAL, wx.NORMAL)
        dc.SetFont(font)
        dc.SetTextForeground(self.label_color)
        dc.DrawRotatedText(self.label, self.label_x, self.label_y,
            self.label_angle)

    def OnRightUp(self, evt):
        self.show(False)

    def OnLeftDown(self, evt):
        self.CaptureMouse()
        x, y = self.ClientToScreen(evt.GetPosition())
        originx, originy = self.GetPosition()
        dx = x - originx
        dy = y - originy
        self.delta = ((dx, dy))

    def OnLeftUp(self, evt):
        if self.HasCapture():
            self.ReleaseMouse()

    def OnMouseMove(self, evt):
        if evt.Dragging() and evt.LeftIsDown():
            x, y = self.ClientToScreen(evt.GetPosition())
            fp = (x - self.delta[0], y - self.delta[1])
            self.Move(fp)

    def OnShow(self, bool):
        pass
