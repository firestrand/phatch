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

# Embedded icon is taken from www.openclipart.org (public domain)

# Follows PEP8

from core import models
from lib.reverse_translation import _t

#---PIL


def init():
    global Image
    from PIL import Image

    global math, r
    import math
    r = math.radians

    global imtools
    from lib import imtools

    global HTMLColorToRGBA
    from lib.colors import HTMLColorToRGBA

TOP = [100, 30, 0, 0, 120, '0%', '5%']
BOTTOM_STRETCHED = [35, -30, 0, 0, -120, '30%', '5%']
LEFT = [100, 0, 30, 120, 0, '5%', '0%']
RIGHT_STRETCHED = [35, 0, -30, -120, 0, '5%', '30%']
TOP_LEFT = [100, 5, 5, 40, 40, '15%', '5%']

PRESETS = {
    _t('Top'): TOP + ['None'],
    _t('Top Stretched'): BOTTOM_STRETCHED + ['Flip Top Bottom'],
    _t('Bottom'): TOP + ['Flip Top Bottom'],
    _t('Bottom Stretched'): BOTTOM_STRETCHED + ['None'],
    _t('Left'): LEFT + ['None'],
    _t('Left Stretched'): RIGHT_STRETCHED + ['Flip Left Right'],
    _t('Right'): LEFT + ['Flip Left Right'],
    _t('Right Stretched'): RIGHT_STRETCHED + ['None'],
    _t('Corner Top Left'): TOP_LEFT + ['None'],
    _t('Corner Top Right'): TOP_LEFT + ['Flip Left Right'],
    _t('Corner Bottom Left'): TOP_LEFT + ['Flip Top Bottom'],
    _t('Corner Bottom Right'): TOP_LEFT + ['Rotate 180'],
}

FIELDS = ['Scale', 'Left Shear Angle', 'Top Shear Angle',
          'Bottom Shear Factor', 'Right Shear Factor',
          'Horizontal Offset', 'Vertical Offset', 'Transpose']
OPTIONS = ['Top', 'Bottom', 'Right', 'Left', 'Top Left', _t('User')]


def perspective(image,
        width, height, skew_x, skew_y, offset_x, offset_y,
        left, top, back_color, opacity, resample, crop, transpose):
    image = imtools.convert_safe_mode(image)
    if transpose == 'NONE':
        transpose = None
    else:
        transpose = getattr(Image, transpose)
        image = image.transpose(imtools.get_reverse_transposition(transpose))
    if opacity != 100 or back_color != '#000000':
        image = image.convert('RGBA')
    if width != 0:
        width = 1 / width
    if height != 0:
        height = 1 / height
    offset_x = offset_x * width
    offset_y = offset_y * height
    skew_x = math.tan(r(skew_x))
    skew_y = math.tan(r(skew_y))
    matrix = (width, skew_x, offset_x, skew_y, height, offset_y, left, top)
    perspectived = image.transform(image.size, Image.PERSPECTIVE, matrix,
        resample)
    result = imtools.fill_background_color(perspectived,
        HTMLColorToRGBA(back_color, (255 * opacity) / 100))
    if crop:
        result = imtools.auto_crop(result)
    if not (transpose is None):
        result = result.transpose(transpose)
    return result

#---Phatch


