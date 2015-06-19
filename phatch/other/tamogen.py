# -*- coding: utf-8 -*-
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#    Title:   Tone Altering Mosaic Generator (TAMOGEN)
#    Version: 1.1
#    Author:  Jack Whitsitt, Juho Vepsäläinen
#    Contact: http://sintixerr.wordpress.com
#
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

# 1.0 Original version by Jack Whitsitt.
# 1.1 Restructuring of the code, new pixel dispersion method and folder fill
# type by Juho Vepsäläinen.

import glob, os, sys, Image, ImageChops
from itertools import izip
from ImageStat import Stat
from lib import openImage

IMAGE_ITSELF = 0
OTHER_IMAGE = 1
FOLDER = 2
FILL_TYPES = (IMAGE_ITSELF, OTHER_IMAGE, FOLDER)

def mosaic(im, filltype, x_squares, y_squares, x_pix, y_pix, fill_image=None, fill_folder=None):
    assert filltype in FILL_TYPES

    fill_size = (x_pix, y_pix)
    num_squares = (min(x_squares, x_pix), min(y_squares, y_pix))
    final_img = Image.new(im.mode, fill_size)

    fill_section_size = get_section_size(fill_size, num_squares)
    im_section_size = get_section_size(im.size, num_squares)

    # calculate missing pixels for dispersion algo to avoid blank pixels
    missing_column_pixels = fill_size[0] - num_squares[0] * fill_section_size[0]
    missing_row_pixels = fill_size[1] - num_squares[1] * fill_section_size[1]

    # alter section sizes based on missing pixels
    if missing_row_pixels:
        fill_section_size[0] += 1
        im_section_size[0] += 1

    if missing_column_pixels:
        fill_section_size[1] += 1
        im_section_size[1] += 1

    boxes = BoundingBoxContainer()
    boxes.append('fill_box', (0, 0), fill_section_size)
    boxes.append('im_box', (0, 0), im_section_size)

    fill_images = FillImages(fill_section_size, im.mode)

    if filltype == IMAGE_ITSELF:
        fill_images.append(im)
    elif filltype == OTHER_IMAGE:
        fill_images.append(openImage.open(fill_image))
    elif filltype == FOLDER:
        for file_name in glob.iglob(os.path.join(fill_folder, '*')):
            try:
                fill_images.append(openImage.open(file_name))
            except IOError:
                pass

    for column in range(num_squares[0]):
        for row in range(num_squares[1]):
            bsection = im.crop(boxes['im_box'])
            fill_img, tone_diff = fill_images.findClosestImageAndToneDiff(bsection)
            set_new_tone(fill_img.copy(), tone_diff, boxes['fill_box'], final_img)
            boxes.move_down()

        boxes.reset_y()
        boxes.move_right()

    return final_img

class FillImages(list):
    def __init__(self, fill_section_size, mode):
        self.fill_section_size = fill_section_size
        self.mode = mode
        super(FillImages, self).__init__()

    def append(self, item):
        super(FillImages, self).append(FillImage(item, self.fill_section_size, self.mode))

    def findClosestImageAndToneDiff(self, cmp_img):
        if len(self) == 1:
            return self[0].image, self._getToneDiff(get_tone(cmp_img), self[0].tone)

        record_fill = self[0]
        record_avg = sys.maxint

        for fill in self:
            diff_image = ImageChops.difference(cmp_img, fill.image)
            image_avg = sum(Stat(diff_image).mean)

            if image_avg < record_avg:
                record_fill = fill
                record_avg = image_avg

        return record_fill.image, self._getToneDiff(get_tone(cmp_img), record_fill.tone)

    def _getToneDiff(self, a, b):
        return map(lambda x, y: x / max(y, 0.001), a, b)

class FillImage(object):
    def __init__(self, image, fill_section_size, mode):
        self.image = self._generateThumbnail(image, fill_section_size, mode)
        self.tone = get_tone(image.convert(mode))

    def _generateThumbnail(self, im, fill_section_size, mode):
        return im.resize(fill_section_size, Image.ANTIALIAS).convert(mode)

class BoundingBoxContainer(dict):
    def append(self, box_name, topleft, bottomright):
        self[box_name] = BoundingBox(topleft, bottomright)

    def move_right(self):
        for box in self.values():
            box.move_right()

    def move_down(self):
        for box in self.values():
            box.move_down()

    def reset_y(self):
        for box in self.values():
            box.reset_y()

class BoundingBox(list):
    def __init__(self, topleft, bottomright):
        super(BoundingBox, self).__init__([topleft[0], topleft[1], bottomright[0], bottomright[1]])

    def get_left(self):
        return self[0]
    def set_left(self, value):
        self[0] = value
    left = property(get_left, set_left)

    def get_top(self):
        return self[1]
    def set_top(self, value):
        self[1] = value
    top = property(get_top, set_top)

    def get_right(self):
        return self[2]
    def set_right(self, value):
        self[2] = value
    right = property(get_right, set_right)

    def get_bottom(self):
        return self[3]
    def set_bottom(self, value):
        self[3] = value
    bottom = property(get_bottom, set_bottom)

    def move_down(self):
        amount = self._get_height()

        self.top += amount
        self.bottom += amount

    def move_right(self):
        amount = self._get_width()

        self.left += amount
        self.right += amount

    def reset_y(self):
        height = self._get_height()

        self.top = 0
        self.bottom = height

    def _get_height(self):
        return abs(self.top - self.bottom)

    def _get_width(self):
        return abs(self.right - self.left)

def get_tone(img):
    return Stat(img).mean

def get_section_size(im_size, num_squares):
    def calculateSection(coord1, coord2):
        return int(round(coord1 / float(coord2)))
    return [calculateSection(x, y) for (x, y) in izip(im_size, num_squares)]

def set_new_tone(fill_img, tone_diff, cur_fill_box, final_img):
    temp_pix = []

    for pix_col in fill_img.getdata():
        temp_pix.append(tuple([int(x * y) for (x, y) in izip(pix_col, tone_diff)]))

    fill_img.putdata(temp_pix)

    if fill_img.mode == 'RGBA':
        final_img.paste(fill_img, (cur_fill_box.left, cur_fill_box.top),
            fill_img)
    else:
        final_img.paste(fill_img, (cur_fill_box.left, cur_fill_box.top))
