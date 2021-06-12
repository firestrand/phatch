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

# Embedded icon is designed by Igor Kekeljevic (http://www.admiror-ns.co.yu).

# Follows PEP8

from phatch.core import models
from phatch.lib.reverse_translation import _t

#---PIL


def init():
    global Image, ImageOps, imtools
    from PIL import Image
    from PIL import ImageOps
    from phatch.lib import imtools


def colorize(image, black, white, amount=100):
    """Apply a filter
    - amount: 0-1"""
    if image.mode != 'L':
        im = image.convert('L')
    else:
        im = image
    colorized = ImageOps.colorize(im, black, white)
    if image.mode == 'RGBA':
        colorized = colorized.convert('RGBA')
        colorized.putalpha(imtools.get_alpha(image))
    if amount < 100:
        return imtools.blend(image, colorized, amount / 100.0)
    return colorized

#---Phatch


class Action(models.Action):
    label = _t('Colorize')
    author = 'Stani'
    email = 'spe.stani.be@gmail.com'
    init = staticmethod(init)
    pil = staticmethod(colorize)
    version = '0.1'
    tags = [_t('color')]
    __doc__ = _t('Colorize grayscale image')

    def interface(self, fields):
        fields[_t('Black')] = self.ColorField('#735710')
        fields[_t('White')] = self.ColorField('#FFFFFF')
        fields[_t('Amount')] = self.SliderField(100, 1, 100)

    icon = \
