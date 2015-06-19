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

import zlib
from cStringIO import StringIO
from urllib import urlopen

import wx

try:
    from lib import system
except ImportError:

    def is_www_file(x):
        return True  # fix this


def bitmap(icon, size=(48, 48), client=wx.ART_OTHER):
    if icon[:4] == 'ART_':
        return wx.ArtProvider_GetBitmap(getattr(wx, icon), client, size)
    else:
        return wx.BitmapFromImage(image(icon))


def image(icon, size=(48, 48)):
    if icon[:4] == 'ART_':
        return wx.ImageFromBitmap(bitmap(icon, size))
    else:
        return wx.ImageFromStream(StringIO(zlib.decompress(icon)))

CACHE = {}


def bitmap_open(x, height=64):
    try:
        return CACHE[(x, height)]
    except KeyError:
        pass
    if system.is_www_file(x):
        im = wx.ImageFromStream(StringIO(urlopen(x).read()))
    else:
        im = wx.Image(x)
    im = CACHE[(x, height)] = im.Rescale(
            float(height) * im.GetWidth() / im.GetHeight(),
            height).ConvertToBitmap()
    return im
