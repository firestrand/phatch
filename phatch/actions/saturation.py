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

#---PIL


def init():
    global Image, ImageChops, imtools
    from PIL import Image
    from PIL import ImageChops
    from phatch.lib import imtools


def saturation(image, amount=50):
    """Adjust brightness from black to white
    - amount: -1(black) 0 (unchanged) 1(white)
    - repeat: how many times it should be repeated"""
    if amount == 0:
        return image
    amount /= 100.0
    grey = image.convert("L").convert(image.mode)
    if amount < 0:
        #grayscale
        im = imtools.blend(image, grey, -amount)
    else:
        #overcolored = Image - (alpha * Grey) / (1 - alpha)
        alpha = 0.7
        alpha_g = grey.point(lambda x: x * alpha)
        i_minus_alpha_g = ImageChops.subtract(image, alpha_g)
        overcolored = i_minus_alpha_g.point(lambda x: x / (1 - alpha))
        im = imtools.blend(image, overcolored, amount)
    #fix image transparency mask
    if image.mode == 'RGBA':
        im.putalpha(imtools.get_alpha(image))
    return im

#---Phatch


class Action(models.Action):
    label = _t('Saturation')
    author = 'Stani'
    email = 'spe.stani.be@gmail.com'
    init = staticmethod(init)
    pil = staticmethod(saturation)
    version = '0.1'
    tags = [_t('color')]
    __doc__ = _t('Adjust saturation from grayscale to high')

    def interface(self, fields):
        fields[_t('Amount')] = self.SliderField(-100, -100, 100)

    icon = \
