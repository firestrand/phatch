# -*- coding: UTF-8 -*-

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
from compatible import GCDC, FONT_SIZE
import graphics
MARGIN = 2 * 10


class Mixin:
    paint_message = ''
    paint_logo = None
    paint_color = wx.Colour(60, 60, 60)  # ,200)
    paint_border_color = None
    paint_opacity = 200
    paint_radius = 8

    def OnEraseBackground(self, event=None, paint_object=None):
        paint_object = event.GetEventObject()
        if not paint_object.IsShown():
            return
        _dc = event.GetDC()
        if not _dc:
            _dc = wx.ClientDC(paint_object)
            rect = paint_object.GetUpdateRegion().GetBox()
            _dc.SetClippingRect(rect)
        dc = GCDC(_dc)
        dc.Clear()
        # Calculate text extents.
        paint_message = self.GetPaintMessage()
        if paint_message:
            tw, th = self.GetClientSize()
            cw, ch = tw - MARGIN, th - MARGIN
            font_size = FONT_SIZE + 1
            while (tw >= cw or th >= ch) and font_size > 5:
                font_size -= 1
                font = wx.Font(font_size, wx.FONTFAMILY_SWISS,
                                wx.FONTSTYLE_NORMAL, wx.FONTSTYLE_NORMAL,
                                encoding=wx.FONTENCODING_SYSTEM)
                dc.SetFont(font)
                tw, th = dc.GetTextExtent(paint_message)
            td = font_size / 2
            twd = tw + 2 * td
            thd = th + 2 * td
        else:
            tw = th = 0
        # Draw logo.
        ew, eh = paint_object.GetSize()
        if self.paint_logo:
            # Draw logo.
            lw, lh = self._paint_logo.GetSize()
            lx, ly = (ew - lw) / 2, (eh - lh + 2 * thd) / 2
            dc.DrawBitmap(self._paint_logo, lx, ly, True)
        else:
            # Skip logo.
            lx, ly = ew / 2, eh / 2
        # Check if text is necessary too.
        if not paint_message:
            return
        # Draw rounded rectangle.
        if self.paint_logo:
            rx, ry = (ew - twd) / 2, ly - 2 * thd
        else:
            rx, ry = (ew - twd) / 2, (eh - thd) / 2
        rect = wx.Rect(rx, ry, twd, thd)
        if self.paint_border_color:
            penclr = self.paint_border_color
        else:
            penclr = self.paint_color
        dc.SetPen(wx.Pen(penclr))
        dc.SetBrush(wx.Brush(self.paint_color))
        dc.DrawRoundedRectangleRect(rect, self.paint_radius)
        # Draw text.
        dc.SetTextForeground(paint_object.GetBackgroundColour())
        dc.DrawText(paint_message, rx + td, ry + td)

    def EnableBackgroundPainting(self, object, state=True, color=wx.WHITE):
        if state:
            if self.paint_logo:
                self._paint_logo = graphics.bitmap(self.paint_logo)
            object.SetBackgroundColour(color)
            object.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        else:
            object.Unbind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

    def GetPaintMessage(self):
        return self.paint_message


#---begin
def example():
    import sys
    sys.path.extend(['..'])
    import images

    class TestFrame(Mixin, wx.Frame):
        paint_message = 'hello world'
        paint_logo = images.LOGO

    class TestApp(wx.App):
        def OnInit(self):
            wx.InitAllImageHandlers()
            frame = TestFrame(None, -1, "Test", size=(600, 400))
            frame.EnableBackgroundPainting(frame)  # ,color=(245,245,255))
            self.SetTopWindow(frame)
            frame.Show(True)
            return 1

    app = TestApp(0)
    app.MainLoop()

if __name__ == '__main__':
    example()