b'x\xda\x01\x1f\x08\xe0\xf7\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00*\
\x00\x00\x00*\x08\x06\x00\x00\x00\xc5\xc3\xc9[\x00\x00\x00\x04sBIT\x08\x08\
\x08\x08|\x08d\x88\x00\x00\x07\xd6IDATX\x85\xcd\x98[lT\xc7\x19\xc7\x7fs\xce\
\xd9\xb3g\xed\xdd\xb5\xbd`\x16\xb0\r,\xc1\x84D\x16\xc4B\xa9L\x13\xa9\xed\x03\
(\x15Q\x93*\x12R\x93T"\xb1\x9dU\xd5\xa8Q\x1eKT\xd2(\xd0J\x95\x8a\xf2P\xa9u\
\x95\xa0\x88bZT \xc5\x12\x94J\xc0K\xa3p7\x11\x11P9$\xb1Y\xd9\xeb\xa5+\xdbk\
\xef\xed\\\xa7\x0f\xde5\xb6\xb1\r\x0e\x17\xf7\x93>\xcd\x99s\x99\xf9\xcd\xff\
\x9b\x99ov\x91R\xf2\xff\xe4o\xbc\xf1F`\xa6\xfbBJ\xc9BZ<\x1e\xf7\x01/(\x8a\
\xf2\xaa\xcf\xe7k\x06\x1al\xdb\xbe\xe9y\xde\x96\x8e\x8e\x8e\x9e\xf2{\xdaB\
\x01\xb6\xb7\xb7\xaf\x03\xda|>\xdf\xf6\x8a\x8a\x8aE~\xbf\x1f)%\xb6m\xe38\xce\
J\xe0%\xe0\xb7\x0b\x06\xda\xde\xde\xfe\xb4\x94rW0\x18\xdc\x12\n\x85\xd0u\x1d\
\xc7q\xb0m\x1b\xd7u)\x14\n\x14\x8bE\x14E\xf9\xf7\xe4\xef\x1e\x19hkk\xebSR\
\xca\xf7\xc3\xe1\xf0\xf3\xb5\xb5\xb5h\x9a\x86\xe388\x8e\x83\xeb\xba\xb8\xae\
\xcb\xc8\xc8\x08\xf9|\x1eEQ\xbe\xf4\xf9|\x9f=R\xd0\xb6\xb6\xb6\'=\xcf{?\x1c\
\x0e\xffx\xd9\xb2e\xc2\xef\xf7\xe3\xba.\xb6m#\xa5\x9cP3\x9dN\x93\xcf\xe7\x11\
B8R\xca\x9fvttx\x8f\x04\xb4\xad\xadm\x99\xe7y\xbf\xab\xac\xac|9\x16\x8b)\x81\
@\x00\xcf\xf3& =\xcf\xc3\xb2,L\xd3$\x99LR(\x14P\x14\x05EQv\x1f8p\xe0\xdc\xf4\
\xf6\x1e8h<\x1e\xd7<\xcf\xfb\x85\x10\xe2\xd7\xb1X,TWW\x87\x94\x12\xd7u\'@\
\x1d\xc7\xa1X,R(\x14H$\x12\x14\x8bE\x84\x10H)\xcf\x17\x8b\xc5\xf7gj\xf7\x81\
\x82\xc6\xe3\xf1\x1f\xb8\xae\xfb\x87\xaa\xaa\xaa\'\xd7\xad[GEE\xc5Dx\xcb^\
\x06\xccf\xb3\xf4\xf5\xf5a\x9a&\x00\xaa\xaa\xf6\xa9\xaa\xfaBWW\x97\xfb\xd0@\
\xe3\xf1x=\xf0{\xd7u\xb7\xad]\xbb\x96\x95+W\xa2\xaa*\x9e\xe7a\x9a&\xb6mS(\
\x14\xc8\xe7\xf3\xe4\xf3y2\x99\x0c}}}\xb8\xae\x8b\xaa\xaaH)\xd3\x8a\xa2l9t\
\xe8\xd0\xe0l}\xdc\x17hWWW}OO\xcf/#\x91\xc8k\xa3\xa3\xa3\x81h4\xca\x9a5k\xf0\
\xf9|\xd8\xb6\x8di\x9a\x14\n\x05r\xb9\x1c\xb9\\\x8el6K:\x9d&\x91H\xa0i\x1a\
\x86a\x00\xe4\x02\x81\xc0\x8b\xfb\xf7\xef\xef\x99\xab\xafo\x95\x99\x8e\x1d;\
\xb6\xd1\xf3\xbc?VVV>\x1d\x08\x04\xd0u\x1d\xd34I\xa7\xd3|\xf3\xcd7\x18\x86A \
\x10 \x9f\xcf\x93\xcdf\' \x93\xc9$\x83\x83\x83\xe8\xbaN(\x14BJi\x1b\x86\xf1\
\x93}\xfb\xf6\x1d\x01\xe6\x04\x99\xb7\xa2]]]\xaf9\x8e\xf3g\xd34\xb5\xf2\x96b\
\x18\x06\x9b6mb\xfd\xfa\xf5\xb8\xae\xcb\xb9s\xe78y\xf2$\x91H\x84\\.G&\x93\
\xe1\xe6\xcd\x9bd2\x19\x82\xc1 \xa1P\x08\xc7q<]\xd7\xdf~\xec\xb1\xc7>\xb9\
\x1b$\xccS\xd1\xce\xce\xce\xce\xa1\xa1\xa1\x97\x01*++ill\xa4\xa6\xa6\x06\xc3\
0(\x16\x8b\xf4\xf6\xf6\xf2\xec\xb3\xcf\x92\xc9d\xb8r\xe5\n\x87\x0f\x1f\xc6q\
\x1c\x06\x06\x06\x10B\x10\x0e\x87\t\x85B\xe5\xadh\xf7\xc1\x83\x07w\x02\xde]\
\xba\x9d\x1f\xe8\x8e\x1d;\xde\xbap\xe1\xc2\x07###X\x96\x85a\x18,Y\xb2\x84\
\x96\x96\x16\xb6n\xddJSS\x13\xb7n\xdd\xe2\xc4\x89\x13l\xd8\xb0\x81|>Oww7\x87\
\x0f\x1fF\xd34\x16-ZD0\x18dtt\x14\xc7q\xf6\x1e=z\xb4\xfd^!\xef\t4\x16\x8bU[\
\x96\xf53]\xd7w[\x96%\xa4\x94\x84\xc3a\x82\xc1 CCC8\x8eC4\x1a\xe5\xcd7\xdf\
\xe4\x99g\x9e!\x99Lr\xea\xd4)6o\xdeLOO\x0f\x9f~\xfa)\xa9T\x8aH$\xc2\xd8\xd8\
\x18\xa6i\x1e;~\xfc\xf8\x8f\xe6\x03\t\xa0\xcc\xf5p\xc5\x8a\x15\xcbkjj\xfeS[[\
\xfb\x9bB\xa1 L\xd3\xa4\xae\xae\x8e\'\x9exb\xe2\x00\x91\xcdf\xb9q\xe3\x06;w\
\xee\xe4\xc3\x0f?\xc4u]\x1e\x7f\xfcq:::0M\x13\xcf\xf3\xc8f\xb3\xa4R)\xc6\xc6\
\xc6\xceo\xdb\xb6\xed\xc5\xf9B\xce\t\xda\xd8\xd8\xe8\xaf\xae\xae\xeejjj\x8a\
\x0e\x0f\x0fcY\x16\x1b7nd\xd3\xa6M\xa4R)\x06\x07\x071M\x13!\x04\x9a\xa6\x91\
\xcdf9p\xe0\x00\x17/^d``\x00\xc7q\xb8t\xe9\x12_\x7f\xfd5\x8a\xa20::z\xbd\xa9\
\xa9\xe9{\xdb\xb7ow\xe6\x0b\ts\x84\xbe\xae\xae\xee\xa3h4\xfa\xfa\xf0\xf00###\
477\xd3\xdc\xdc\xcc\xe5\xcb\x97\xb9~\xfd\xfa\x04di/\xc4\xf3<\x8a\xc5"\x8d\
\x8d\x8d<\xf7\xdcs\x9c={\x96\xbe\xbe>4Mc\xf9\xf2\xe5I\xd7u\xd7\x9e>}:\xfbm a\
\x16E\xeb\xeb\xeb7\xa8\xaa\xfaz\xa1P \x93\xc9\x10\x89D\xa8\xad\xad\xe5\xcc\
\x993\\\xbbv\r\xd34Q\x14\x85\x86\x86\x06V\xacX\x010\xfesA\x08\x12\x89\x04\
\xd9l\x96\xde\xde^\xfa\xfb\xfb)\x16\x8b444\xbct?\x900\xcb>*\xa5l\x05H\xa7\
\xd3\xa8\xaaJ$\x12\xe1\xea\xd5\xab\xa4\xd3i,\xcbBUUV\xadZ\xc5\xd2\xa5K\xf9\
\xfc\xf3\xcf\'\x8ej\xba\xae#\x84\xc0\xb6m\xc6\xc6\xc60\x0c\x83\x96\x96\x96\
\xbf\xef\xdd\xbb\xf7\xcc\xfd@\xce\n\x9a~5\xfdj\xf8D\x18/\xe7\xe1\xf7\xfbI&\
\x938\x8e\x83i\x9a\xe8\xbaN}}=\x9e\xe7\xd1\xdd\xdd\x8deY8\x8e\x83\xae\xeb\
\xa8\xaa\x8aa\x18\x08!X\xbcx1\xb1X\xec_\x9d\x9d\x9d\xdb\xee\x17\x12f\x98\xa3\
\xe2=Q\xcdw\x19\x16\xff\x14(\x8d\n\xb2AR\xf3N\r^\xc2C\xd7u\x82\xc1\xe0\xc4\
\x8a\xb7,\x0b\x00\x9f\xcf\x87\xa6\x8d\x8fy\xfd\xfa\xf5,]\xba\x14]\xd7wutt\
\xfc\xeaA@\xc2L\x8a*\xac$\x012 q[]\xf8+\x0c\xad\x1d\xa2bI\x05\xd2\x95\xc8[\
\x12/\xe5\xe18\x0e\x9a\xa6\xe1\xf3\xf9\x10B\x00\xb0z\xf5j\xa2\xd1h\xae\xa6\
\xa6f\xfb\x9e={\x0e=(\xc8\x99A%\xab\xb8\x06\xbc\x02\x1c\x01\xce\x82\\\'\xc9\
\xa99\xc8\x80\xfa\x95J\xf5\x7f\xab1\x0c\x03EQ(EDVUU\xfd%\x1a\x8d~\xf0\xf1\
\xc7\x1f_~\x90\x80e\xbb3\xf4\xef\x8a\xfd\x14y\x85\n`\rP\x0f\xf4\x00\xdd\x80\
\n\x84@1\x15\xaa\x8eW\xa1\ri\xf8|\xbe\xcf\xa4\x94o\r\x0c\x0c\\|\x18\x803\x82\
\x8a\xf7\xc4b\xaa\x18d\t*\xd5@\x02\x18\x00,\xc0)\xb9\r\x98\x10\xbe\x1a\x1e\n\
\xf6\x05\x7f\xde\xdf\xdf\xff\xb7\x87\tX\xb6\xe9\xa1o\x11\xcb\x85-\x13R\xe5Kn\
\x1f\xbe\x8c\xf1ka\x8ba\xe1\x89^\xc2\x9c\x1f}~\xf4\xdd\xcc\x8eL\xeaQ@\xc2\
\xcc\xab^\x01\x9e\x02"\x80\x8e@ \xe9#\xccW\xf2mYxT`\xd3m\xc1\xff{\xbaW\x9b\
\x92B\x05B\x08G|\x7f\x81X\xe6\xb4\xa9\xb9>E+C|\xb4@,s\xdaT\xd0\x02\xef\xe0\'\
&\xae\x88\x96\x05\xe2\x99\xd5&@\xc5\x17\xa2\x06\x8f\x95\x84\x11d\xd9\'\x10s\
\x1e\xaa\x1f\xb5\xdd\x86I\xb1\x99\x1b\x08\xfa\x81\x9b4\xf2\x0fv-\x1c\xd6\x9d\
v{\x1f\x1d#O/\xf0\x05\xe0\x02\xd5|g\xbe\x8d\x95s\xfe\xc3\xd8I\xa6f\xa6?\x89#\
\xa4\xf9!\x01\x12\x84x\x8d8\x17\xca\x8f\xa6\x95\xccR\x87\xf14!\xef\xe1zJy\
\xb7\xc1\x89\xd2\xc9\\a<\xff\xf8XL\x804*\xa03\xae\xb8(\xb92\x0bp\x19\xc0\x9b\
T\x96\xdd\x9d\xa1\xee\xce\xf2\xac\xec\x13mN\x11\xb1T\x06\x81\xb5\xc0\x12\xc0\
_\x82R&\x7f4\xcd\xa77>\x1d`.w\xeeR\x9f\xd2F\x99\xb6\xacX\x00XTr\x7f\xe9\xfed\
\xd0\x99\xa0\xee\xb5\xf3\xe9\xd7\xda\xb4{\xea\xa4z\xb9\x9c,\x90\x0b\xb7C\xef\
\x03\xc2%\xaf,y\xc5$u\xcb\xe1\x87\x99C<=\xd4wS\xf5n\x83r\xca\xfd\x94\x15\x9d\
XL\xa5\x15\xab\x96F\xac\x96|\xfa\xbc\x9c\xcb\x99T\x96\x95\x98i0\x93\x07:\xd3\
b\xbbc~\x02\xfc\x0f\'\xc4\x97\xb6\x97\xab\xbe\x05\x00\x00\x00\x00IEND\xaeB`\
\x82`8\xef\xcc'
