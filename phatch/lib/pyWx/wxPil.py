# Copyright (C) 2007-2009 www.stani.be
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

from PIL import Image
import wx


def pil_wxImage(image):
    if image.mode == 'P':
        image = image.convert('RGBA')
    if image.mode == 'RGBA':
        wx_image = wx.EmptyImage(*image.size)
        wx_image.SetData(image.convert("RGB").tobytes())
        wx_image.InitAlpha()
        wx_image.SetAlphaData(
            image.convert("RGBA").split()[-1].tobytes())
    else:
        wx_image = wx.Image(*image.size)
        new_image = image.convert('RGB')
        data = new_image.tobytes()
        wx_image.SetData(data)
    return wx_image


def pil_wxBitmap(image):
    return wx.BitmapFromImage(pil_wxImage(image))


def wxImage_pil_(wx_image):
    size = wx_image.GetSize()
    if type(wx_image) == wx.Image:
        size = (size.width, size.height)
    image = Image.new('RGB', size)
    image.frombytes(bytes(wx_image.GetData()))
    if wx_image.HasAlpha():
        alpha = Image.new('L', size)
        wx_alpha = wx_image.GetAlphaData()
        alpha.frombytes(bytes(wx_alpha))
        image = image.convert('RGBA')
        image.putalpha(alpha)
    return image

def wxImage_pil(wx_image):
    w = wx_image.GetWidth()
    h = wx_image.GetHeight()
    data = wx_image.GetData()

    red_image = Image.frombuffer('L', (w, h), data[0::3])
    green_image = Image.frombuffer('L', (w, h), data[1::3])
    blue_image = Image.frombuffer('L', (w, h), data[2::3])
    return Image.merge('RGB', (red_image, green_image, blue_image))

def wxBitmap_pil(wx_bitmap):
    return wxImage_pil(wx.ImageFromBitmap(wx_bitmap))