class Action(models.Action):
    label = _t('Perspective')
    author = 'Stani'
    email = 'spe.stani.be@gmail.com'
    init = staticmethod(init)
    pil = staticmethod(perspective)
    version = '0.1'
    tags = [_t('transform'), _t('filter')]
    __doc__ = _t('Shear 2d or 3d')

    def interface(self, fields):
        fields[_t('Projection')] = self.PerspectiveField('Left')
        fields[_t('Scale')] = self.SliderField(100, 1, 200)
        fields[_t('Left Shear Angle')] = self.SliderField(5, -180, 180)
        fields[_t('Top Shear Angle')] = self.SliderField(5, -180, 180)
        fields[_t('Bottom Shear Factor')] = self.FloatField(40)
        fields[_t('Right Shear Factor')] = self.FloatField(40)
        fields[_t('Horizontal Offset')] = self.PixelField('15%')
        fields[_t('Vertical Offset')] = self.PixelField('5%')
        fields[_t('Transpose')] = self.OptionalTransposeField(
                                    'None')
        fields[_t('Background Color')] = self.ColorField('#000000')
        fields[_t('Background Opacity')] = self.SliderField(0, 0, 100)
        fields[_t('Resample Image')] = self.ImageFilterField('bicubic')
        fields[_t('Auto Crop')] = self.BooleanField(True)

    def values(self, info):
        #get info
        dpi = info['dpi']
        x, y = info['size']
        #get field values
        scale = self.get_field('Scale', info) / 100.0
        return {
            'width': scale,
            'height': scale,
            'skew_x': -self.get_field('Left Shear Angle', info),
            'skew_y': -self.get_field('Top Shear Angle', info),
            'left': -self.get_field('Bottom Shear Factor',
                                        info) / float(y * 100),
            'top': -self.get_field('Right Shear Factor',
                                        info) / float(x * 100),
            'offset_x': -self.get_field_size('Horizontal Offset',
                info, x, dpi),
            'offset_y': -self.get_field_size('Vertical Offset', info, y, dpi),
            'back_color': self.get_field('Background Color', info),
            'opacity': self.get_field('Background Opacity', info),
            'resample': getattr(Image, self.get_field('Resample Image', info)),
            'crop': self.get_field('Auto Crop', info),
            'transpose': self.get_field('Transpose', info)}

    def get_relevant_field_labels(self):
        relevant = ['Projection', 'Background Color', 'Background Opacity',
            'Resample Image', 'Auto Crop']
        projection = self.get_field_string('Projection')
        if projection != OPTIONS[-1]:
            for label, value in zip(FIELDS, PRESETS[projection]):
                self.set_field_as_string_dirty(label, str(value))
            return relevant
        return relevant + FIELDS

    icon = \
