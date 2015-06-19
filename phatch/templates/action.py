# -*- coding: UTF-8 -*-

# Phatch - Photo Batch Processor
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
# Phatch recommends SPE (http://pythonide.stani.be) for editing python files.
#
# Follow PEP8
# Always import this (other imports in method Action.init):
from core import models
from lib.reverse_translation import _t

# Declare constants here (remove this line, for demonstration only)
CHOICES = [_t('Description'), _t('Image')]

# Use any PIL function you need


def init(cls=None):
    global Image
    import Image


def foo(image, dpi, horizontal):
    # process image with pil
    # (...)
    image2 = Image.new('RGB', (10, 10))
    return image


class Action(models.Action):

    label = _t('Label')
    author = 'Author'
    email = 'info@email.com'
    init = init
    version = '0.1'
    tags = [_t('tag')]
    __doc__ = _t('Description')

    def interface(self, fields):
        fields[_t('Boolean')] = self.BooleanField(True)
        fields[_t('String')] = self.CharField('hello world')
        fields[_t('Choice')] = self.ChoiceField(CHOICES[0], CHOICES)
        fields[_t('Color')] = self.ColorField('#FFFFFF')
        fields[_t('Resolution')] = self.DpiField('<dpi>')
        fields[_t('File')] = self.FileField('/home/images/logo.jpg')
        fields[_t('File Name')] = self.FileNameField('<filename>')
        fields[_t('In')] = self.FolderField('<folder>')  # folder
        fields[_t('Float')] = self.FloatField(3.14)
        fields[_t('As')] = self.ImageTypeField('<type>')  # png, jpg
        fields[_t('As')] = self.ImageReadTypeField('<type>')  # png, jpg
        fields[_t('As')] = self.ImageWriteTypeField('<type>')  # png, jpg
        fields[_t('Mode')] = self.ImageModeField('<mode>')  # png, jpg
        fields[_t('Resample')] = self.ImageResampleField(_t('bicubic'))
        fields[_t('Integer')] = self.IntegerField(-4)
        fields[_t('Integer+')] = self.PositiveIntegerField(0)
        fields[_t('Integer+0')] = self.PositiveNoneZeroIntegerField(0)
        fields[_t('Horizontal')] = self.PixelField('5%')  # accepts %, cm, inch
        fields[_t('Slider')] = self.SliderField(60, 1, 100)

    def apply(self, photo, setting, cache):
        # get info (always get this)
        info = photo.info

        # in case you use PixelField you can get width, height & dpi ...

        # ... from photo (use new_*)
        width, height = info['size']
        dpi = info['dpi']

        # ... or from user input (see actions/image_size.py)
        dpi = self.get_field('Resolution', info)

        horizontal = self.get_field_size('Horizontal Offset', info,
                            width, dpi)

        # collect parameters
        parameters = {
            'dpi': dpi,
            'horizontal': horizontal,
        }

        # return manipulated photo
        photo.apply_pil(foo, **parameters)
        return photo

    # icon: 48x48pixels
    icon = 'ART_TIP'
