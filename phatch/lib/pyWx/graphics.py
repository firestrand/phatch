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


def create_placeholder_image(size=(48, 48)):
    """Create a simple placeholder image with a colored rectangle."""
    width, height = size
    image = wx.Image(width, height)
    
    # Fill with light gray
    for x in range(width):
        for y in range(height):
            image.SetRGB(x, y, 200, 200, 200)
    
    # Draw a border
    for x in range(width):
        image.SetRGB(x, 0, 0, 0, 0)  # Top border
        image.SetRGB(x, height-1, 0, 0, 0)  # Bottom border
    
    for y in range(height):
        image.SetRGB(0, y, 0, 0, 0)  # Left border
        image.SetRGB(width-1, y, 0, 0, 0)  # Right border
    
    # Draw an X
    for i in range(min(width, height)):
        if i < width and i < height:
            image.SetRGB(i, i, 0, 0, 0)
            image.SetRGB(i, height-i-1, 0, 0, 0)
    
    return image


def _is_art_provider_icon(icon):
    if isinstance(icon, str):
        return icon.startswith('ART_')
    elif isinstance(icon, bytes):
        return icon[:4] == b'ART_'
    return False

def bitmap(icon, size=(48, 48), client=wx.ART_OTHER):
    if _is_art_provider_icon(icon):
        return wx.ArtProvider.GetBitmap(getattr(wx, icon), client, size)
    else:
        return wx.Bitmap(image(icon, size))


def image(icon, size=(48, 48)):
    if _is_art_provider_icon(icon):
        return wx.ImageFromBitmap(bitmap(icon, size))
    else:
        try:
            # Ensure icon is bytes
            if isinstance(icon, str):
                try:
                    icon = icon.encode('utf-8')
                except Exception:
                    return create_placeholder_image(size)
            
            # Check if it's a zlib compressed icon
            if icon[0:1] == b'x':
                # Look for PNG signature in the data
                png_signature = b'\x89PNG\r\n\x1a\n'
                png_start = icon.find(png_signature)
                
                if png_start >= 0:
                    # Extract the PNG data directly
                    icon_b = icon[png_start:]
                else:
                    try:
                        # Try to decompress with zlib
                        icon_b = zlib.decompress(icon)
                    except zlib.error as e:
                        print(f"Zlib decompression error: {e}")
                        return create_placeholder_image(size)
            else:
                icon_b = icon
            
            # Try to load the image
            try:
                icon_b_io = BytesIO(icon_b)
                wx_image = wx.Image(icon_b_io)
                if not wx_image.IsOk():
                    return create_placeholder_image(size)
                
                # Resize if needed
                if wx_image.GetWidth() != size[0] or wx_image.GetHeight() != size[1]:
                    wx_image.Rescale(size[0], size[1])
                
                return wx_image
            except Exception as e:
                print(f"Error creating image from data: {e}")
                return create_placeholder_image(size)
                
        except Exception as e:
            print(f"Error loading icon: {e}")
            # Fallback to a custom placeholder image
            return create_placeholder_image(size)


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
