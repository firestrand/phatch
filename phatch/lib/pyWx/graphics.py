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
from io import StringIO, BytesIO
from urllib.request import urlopen

import wx

from phatch.lib import system


def _is_art_provider_icon(icon: bytes) -> bool:
    if icon[:4] == b'ART_':
        return True
    return False

def bitmap(icon, size=(48, 48), client=wx.ART_OTHER):
    if _is_art_provider_icon(icon):
        return wx.ArtProvider.GetBitmap(getattr(wx, icon), client, size)
    else:
        return wx.Bitmap(image(icon))


def image(icon, size=(48, 48)):
    if _is_art_provider_icon(icon):
        return wx.ImageFromBitmap(bitmap(icon, size))
    else:
        if icon[0:1] == b'x':  # compare first byte expect x to be zlib
            icon_b = zlib.decompress(icon)
        else:
            icon_b = icon
        icon_b_io = BytesIO(icon_b)
        wx_image = wx.Image(icon_b_io)
        return wx_image


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