'x\xda\x01V\x06\xa9\xf9\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x000\x00\
\x00\x000\x08\x06\x00\x00\x00W\x02\xf9\x87\x00\x00\x00\x04sBIT\x08\x08\x08\
\x08|\x08d\x88\x00\x00\x06\rIDATh\x81\xe5\x9amh\x9dg\x19\xc7\x7f\xd7s?\xe7m[\
zNb\xda\xd2\x8d\xacY\xe6\xf4\x83\xf3C\x87kVVq\xa3\x18\xc5|\xd2m\x8d\xb2%D$\
\x84"\x1d\x94Rd\x1fTp\xe8\x07\x11\x0b\xce"\xa38\x95\x19[\xa6\xb1~p\xd2\riXMM\
\xc7\xb6\x94\r\xd3V\\\xda\xc1\xe8\xd6\xd4\x98\x97\xa6\xcb\xcb9\xe7\xbe/?\x9c\
s\x9e4\xedIr\x9e\xe7\x9c\xb39\xfc\xc1\r9\xe1y\xce\xf9\xffs\xbd\xdc\xd7s\x9f\
\x88\xaa\xf2q\xc6\xfb\xa8\x05T\xcb\xff\xa7\x01\x11yTDv\xd4ZL\x14B\x19\x90\
\x02>p\x19x\xa0>\x92\xc2\x116\x02\xf1\xae\xae\xae{\x06\x07\x07\xe7\x81\x9f\
\xd5CPX*6 "\x024\xcc\xcd\xcd=\xd0\xde\xde\xfe\xb7\x91\x91\x91>\x11\x89\x89\
\xc8]"\xf2\xaa\x88\xa4\xeb\xa8sU\xc2F\xc0\xcc\xce\xce~\xc2\x18sKkk\xeb/\xce\
\x9e=\xfb\x9b={\xf6\xcc\x00\x8f\xa8\xeal=\x04\xaeG\xe8"\xb6\xd6\x06\xf7466~\
\xe3\xc0\x81\x03\xa7\x8f\x1e=\xbaED\x0c\x80\x88\xec\xf80\xa3\x11\xda\x80sn\
\xc5\xce\x97J\xa5>\xb5s\xe7\xceWN\x9d:\xd5/"1`7\xf0\xe9Z\t\\\x8f\xd0\x06\xb4\
\xcc\xd6m\x8cI\xb5\xb5\xb5\x1d\x1a\x1b\x1b{~\xdf\xbe}O\x03\xaf\xd5D]\x05D\
\xd9\x07V\x9d=\x9a\x9a\x9a\xba\xf6\xee\xdd{zpp\xf0s"bD\xe4\x9b"\xf2\x93*\xf4\
\xadK\xd5)\xf4\xcb\x91q\xe6\xb36x\x9dJ\xa5\xee\xd9\xbe}\xfb\xc9\xe1\xe1\xe1=\
\xc0\x9f\x80\x83U\xab\\\x83\xaaG\x89\x91\x8b\x93|\xef/o\xf1\x8f\xf7g\x00p\
\xce\x01$[ZZ\x9e\x19\x1d\x1d}v\xff\xfe\xfdK\xb2\xcc\xe7\xab\xfd\xbc\x1b\x89\
\x12\x81\x95\xbf\x10\x98\x9e\xcfrp\xe8\x9f\xfc\xea\xf48\x1f,eq\xce\xe1\x9c#\
\x9dN?\xd6\xdb\xdb{z``\xe0~\xe0.\xa0_Dn\xab\x8d\xf4\x02Q\x8ax\x85\x03A\x82\
\x9f\x87/L\xf2\x83\x97\xceq\xf6\xf2,\xd6Z\xac\xb5\xc4\xe3\xf1\xbb\xb7m\xdb\
\xf6\xca\x89\x13\'\xbe\x0ct\xab\xea\xb5\xeae/S}\x04n`j>\xcb\xcf\x87/\xf0\xc2\
\x9b\x97X\xcc\xe5\xb1\xd6\xe2\x9cK677\x1f:v\xecX\x1b\x043\xd5\x80\x88|!\xa2\
\xee\x00?\xe4\xf5\xea\x8a\x0eT\x15UE\x84\x9b\xfa\x92\x02\xc3\xefLs\xee\xca5v\
\xdf\xbb\x89\xad\xe9\x04\xce9T\xd5\x14\xefU\x11y\x1a\x18\xaf\xd6@\xa4.\xa4\
\xaa8\xe7\n)\xe2\x9bU\xd7\\\xd6\xf1\xdc\x99\xcbd\x8b\x91\xc8f\xb3\xcb&U\xcf\
\xabj\x0e@D\x9aD\xe4\x93Q\x0c\x84\x8d@ \xbc\xf8\x17%\xe9\x1b\xf2n\xed\xc7R\
\xeb\x1c\xde\xea\xdb\x07@\'p\'\xf0\xc3\xb0zB\x1b\x00\x82.\xe3\x9c#\x113\x98u\
\x0c8k\xd15\x0c\xa8\xea\xf3Qt@\xc4\x14*u\x18\xe7\x1c\t\xdf\xac\xbb\\1\xe5*AD\
\xee\x16\x91?V\xdan\xa3\xa4\x90^\x1f\x81\xb8o\xf0\xd6K!k\x11u,--U\xf2\x11\
\x17\x80\x1fU\xdan#\x19\xb0\xd6R*\xe4\x8aR\xc89D+\x8b@qX|\xbd\xf4ZD\xee\x05\
\xce\xa9\xaa-w}\x14\x03nE\r\xf8\x95\xd4@\x0e*4p="\xb2\t\xf81\xf0$\xf0v\xb9kB\
\x1b(\xe5\x7f\x10\x01\xdf\xc3\xac\xa2\xed=9\xcf\xf9\xecIv\xe9\x13\xe0*N\xa1\
\x00U\xbd\x02|e\xadk"\x15q\xa9\x95Zk\x0b\x85\x1a\xbby]\x8a\xbd\xc9\xaf\x17\
\xbf\xcd\x99\xb9?c\xad\x0bS\xc4_\x14\x91\x8a\'\xd8\xea\xdb\xa8o0\n9\x96xO\
\xff\xc5fie\x91\x0f\xf8\xed\xec\x01rs\x8b\xa4\x16\x1aP\xe7p\xael\n\x97\xe3U`\
\xb2n\x06\xae\xdf\xc8\x9cs\xc4b>/.\x1cbx\xf1\xf78\xcd\x11s>\x19\x7f3\xa9l\
\x8cT>\xc3\x06\x97AD@\x84|>/\xe5\xdeSD\xee\x00\xfe\xad\xaaYU\xbd\n\x9c\xa9\
\xa7\x81\x15E||\xe1Y\xfe~\xed\x05R$\x88s\x1b>>f\xc9\x92\x91\x0c\xe4\xa1A\xd3\
x\x9e\x87S\x871\xa6\xac\x01\xe0;\xc0I\xe0\x0fa\xf5D)b-E@D83\xf72\x19\x97!)I\
\xe2\xc4\xf0\x89a\xd4C\x104\xa1\xb4g\x1e\xc27\x1e\x16\x83\xe7ye\r\xa8\xea\
\x93auD5\xa0\xa5\x19\xc8\xf3<D\x84F\xd7\x88j\x8e\x04I\x12\x12/D\x00\x83\'\
\x86\x8e\x96Nv4\xdc\x17\xa4\\)\x02"\xd2\x04\xfc\x14xJU\xdf\x8f*>\x8a\x01\xac\
\xb5A\xd3\x17\x112\x9aF5OB\x92$%\x81\x8f\xcf\xed\xa9;\xe9\xda\xf2(\tbA\xcb\
\x05\xa6s\xb9\xdc4\x80\xaaN\x89\xc8\xef(\x9c\xb1VE\xe86*"\xce\xf3<Jk\x83l M\
\x86F\xaf\x91\xe6\xd8F\x1ek\xf9:}\xad\xbd4\xc4o\xc5\x18\x831\x86\x85\x85\x85\
7\x86\x86\x86\xda\xfb\xfb\xfb\x03\xf3\xaa\xfar\xb9#\x9a\xb0Dj\xa3E#\x88\x08i\
i@\x8c\xb0}\xf3\x83<\xd8|?q\x89\x01A\xab\xcdONN>\xd3\xd9\xd9\xf9\x14\xf00\
\xd0\r<^\xad\xe8\xeb\x89\xb4\x13\x97\xc4\x8b\x08[om\xe3\xe1;\x1ebKrcP\x17\
\x00\xf3\xf3\xf3W\xc6\xc6\xc6zzzz\xfeZ\x9cc\x8e\x17WM\x89r\xac\xe2`9\x02\xbb\
[\xbf\xca\xed\xa9M\xf8\xbe\x1f\xac\x99\x99\x99\xa1\x81\x81\x81\xcf\xf4\xf4\
\xf4\xdc\x07t\xd4V\xf2J"md%D\x04\xe3\x19D\x04\xcf\xf3P\xd5\xc5\x8b\x17/~\xbf\
\xa3\xa3\xe3 \x90\x07N\x00\xef\xd6N\xee\xcdD\xeaB\xa5\xda+\xa5\x8b\x88p\xf5\
\xea\xd5\xb7GGG\x1f\xe9\xeb\xeb\x9b(=\xebR\x18\x0b\xeaJ\xe46\xaa\xcbOYvbb\
\xe2\xb9]\xbbv\xed\x05R\xc0K"\xf25U\xbdT[\xa9\xe5\x89\x92B\xd6\xda\xc2`\x96\
\xcdf\'\xc6\xc7\xc7\xbf\xd5\xdd\xdd}\xbcX\xa8K@{\x8d5\xaeI\xd8"\xb6\xd6\xdai\
\xe7\x1cSSS/\x1e>|\xf8\xb3\xdd\xdd\xdd\xff\x01\xbe[\x0fq\x15Q:\xa0\xaad\x01I\
`\xeb\x91#G\xfa\x80\x18 \xc0F\xe0Ka\xde\xa7\x96K\xc2l\x86\xc5/\xfa|\xe0\x16`\
\xee\xc6s\xd2\x8f\x82P)\xa4\x05r\xc0!\xa0\xb7.\x8aB\x12*\x02\xc1M"f\xb5S\x82\
\x0f\x9bH\x06\xfe\x97\xf8\xd8\xff\xb3\xc7\x7f\x01P\xac\x83\xc2\x03\xdcD\xbc\
\x00\x00\x00\x00IEND\xaeB`\x82\x9e\x92\x0c"'
