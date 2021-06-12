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

from phatch.core import models
from phatch.lib.reverse_translation import _t
from phatch.lib.formField import IMAGE_EFFECTS

#---PIL


def init():
    global Image, ImageFilter, imtools
    from PIL import Image
    from PIL import ImageFilter
    from phatch.lib import imtools


def effect(image, filter, amount=100, repeat=1):
    """Apply a filter
    - amount: 0-1
    - repeat: how many times it should be repeated"""
    filter = getattr(ImageFilter, filter)
    image = imtools.convert_safe_mode(image)
    for i in range(repeat):
        filtered = image.filter(filter)
        if imtools.has_alpha(image) and \
           filter in [ImageFilter.CONTOUR, ImageFilter.EMBOSS]:
            filtered.putalpha(imtools.get_alpha(image))
        if amount < 100:
            image = imtools.blend(image, filtered, amount / 100.0)
        else:
            image = filtered
    return image

#---Phatch


class Action(models.Action):
    """"""

    label = _t('Effect')
    author = 'Stani'
    email = 'spe.stani.be@gmail.com'
    init = staticmethod(init)
    pil = staticmethod(effect)
    version = '0.1'
    tags = [_t('filter')]
    tags_hidden = IMAGE_EFFECTS
    __doc__ = _t('Blur, Sharpen, Emboss, Smooth, ...')

    def interface(self, fields):
        fields[_t('Filter')] = self.ImageEffectField(
            self.IMAGE_EFFECTS[0])
        fields[_t('Repeat')] = self.SliderField(1, 1, 10)
        fields[_t('Amount')] = self.SliderField(100, 1, 100)

    icon = \