b'x\xda\x01\xe1\r\x1e\xf2\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x000\x00\
\x00\x000\x08\x06\x00\x00\x00W\x02\xf9\x87\x00\x00\x00\x04sBIT\x08\x08\x08\
\x08|\x08d\x88\x00\x00\r\x98IDATh\x81\xd5\x9a{\x8c\\\xe5y\x87\x9f\xf7;sffgvv\
vgo\xde\xab\xd7kc\x1b\x93\xd8\x0e\xf7\x04DB\x1a\x14)-Upj\nU\xd2H\xeee\x0b\
\x8d\x95Vm)\x97V\xeaE!\xff\x844\xad\xb8\xa5\x81Hn\x0b\x94*RJT\xaa"\x17c\x1c\
\x12\x88MS0Ax\x9d\x18\xaf\xbd\x1b\xeceo\x9e\xf1\xce\xcc9g\xce\xf9\xde\xfeq\
\xce.k\x83\tko+\xf5\x93\x8eV;\xbbs\xce\xefy/\xdf\xfb\x9bsFT\x95\xff\xcf+\xb5\
\xd2\'\xbc\xed\xb6\xdb\xbe\x90\xcf\xe7\x8f\xae^\xbd\xfa\xc0\xce\x9d;\xfd\x95\
>\xff\xd9KV:\x03\xc3\xc3\xc3\xff\xb1c\xc7\x8eO_w\xddu\xcc\xce\xce6\xe6\xe6\
\xe6\xca\xf3\xf3\xf3\'\xeb\xf5\xfa\x9ba\x18\xbe\x9eJ\xa5\xf6\x0f\x0e\x0e\xee\
\xbf\xe5\x96[N\x00\x17|\xf1\x15\x07hnn\xfe\x83F\xa3\xf17\xd7\\s\rw\xddu\x17\
\xcd\xcd\xcdDQD\xa3\xd1X<\x82 \xa0Z\xad\xdar\xb9\\\x9d\x9f\x9f\x9f\xda\xb0a\
\xc3\xc9F\xa3q\xdd\xf6\xed\xdb\xa3\xe5^o\xc5K\xa8Z\xad>\xdc\xd2\xd22\xbce\
\xcb\x96/\x95J%QUD\x04U\xc5ZK\x14E\x88\x08\xae\xeb\x9aB\xa1P\xc8\xe7\xf3\x85\
\xe1\xe1\xe1\xae\xcd\x9b7/[\xfc\x8a\x01\x88\x88\x00\xbcp\xfb\xed_|\xe1\xa1\
\x87\xeei\xb9\xfc\xf25N.\'\xd6Z\xc20DU\x17\x85\'\xff\xba\xb86n\xdc\xc8\xd3O?\
\xfd\xda\xe6\xcd\x9b\xcf\xeb\xda\x17\x04\x90\x08\x97}w\xdc\xf1\x0f\xfe\x87>t\
\xb3\xac]\xebvww#"|\x10\xf1\x00\xcd\xcd\xcd<\xfb\xec\xb3\xbb\xef\xbe\xfbn\
\xd1\xf3\xa8\xe7\xf3\x06\x10\x11\xf9\xfe\xc8\xc8H\xf5#\x1f\xf9z\xa5\xbf\xbf\
\xa9T*\xd1\xdf\xdf\x8f1\x06U}\x97\xf8l6K\xa9T\xe2\xe1\x87\x1f\xe6\xd2K/%\x9d\
N388\xc8\xee\xdd\xbbuff\xe6I\xc0\x15\x91PU\xed\xff:\x80\x88\x98\xe7w\xee|p\
\xe6\xe3\x1f\x1f\x11\xd7\xa5T,244\x84\xe38\x88\x08Q\x14\x9d!\xbeT*q\xe8\xd0!\
\xee\xb9\xe7\x1e\xc20\xe4\xc0\x81\x03\\\x7f\xfd\xf5l\xdd\xba\x95\xa7\x9ezj\
\xff+\xaf\xbcb\x81f\xe0\xb4\x88\xe8r2\xb1l\x00\x111{n\xbf\xfd\x9f\xe6\xae\
\xba\xeaVU\xa5\xb5Xd\xed\xda\xb5d2\x19R\xa9\x14\xaaJ\x10\x04DQ\x84\xe38455q\
\xef\xbd\xf7\xb2o\xdf>\\\xd7%\x93\xc9\x10\x86!{\xf7\xeeebb\x82\xe3\xc7\x8f\
\x8f\x02\xc3\x80\x07\xd4\x81p9z\x96\x05 "\xce\xde\x91\x91\xefV6o\xbeQ\x1a\r\
\xb2\xcd\xcd\xac[\xb7\x8el6K&\x93\xc1\x18C\x18\x86\x88\x08\xc6\x18\x00n\xbe\
\xf9f*\x95\n\xaa\xca\xdbo\xbfM\x14Ed2\x19z{{9vl\x8c\xb9\xd9\x939\xa0\x1dH\
\x03\x92\x1c+\x9b\x81\xa4Y\xcds;v\xec\xae\x0c\x0f_\xaf~<`\xd7\xac_O:\x9d\xc6\
u]\xd2\xe94\xd6Z\xac\xb5\x88\x08A\x10\xb0}\xfbv\xca\xe5\xf2\xe2\xe18\x0e\x8e\
c\xf0\x03\x9f\xea\xcf\xaatwwq\xd9G\xaf\xdeVI\xcfT\x0f|\xef\xe0\x0f\x13\xe1\
\xcbj\xe4\x0f\x9a\x01\xf3\xfc\xad\xb7~\xf7t_\xdf\xf5\xe2\xfb(\xd0\xb5~=\xcd\
\xc5\xe2\x19u\x1f\x86!\xd6Z\xaa\xd5*\xdb\xb6mc~~\x9e\xe9\xe9ij\xb5\x1a\x99l\
\x86\\S\x8el6\xbb8\x13\x9a\xb29\xba\xdaV\x99On\xf9\xd4\x17\xb7|\xe6\xca\x96G\
~\xef\x91\xdfX\x8e\xf8\x0f\x04 "\xe6\x99O|\xe2S\xd5\x8e\x8e_\x96z\x1dU%\xdb\
\xd6F\xf7\xfa\xf5\x00\x8b\xcd\xba\x00\x10\x86!7\xddt\x13\xd5j\x95\xa9\xa9)<\
\xdf\xa3P(\xd0\xde\xdeNGG\x07\x85B\x01k-A\x10P(\x14\xe8\xed\xed\xa5\xa3\xad\
\x83M]\x9bn\x1a\xfa\xd75\x07\x9fx\xfc\xf1KE\xa4\xf6Aw\xa3\xf7\x05HJ\xc7u;:\
\xfe\xde\x06\x81\xd1d\x1f\xef\xda\xba\x15\x92\xe9\xba\xb0\xe3Xk\xc9d2\xdcy\
\xe7\x9d\xd4\xebu&\'\'\t\x82\x80bK\x91\xee\xeen\x06\x06\x06\xe8\xef\xef\xa7X\
,\x12E\x11\xbe\xef\x93\xcf\xe7Y\xbdz5\xfd\x83\x83\xb4\xb6\xb6\xd2\xe7\x0e\\\
\xb4\xf5\xb6\x8fV\xfe\xf9\xd6\x9f\xdc""\xdf\x89\xe3\xf3\xfe;\xd29\x01\x12\
\xf1\xce\x9ek\xaf\xfdJ\xe8\xba\x83\xe2y\x88*\x99\x8e\x0e2\xed\xedg\x0c*\x11!\
\x93\xc9\xb0g\xcf\x1e^z\xe9%fgg\t\x82\x80\xd6\xd6Vz{{\x19\x1a\x1abhh\x88\xee\
\xeen\n\x85\x02\xb9|\x0e\xe3\xa4H\x19CKK\x0b-\x85\x02\xe9T\n\xc7\x18z\x8b\
\xad\xf2\xdb\x85k\x9e\x18\xfc\xe1\xfe\x81{?v\xe57D\xc4\xbe\x1f\xc49\xcd\x9c\
\x88\x98\x07\xd6\xad\x1b\xbex\xe3\xc6\x83\x91\xeb6i&\x83M\xa7i\xb9\xf1F\n\
\x1b7\xe2\xba.\xa9T\n\x11\xc1q\x1c\xac\xb5l\xdb\xb6\x8dj\xb5\xca\xc4\xcf\'h)\
\xb6\xd0\xd7\xd7\xc7\xba\xe1u\xacY\xb3\x86\x9e\x9e\x1eV\xadZE\xa9\xb3\x93T\
\x92\xbd\xc4\x13\xe1\xba.\xc6\x98\xc5~\x02\x08Uy.4O\xff\xe9U\x1f\xf9,\x10\
\x9d\x0b\xe2=3\x90D?\xf5\xe1\xd6\xd6Gj\x1b649\x8e\x83\x1c>\x8c\x93\xcf\xe3\
\xae\x1e\\\x1cP\x0b;N[[\x1b;w\xeeDD81y\x82|K\x9e\xce\x9e.\x06\x86\x07\xe8[\
\xddGWW\x17=\xfd}\x14\xdb;qS\x0eN"\xfel{\xd1\xf0}\x82FD\x18\xa1X\xe5\n\xf8\
\xcc\xc3\xbb\x9e\x99{\xea?\xc7\xd7\x8b\xc8\xe4{\xf5\xc5\xb9J\xc8<\xb9z\xf5e\
\x8e\xc8u\xe9#G\xf0GF(\xaf]KK\x10\x10YE\x96\x94N*\x95bbb\x82\xf1\xf1qNN\x9e\
\xc4I;\x94\xbaK\xf4\xae\xe9\xa1g\xa8\x87RO\x89\xce\xbe>R\xed]\x04\x8eATHK|\
\xe1\x05\xf1\xd5\xf9*~- %!b\x0c\xc6\x181" \xc2\x86U4\x7f\xfe\xd3\x83c=\xc5\
\x7f\xff\xac\x88<\xc3Y}a\xce\x11}\xb7]\xe4\xf3\xc6\xf7%=1\x01ss\xb4\x0f\x0f\
\x93\xfb\xf0\x87\t\xc3p\xd1\xd3\xfb\xbeOkk+\x0f>\xf8 a\x14R\xa9U(\xb4\x17\
\xe8\x18\xec\xa0kM\x17\xad=%:{\xd7a;{\xf0\x8c\xc1G\xf0\x01\x1fh(\xd4\xabU\
\xa6OL\xe3U\xca\x10y\x8bsd\xe1X\xd0\xd9\xdb\xa9\xe9_\xbb\xc1y\xfa\x0f\xef\
\xda\xfd5\xc0\xc8\x92\xb4\xbd\x0b y-\x93\xb3\xf6\x97\xc4\xf3\xc0\xf71\xaf\
\xbf\xbe\xb8E.\x15\x1fE\x11\xb3\xb3\xb3\x1c9r\x84\xa9\xe9)2-Y\x8a\xbdEJ\x03%\
Z\xba\xdb\xe8\xec\xb9\x84\xa0\xb3\x97\xba\xe3\x10\x88\xc1W\xc5S\xc5\x8b\x94\
\xe9\xb7OQ\x99\x9eF#\x8f(\x8a\xce\x14\x7f\xc6\xef\xca|M\xf5\xd4i\t\xaf\xde\
\xac;\xff\xf2\xab{\xf6^\xc2%\xee\x02\xc4{\x95\x90\x19I\xa7\xfb2\x8d\xc6EV\
\x04\x0b\x98W_%\xb8\xfaj\x00\xa2(\xc2\x18\xb3\xd8\x80\xbbv\xedBD\x98\xab\xcd\
Q\xec+R\xec/R\xe8-\xd0\xbe\xeaR\xaa\x9d\x03d\x1c\x07\x9b\xb8\x03+\x82F\x8a\
\xf7\xd6,&\xf0P\x07\x1c\rq\x8cA\x1dg1z\r5\x1c\x1ek\x84?<\xf0\xc6\xd43O\xdf\
\x7f\xe0t\xe5\xadQ\xe00p(Kv\xbc@!M\xec\x99\xf4\x0c\x80\x85\xf2\xf9\x15c>\xe7\
z\x9ei\xa8\x82*\x8c\x8e\x12x\xa7\xd1L\xf3\xa2x\x00\xcf\xf3(\x16\x8b\xcc\x95\
\xe7H\x15R4\xf7\x15\xc8\xf7\xe6)tl\xd2\xda\xaa\xb5\x92M\xb9\x10\x17m\xec\x11\
"%\x1a\x9bA\xfd\x00\xd71D\xaa\xa4-h\xcabTQU\x0e\xfe\xd46\x1e}\xf4\xfe7\x8e\
\x1d\xfd\xc1$P\x05N%\xf2r@\xab\x877\xe3\xe1U\x00GD\xf4\xec\x0c\x08\xe0v6\x1a\
7\x88\x08F\x15\xac\xc5\xb7\x11\xf5\xd3\xaf\xa2r\xc5\xa2I[\x10v\xf1\xc5\x173\
\xd29\xc2c\xcf<F\xbd\xdb#\xdb\xdd\x8eYu\xa9xn:\x19v667\r\x8b\x1c\x9e\xc6\x0f\
\xc01\x0e\xaa\x96\x94:\xa8\x13aU\x99\xaf\xa1\xdf~b\xf7\xd8\x8f^x\xe4p"z\x16\
\x98N~\x9e\x02\xe6\x92\xa3\xc1\x12\xbft6\x80\xd3\t\xb9B\x14].A@\x04\x18U\xec\
\xea\x88z\xf5%Lv\xcb"\x80&\x11\xb3\xd6\xd2\xd5\xd9\xc5}w\xde\xc7W\xfe\xe5^r\
\xa5\xeb\xf4tKI\x9a\x8c\x01\x14M\xca&\xfd\xda\x8cV\xea\x8e\xb8\xae\xe2\x9a8\
\xb1V-V\r\xd3\xa7\x1c\xfb\xf5\xbf\xfd\xda\x8f\xdf\x1a\xdf?\x06\x9c\x00&\x80\
\xb7\x80\xc9D|\x8d\xd8n\xfb\xc4\x96\xdb\x07\xec\x19\x00\x0b\x93w=\x94\x04\
\x9a$\x8aH\x05\x01\x0e\x10m\x8el\xc3\xffo\xe3yu\x1c\'\xb5\x08 "l\xd8\xb0\x81\
\xb9\xb99\xee\xbf\xff~\x1c2x\xd9^q\x9d\x14"\x89\xb5T%3Z\xd6Ssiq\x1d\x8dE;\
\x0b\x00\xf0\xd6\x14\xd1\x83\x0f\xdc\xf3\xe2\xec\xd4\xe1#\xc0Q\xe0\x08p<\x11\
_N\x84\x87@\x94D>J\xc4[U=\xa3\x84$\x01*D\xc4\xcdd\xa2\x08\xd7\xf7\xc9^\xe5h\
\xa6\xae\xbc=9F\xa9}\x00\x80\xc1\xc1AJ\xa5\x12O>\xf9$\xc7\xc6\x8f1\xd92\x8d\
\\\xb3C\xd3]\xab$\x9b\xf4\x88U\xc5\x9c\n\xa9\x1fS\xb1\xd6\x10\xa5\x15WAm\xac\
db2l<\xf2\xcd/\xef\xabV\xde:\x02\x8c\x02\x87\x801`\x06\x98\x07\x82D\xec\x196\
{\xe9\x1c8\x1b\xc0IA\xc1.y\xc1\xac\xb2\xb4\r\xa8S\x1e\x17~\xf6\xf3C\xf4\x0fl\
`\xd3\xa6M\xbc\xf8\xe2\x8b\xec\xda\xb5\x8b\xc9\xb9I\xde\xb0o\x90\x19\xbcZ\
\x8b\xb9\x92\xe4\xad]\xbc\x9a\x15C\xf3\xfe\xb2Vj\x19I\xa7,\x8a\xc6\xd1O)\xc7\
Ox\xfe\xe3\x8f\xfe\xee^\xdf/\xbf\t\xbc\x01\xbc\x9ed`fI\xd4\x97m\xe6\x8c\x0b\
\xe9\x05d\x03\xd0\x0c)G\xc9\xe7\x94\x96\xdc\t\x8a\xc5"\x0f<\xf0\x00\xe5r\x99\
\x97_y\x99\xe3\xe5\xe3\xa4\xd7dh\x99-\xaa)\x9f\x12\xc9\xe7\x91\x94\x8b:B\xf6\
\'U-O5\x89#\xa0V\x88\xac\xc5\xa6\x94\xd3\xf3\x1a\xfd\xe3#\xbf\xf3\\\x18T\x8e\
$\xc2\x17\xc4\xcf&\xe2\xdf\xd7\xc0\xbd\x1f\x00\'\xa1Q\x83\xd3MPP@\x1d\x10\
\x81L\x1a\xd2\xf2\x02\xdfz\xe8e\x0eM\x0e26:F\xe0\x07HN\x08\xcbJ}>4ff\n\xa7\
\xb5\r\xc96!\x9e\xa1\xb1?$\xb0.\x99\x94\xc5bI[A\xd5\xf0\xfd\xe7\xbf\xf7F"\
\xfe\xb5D\xfcX"\xde_\x8exx\xf7$\xd6\x9f@\xe5\xb7\xe0\xef\xc6`\xd6\x02\x81\
\xa0J\x0cP,\x80\x97\xf38<{\x98@\x83\x18\xdf\x01+\x05\rU\t\xc2\x08\xcf*u\x14\
\xdd[\xb1\xe5J\x93x\xbe\x83\x17\x18|_\xf0\x03\xc3\xd8\xf1\xa9\xca\xe8\xab\
\xdfz\x89\xf7(\x1bU=\xa7\xeb\xfc \x00J\xdc0\xde!\x98\xf8u\xf8\xde\xb30\xe1;X\
%n\x8e|\x1e\xeaY\xb1\xb4H|\x13\xa4\x08t\x81\xf4\xae\xd7hp\x88\xb0\xbd\x93 \
\x97\xc3s\\\xfcQC\xdd7x\x81P\xf7\x05?p\xa8yj\x7f\xf4\xdc\xbd\xfb\x807\x89\
\x9b\xf6\x18\xf1\xde\xee/\xf7~\xd0\xc2ZZBJ<$N\x01\xe3\r\xe8\xb8\x03\x9c\x91\
\x06\x97\xfff\xc0\x06c0\xf9\x1c\xa4[P:\x88\xeb*\r\xacr\xd1M7\x88\xae\xb9\x88\
\xa0\xbb\x07\x93/\x90\x9ar\xa8\x95\xf3&\x95\x02\xc5\xc4\xbb\x8eZ\xc6\x8f\xee\
;zz\xee\xf5Q\xde\xd9*/H\xfc\xd9\x00$\x00s\xc9\x05\x1c\xa0\xf1\xcdC\x04?\xfes\
f\xff\xe2\x8f\xb9<\xdbD&]D\x19\x00\xda\x80f\xd0\xae\xf5\xca\xc5\x9b\xc5\xb6\
\xb5#\xcd\xcdxi\x97\xd4\x8b\xb3Q\xd5kv2\xe9x\xd0\xd9\xb4\xa1Z\x9b\xa9\xfd\
\xf4\xe5\xbf~\x9e8\xfac\xc4e\xb38\x90.\x18@UUD"\xe2\xa9w\x82x`\xd4\x81\xda\
\x81\x1fS\xff\xe2\x97\xa8|\xf5\x1e>\xe6\xb4\x90\xc3\x95\xf8\xafM\x80\xf6\x07\
\xda\xd1\x9d\x892\x19\xd488\x16\xfc\xfd\xa8\xe3\x9bE\xf1\x8aev|\xdf\x9b`\xc7\
\x13\x80\x13\xc4>\'<\x9f\xfb\xa1\xef\t\xb0\x04"LN~\x828B5\xa0:=Km\xe4O\x98\
\xbf\xe46>\xc6F\xfa\x00p\x81J\xce\x92\xc9\x801q(\xcbJ0\xdd\x9a\x12W\xb1jb/\
\xa4\xe8\xf4\xf8w\xfe\x8b\xb8a\'\x88\'l\xe3B\xc5\xbf\x0b`\t\xc4B\xf4\xa7\x88\
\xa7a\x1d\xa8ZK\xfd\xb5\x07\xd4\xe7\x93la\xbbl"\x8d\x13\x9f"q\xad\xd6b\x7fP\
\xb7\x8dF\xdeX+X\x8d\xf7\x7f\xdf\x9b,7jG\x8f$\xe2\x17\x06\xd5\x05\x95\xce9\
\x01\x16 \x80HD|\xdeq\x80\x1eqf\xe6\xd9\xa35\x8e\xe9,\xbfo\xaeDS\x16M\xfc\
\x81\x11\x18\x9d\x0e\xadmJ\xab\n\xd6\nj\rZ=8\x06\x9c\x04\xde&\xb6\x08\xcb\
\xde.\x97\x05\xb0\x04\xc4\x8aH\x00T\x88G\xbbG\\R5\x8e\xe0\xf1g\xb6\xccmr96\
\xca\'\xc6\x03\xc2P\xc1\xa2*D\x91P\x0f\x04\x99\xf9\xb7\x83\xc4\xd9,\xf3\x8e\
\xbfY\x91\xf5\x0b\xef\xcc\x9d\xd5\x17!KJ\x8a\x1a5\xee{\xacF\xb5\xfb\n~\xf5s\
\xc3\xa0B\x10&\xfa\xe2\xfb\xb46\x98\xa9R}\xe9\xa7\xc4\x93\xb6\xc6\nF\xff\x03\
\x01,\x81\x88\x8830C\\R\xf5\x04\xaa\xca\xc3_\xf7\x18}}\x96/\xfd\xd1V\xc2P\
\xd1\xc4\xcf\x8a@\xf0\xe6\xc9\xe4=eV`\xdb</\x80\x05\x08\xce\xdd\x17U\x9e{\
\xc6\xe3\xcd\xc3e:\xee\xb8\x0cl6~\x93\x00~5\x018\xcdY\x9f\xa6\xfeO\x01\x16V\
\xd2\x17\x8dD\xd0\xd2\xbe\xa8r\xech\x8d\xe3_>M\xc7_]M\xee\xda\x1e0\xa0\xb6N\
\x1c\xfd\x15/\x9f\xf3\x02\x80_\xd0\x17\x1a\xd4\x98\xba\xb3F\xeb\x8e-\x14\xbe\
p1\x1a\xd5\x89\xc57X\xe1\xf2\x81\x0bx\xc8\x97@X\xe2\x0c\xcc\xf2N_\xc4\xd98\
\xf5\xed\n\xc1\xcfF\xc9n]\xf8du^\xcf\x81\x7f\xd1Z\x91\'\xf5"b\x88\x83\x91\
\x03:\x81!\xe2\xe7^\x05\xe2\xfd\xff \xb1\xff\x99\xbf\x10\xe3\xf6^kE\x1et/\
\xe9\x8by\xe2H\xfb\xc4\xae\xb6\x8d8#\x0bsd\xc5\xbf\x1a\xb3\xa2\xdf\x95Xx\x96\
Fl\xb4\xf3\xc4\x19\xb1\xc4`+b\xde\xce^\xff\x03PiL\xa0\xa2\xb2~A\x00\x00\x00\
\x00IEND\xaeB`\x82\xber\xe4\\'
