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

ICON_SIZE = (48, 48)

# ---vlist


class Box(wx.VListBox):
    """Default Icon Size is ICON_SIZE (48)."""
    def __init__(self, parent, *args, **kwds):
        super(Box, self).__init__(parent, *args, **kwds)
        self.SetIconSize(ICON_SIZE)
        self.SetVerticalGradient()
        if wx.Platform == '__WXGTK__':
            self.SetTheme('default')
        else:
            self.SetTheme('light_blue')
        self._events()
        wx.CallAfter(self.SetSelection, 0)

    def _events(self):
        """Can be overwritten."""
        pass

    def GradientColour(self, color):
        rgb = r, g, b = color.Red(), color.Green(), color.Blue()  # wx2.6
        m = max(rgb)
        rgb_without_max = [x for x in rgb if x != m]
        if not rgb_without_max:
            return wx.Colour(128, 128, 128)
        n = max(rgb_without_max)
        keyw = {}
        for c in ('Red', 'Green', 'Blue'):
            x = getattr(color, c)()
            if x == m:
                keyw[c.lower()] = x
            elif x == n:
                keyw[c.lower()] = x / 2
            else:
                keyw[c.lower()] = x / 8
        return wx.Colour(**keyw)

    def SetTheme(self, theme='default'):
        self._theme = theme
        if theme == 'light_blue':
            # mozilla like
            self._color_from = wx.Colour(180, 197, 214)
            self._color_to = wx.Colour(217, 226, 234)
        else:
            # theme based
            hilight = wx.SystemSettings_GetColour(wx.SYS_COLOUR_MENUHILIGHT)
            self._color_from = self.GradientColour(hilight)
            self._color_to = hilight

    def SetIconSize(self, icon_size=(48, 48), units=5):  # 31.0):
        """All vertical spacing is calculated by the icon size.
        The higher the units, the less space in between label and summary and
        the more space between the label/summary and the separators."""
        self._icon_size = i_x, i_y = icon_size
        self._row_height = int(1.5 * i_y)
        # vertical spacing
        line_height = self.GetTextExtent('H')[0]
        first_line_unit = int(units / 2)
        unit_dy = (self._row_height - 2 * line_height) / units
        # positions
        self.icon_x = (self._row_height - i_x) / 2
        self.icon_y = (self._row_height - i_y) / 2
        self.text_x = 2 * self.icon_x + i_x
        self.text_y1 = int(round(first_line_unit * unit_dy))
        self.text_y2 = int(round(
                            (units - first_line_unit) * unit_dy + line_height))

    def GetIconSize(self):
        return self._icon_size

    def OnDrawSeparator(self, dc, rect, n):
        dc.SetPen(wx.Pen(wx.LIGHT_GREY, style=wx.DOT))
        y = rect.GetBottom()
        dc.DrawLine(rect.GetLeft(), y, rect.GetRight(), y)

    def OnDrawBackground(self, dc, rect, n):
        """ Gradient fill from color 1 to color 2 with top to bottom
        or left to right. """
        if n != self.GetSelection():
            return

        if rect.height < 1 or rect.width < 1:
            return

        size = (self._is_vertical and [rect.height] or [rect.width])[0]
        start = (self._is_vertical and [rect.y] or [rect.x])[0]

        # calculate gradient coefficients
        col2 = self._color_from
        col1 = self._color_to

        rf, gf, bf = 0, 0, 0
        rstep = float((col2.Red() - col1.Red())) / float(size)
        gstep = float((col2.Green() - col1.Green())) / float(size)
        bstep = float((col2.Blue() - col1.Blue())) / float(size)

        for coord in xrange(start, start + size):

            currCol = wx.Colour(col1.Red() + rf, col1.Green() + gf, \
            col1.Blue() + bf)
            dc.SetBrush(wx.Brush(currCol, wx.SOLID))
            dc.SetPen(wx.Pen(currCol))
            if self._is_vertical:
                dc.DrawLine(rect.x, coord, rect.x + rect.width, coord)
            else:
                dc.DrawLine(coord, rect.y, coord, rect.y + rect.height)

            rf += rstep
            gf += gstep
            bf += bstep

    def OnMeasureItem(self, n):
        return self._row_height

    def OnDrawItem(self, dc, rect, n):
        label, summary, bmp = self.GetItem(n)
        # coordinates
        x0, y0 = rect.GetTopLeft()
        x1, y1 = rect.GetBottomRight()
        # bitmap
        dc.DrawBitmap(bmp, x0 + self.icon_x, y0 + self.icon_y, True)
        # text
        if self.GetSelection() != n or self._theme == 'light_blue':
            c = self.GetForegroundColour()
        else:
            c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        bold = self.GetFont()
        bold.SetWeight(wx.FONTWEIGHT_BOLD)
        dc.SetFont(bold)
        dc.SetTextForeground(c)
        dc.DrawText(label, x0 + self.text_x, y0 + self.text_y1)
        dc.SetFont(self.GetFont())
        dc.DrawText(summary, x0 + self.text_x, y0 + self.text_y2)

    def SetVerticalGradient(self, bool=True):
        self._is_vertical = bool

    def GetItem(self, n):
        """Needs to be overwritten."""
        return ('label %d' % n, 'summary %d' % n,
            wx.ArtProvider_GetBitmap(wx.ART_INFORMATION, wx.ART_OTHER,
                self.GetIconSize()))

    def RefreshAll(self):
        self.Refresh()
        if self.GetItemCount():
            self.SetSelection(0)


class TestFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Test Tag Browser",
            size=(640, 480))
        vlist_box = Box(self)
        vlist_box.SetItemCount(10)


def example():
    # install translation function everywhwere _
    __builtins__._ = str
    # create test application & dialog
    app = wx.PySimpleApp()
    frame = TestFrame(None)
    frame.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    example()