b'x\xda\x01|\x07\x83\xf8\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x000\x00\
\x00\x000\x08\x06\x00\x00\x00W\x02\xf9\x87\x00\x00\x00\x04sBIT\x08\x08\x08\
\x08|\x08d\x88\x00\x00\x073IDATh\x81\xc5\x98{\x8c\\U\x1d\xc7?\xbfs\xef\xcc\
\xd2\xa5\xefN\xb7mJ\x84\xb6(\x04\x83\x98\xa84\x06+\x8d\x16\x89XJB\xd3J\x8cQ \
A\x12\x03\xd1FCI\xac\xa4\xd1D\x0c\x12\x1e\nhL0`\x9a&\xbe*Z\xa2\x18\r\x101\
\x96\x86\xfa\xc4\xe2\xa3J\x81\xd6>\xf65\xbb\xcb\xce\xce\xcc\xbd\xf7\x9c\xaf\
\x7f\xdc\x99\xd9-\xf1\xaf\xbdw\xdb_r23\xf7\x9e\xf9}\x7f\xdfs~\xe7\xfc\x1e0\
\x87\xd2:\xce;FO\xf6}t.1\xe6\\\xea#\xf1\xe8\xd0\xb1\xea\'\xce\xb5\x1d\xb3\
\x96\xfaH<^\x1f\x8aG\xe6J\x7f<W\x8a\x01\xeaoT\x1e\'f!\x93H\xc2\x99\x11\xca\
\xc6pe+\xecJ\xfd\xf5\xca\x13,\xe0VM@\x18\xa55\xd3\xf8\xe1\x9freY8sB`\xf4\xdf\
\x95;l!\x9f\xd28P\x07\x8d\xeb\xe0\x19\x13T\xf9\xe2\xd8\xbe\xf8Ce`\xcd\x89\
\x0b\xb9y\xda\x15\xeafL\x80&EhD\xf7A\xd6{o\x19\xefK\x8d\x05\xc0\xb3\x85\xb1\
\x8a*\xf8\x7f\x12Z\xb6\x9c1\xd0\x84\xb07\xdd\xc9\x81k\xdb\xbf\xec\xbe\x1b\
\xde[\xfd\xa4\xbc.rh\xd3\x89\xfd\xf4\x17\xc5*\x8d\x80\x8e\xd07\xf4r\xbc\x11@\
#\xb45.4i\x84Fx\xa5;g\xf0\xfb\xd5mRx\x04\x84\x02q_\xc2\xd2\xa2\xb8\xa5\xb8\
\xd0\x89C\xd4F\xe3\xca\x1f*\x93v\x17\x00u\x1dR\xca\x06\xa6\x84\x12\xae\x1cy2\
\xfa\x81\xe4\xd6(\xf8\xf7\x9a\xc90\xc0\xf3\xb7e\x1f\xe7xQ\xec\xc2\x04t\x88J}\
qt\xc8\xb5X=TO\x9e\x02\xf0\xe3\xfa\xa6\x0b\xb6A\t\x98\xd7\x02y\xdb\x8e\x05\
\xcc\t\x02\x108\x12\x85p}Ql(\xc1\x85\xc6\xe2\xf8nZ\xeeB?\xac\xe1\xb7_G\x1b``\
\xbb\xff\xb1\xa6\xec/\xd6\x16j\x1bx\x81:\xc6gv0n\x84\xf5Kn\xe1\xb5\xa2\xd8P\
\x02\x81\xd0d\xb3\xea\x10\xc6\x988Cq\x9bG\x95\x19\x16\x04\x08<(\xe3hj\xfe\
\xfa\xc5\x9f\xa5^\x14\xb7\x87SX\xc3\x94\xad\xd0\xb8\xb0\x065\xfd\x90\xa8\xfb\
\xd8g\xee\xb8\xa5BA\xf9\r\x9a\x01\xde>\xbf\xeaV\x86\nc\xce\x90\xe2g`<d\xb4\
\x0c\x9a,\x19mW\xf6\x8c>\x9c\xeeL\x02\x17\x9b\xf7\x0f\xab\xe3\xf3\x12\x00\
\xa7ku\xffta\x8b\xdf"\xc5\tL\xda\x1b\xb4XG\x1b\x94\xe9&\xf9\xe8\xa6\x08\xc0B\
\xee\xf3\xeaMmw\xbf\x8c\xfc\x84\x0b\xac\xbf\xb2\xc5\x16\xa9F\xc2\x0bK6f\xcf\
\xcd\x16\xdf\x8a\x18\x0f0\xf4h\xe56\xd2\xf0]RC^\x98\x00\xa7i\xcd\xde\xc0\x0c\
bP\x1fG\xa2\xf9\xaaj\x99\xbd\xcdj\x98\xad\x04\x8b\tz\x9d{\x97n\xc8v\x9d\x13\
\x02\x126\xfc\xf5\xe8)\xc4\x16\x05\xf2\xab\xb2\xf7\x12\x14,\x87\xa9\x08\x9bg\
p>\xd8b\xb0\x9a\xc1\xf9\x1a\xd6xv]m\x13/\xcd\x16\xbf\xf0!6C\xb5u\xfeF2\xddgA\
\x81\x14z#\x03\xf3`\x99\xb0\xcc \x01K\x80\xb6`L\xc7\x93\xa3\xd9eE\x8c/\x85\
\xc0\xc4\x81\xe8\xfa\x91\x0bX\xb9\xfc\x9e\xb0\x93,l"\xd3q21=\x02dB\xa9 \x01\
\xa5@\xdbe\xd4m\xdb\xaa\xed\xc5o\xa4\xc2\x04\xb2\x04\x1f\xad\x8d\x8f\x8c\x1d\
\x8dN\xc5\x1f\x88C5\xd2\x15\xca\xd8\xa747VY>HA\x99P\x02j\xea\xf9e\xb7\xa4/\
\x02\x0c\xfd<\xda|\xce\x08\x0c\xff\x9e\xd5K\xaf\xf6\xbf\xf0\xff\xb0\xabC\xe4\
\x96\xf9\x1a\xbfj\xae%\x1e\xb8W[-\xd3\x0e2B/\x06tHX\naROtu\xd8"\x1e\x1cy:\
\xbe\xf6\x9c\x10pK\xa3\xdf\xe99\xe2\xda\xc6\xf4%\x1d\x0eO\xb9)\xeb\x8b\x89\
\x1e\x03X~?\x0f)\xd3\x1d\xd3gb\x86\x0b\x99\x7f\xb1G\xc0\xb1\xd2-\xe0\xae\xb3\
N`\xe4\xf9\xe86[\xe3.\x1a\x1de%@:\xc8\x9eP\x17\x04\xdb\xd4\x9d\xb3\xe2!\xbeM\
\xca~2\xf5\x0e\xb6%\xc0T\xbc\x02\xa0\xfe\x1d\xb7\xcb\xcc\xe6\xab\xaa\xb5g\
\x95\x80\xf6\xd3o\x17\xdb#zU\xc9\xb2\xadyJ\xec\x9a\xa4\x1a\x03M\xb1\xe8\xe4n\
.\xebMN\xb5\xaf\xeb>\xa4\xa0D8\xf1\xf8\xf07\xe2g\xb2\xf9nwh\x8b\xd0\xc6\xcf\
\x96\xc0\xac"\xf1h\x7f\xfc5\x17\xac\x1a^\xd3\xe1\xde\xc3\xa6\xae 5\xd40hFk\
\xc0\xbf\x02 \xcf\xf8\x19\xc1&\x02\xfa\xb8Tp\xa9%\xc2\xda\x06\x81W\xcf*\x01\
\xe7\xed\xf20\x08a\xd0\x1d\xed=L\xa2\x8f\xa9\x01\xd6\x1469#@z\xf7n\x85nd\x16\
\x16\x19\xea\xc4\x03%@\x0b\xb2\x19\x87\xfa\xac\x10\xc8F\xc3\x94\x93\xc3\xcc\
\x7fp\xe8\xab\\\x12\x85hm\xd6b=SBM \xf5C\x00Go\xe6<\xda\xfa4\x00&\x08\x86\
\x1cyV\xd4&_\xfd\x11\xfb\xe7\xca\xdb\xb2\xbdg\x95\x80\x86\xf5\x8c\xbc6\x87\
\x86-\xb4j|8\x9b4GS\xa6\x16\xd0\x12\x96\xe0\xf4\x19*\x83c\xee{H\x17v\xfe\x05\
\x0e,\x02\x12A\xdb\xa0\xc1\x84&\xb2\x1bfk<\xcc2\x17\xd2\x9d\xf4\r\xaf\x8b\
\x07\x99b\xa1\x1a\xd0]yk\xe7\x81\xcaR\xfd\xd6\x05j!\xd3e(_|\x04\x8a\r\xfa\
\x0c\xf5\x83-\xb4c8\x7f\xc3\xc0\x03\xfc\xe9\xac\x13\x00\x18\xba;\xfe\x8a\xc4\
\x97{\xc6\xb7\x94\xdf\xf1\xa9\xb0D\xa0<\xa3\x86^=\x00\xceP\x15\x98\xc7o\xfaL\
\xdb\x17\xef-^\x99\xcd\x9a\x80\xc0\x86o\x8f\x0e\x846\xebi+\xf7\xebTX\x9a\x17\
1\x16:\xa5@g\xf5;\x7f\x121\xf7\x0e\xfc\x9a/\x155\xbc+\xb3\x0ed\x06"\xf5\xd7\
\xd0\x08/\xd2\x00\x9b\x12\xae\x99G[:yP~\xefw\xf2\xa1\x14B\xc6\x17\xca4\xbecG\
1\xd16\xa2\xd3uw\xbf\xcb\xc2\xe7\xf0\x18\x9d\x06D\xef\x93\xfc;\xc6\xfe\x95\
\x07\xd8R\x14\xef\xadR\xb8\xa4\xb4\x1f\xe1!\xec8y\x15\xffq\xe2[\xdd\x1a\xb8G\
\x02\xba.TZ\'\xe2\x0c\xfc\xb2\x14\xe9=T\x06+4\xe5,R[\x84\x19;\xd0\xf9l\xf79\
\xae\x19\xf8#/\x94\x85\t%\xf6FO\xaf\x8anf\xb1\x8b\x04\x04?=|\x06>\xff\xeckf\
\xec?q9\x97\x96\x85\t%\xed\xc0\xb1m\xcc\xab\xc6\xd1\x1baT5\x8d\t?%B\xb7)1\
\xc3\x8d\xcc v\xfc\xb7\xee\xb8\xe4\x8a\xbf\xd2(\x03\xbb\x94\x1d8\xaf?z\x00\
\xa3\x86\x07y\x08\x19\xf8\x00\x99\xcf\xcb\x80,\xe4\xc3\x07H=\xab\x17\xa7<V\
\x06.\x94D@\xe7\xb3\xb5{xC\x9e\xf2tz\xb8\x1d\xa3g6\xe7\x80\x14n\x14\xd3]\xbc\
"R\x98\x80v3\xc0y\xb6\xbc\x1b\xaf\x04\x84\x90\xf7sS\xe5iO\xda\x1dy}\x0f0\xff\
\xe4;y\x7fQl(\x81\xc0\xc8\xabT\xe8\xf4\xae\xba\x12\xc8W:\x90\x1b\x9ctv\xc1\
\x93\xef\x90\x0f\x90\x18\x8b\x8abC\t\x04\x9e\xdd\xcc)2\x9a\xbd\xfb\x9f\x0e\
\x19\xe5\xbb\xd0-\xc6\x12r2az\xce\xdf\x8bbC\t\x04\xb6o\xc73\xae\x83\xd8\x99W\
\x9a:?D\xbe\xfa\xbd\xa8l\xe0\x8c\xfa\x85/\xcf\xbe\n\x9b)\xe5\xc4\x81\xc4\xef\
@\xa4\xbd\xa6b\xa7\x003\xf2\x93Zu\x10\xd9\xf4\xceD\x8e\x9f\x95\x82KI\x04\x06\
\xf6\xf2g\x1az0\x02\xb9|\x85\x89\x04\xb1A\xc5\xa0\x0f\xa8\xe6\xfd]\xaa\x8eS-\
\xe3\xce2p\xa1\xc4T\x02\xe0\xf4U\xee\x9e\xe4\xcd\xb0\xd3\xa7\xf4w;\x8b\x9e\
\xfc,X^\xcb\x1c^\xd4\xe6\xc3+\x8er\xba,\xccR\t\x00\x9cz\x17\x03I\xca\xed\xc1\
\xf8H\x08\xac\xf6Fj\xe2\xb8\x0b<\xb9\xe6_\xec\xe9\x84\x88\xd2\xe4\x7f\xa0\
\xa7\xce=%\x05\xa1\x93\x00\x00\x00\x00IEND\xaeB`\x82\x00a\x9a\x0c'
