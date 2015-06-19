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

import os
import wx


def get(rect):
    """ Takes a screenshot of the screen at give pos & size (rect). """

    # Create a DC for the whole screen area.
    dcScreen = wx.ScreenDC()

    # Create a Bitmap that will later on hold the screenshot image.
    # Note that the Bitmap must have a size big enough to hold the screenshot.
    # -1 means using the current default color depth.
    bmp = wx.EmptyBitmap(rect.width, rect.height)

    # Create a memory DC that will be used for actually taking the screenshot.
    memDC = wx.MemoryDC()

    # Tell the memory DC to use our Bitmap
    # all drawing action on the memory DC will go to the Bitmap now.
    memDC.SelectObject(bmp)

    # Blit (in this case copy) the actual screen on the memory DC
    # and thus the Bitmap
    memDC.Blit(0,  # Copy to this X coordinate.
        0,  # Copy to this Y coordinate.
        rect.width,  # Copy this width.
        rect.height,  # Copy this height.
        dcScreen,  # From where do we copy?
        rect.x,  # What's the X offset in the original DC?
        rect.y  # What's the Y offset in the original DC?
        )

    # Select the Bitmap out of the memory DC by selecting a new
    # uninitialized Bitmap.
    memDC.SelectObject(wx.NullBitmap)

    return bmp


def get_window(window):
    return get(window.GetRect())


def save(rect, filename):
    ext = os.path.splitext(filename)[-1][1:].upper()
    typ = getattr(wx, 'BITMAP_TYPE_' + ext)
    return get(rect).SaveFile(filename, typ)


def save_window(window, filename):
    return save(window.GetRect(), filename)
