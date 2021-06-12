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
# Phatch recommends SPE (http://pythonide.stani.be)
# for editing python files.

# Embedded icon is taken from www.openclipart.org (public domain)

# Follows PEP8

from phatch.core import models
from phatch.lib.reverse_translation import _t
from phatch.lib.openImage import open as open_image
from phatch.lib.imtools import has_transparency, paste

#---Pil


def init():
    global Image, ImageMath, imtools
    from PIL import Image
    from PIL import ImageMath
    from phatch.lib import imtools


def put_highlight(image, highlight, resample_highlight, opacity, cache=None):
    if cache is None:
        cache = {}
    resample_highlight = getattr(Image, resample_highlight)
    id = 'highlight_%s_w%d_h%d_o%d'\
        % (highlight, image.size[0], image.size[1], opacity)
    try:
        highlight = cache[id]
    except KeyError:
        highlight = open_image(highlight)\
            .convert('RGBA').resize(image.size, resample_highlight)
        if opacity < 100:
            #apply opacity
            highlight_alpha = imtools.get_alpha(highlight)
            opacity = (255 * opacity) / 100
            highlight.putalpha(ImageMath.eval("convert((a * o) / 255, 'L')",
                a=highlight_alpha, o=opacity))
        #store in cache
        cache[id] = highlight
    if not has_transparency(image):
        image = image.convert('RGBA')
    else:
        if has_transparency(image):
            image = image.convert('RGBA')
        alpha = imtools.get_alpha(image)
        highlight = highlight.copy()
        highlight_alpha = imtools.get_alpha(highlight)
        highlight.putalpha(ImageMath.eval("convert(min(a, b), 'L')",
            a=alpha, b=highlight_alpha))

    overlay = highlight.convert('RGB')
    paste(image, overlay, mask=highlight)
    return image

#---Phatch


class Action(models.Action):
    """Apply a transparency highlight"""

    label = _t('Highlight')
    author = 'Nadia Alramli'
    cache = True
    email = 'mail@nadiana.com'
    init = staticmethod(init)
    pil = staticmethod(put_highlight)
    version = '0.1'
    tags = [_t('filter')]
    __doc__ = _t('Apply a transparency highlight')

    def interface(self, fields):
        fields[_t('Highlight')] = self.HighlightFileField('Sphere Top')
        fields[_t('Resample Highlight')] = self.ImageResampleField('antialias')
        fields[_t('Opacity')] = self.SliderField(100, 0, 100)

    icon = \
b'x\xda\x01\xd9\r&\xf2\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x000\x00\
\x00\x000\x08\x06\x00\x00\x00W\x02\xf9\x87\x00\x00\x00\x04sBIT\x08\x08\x08\
\x08|\x08d\x88\x00\x00\r\x90IDATh\x81\xed\x99{pT\xd7}\xc7?\xe7\xde\xbb\xbbZi\
\xd1\x0b\xb1zXO\x04B\xc2\x0f\x10\x86\xe2\x9a\xd8\x10364u\xd3\xc4.\xb6k;\xc43\
\x8e\'\xf6$\x99\xc6\xcd\x1f\x9dt\xa6\xd0\xc6\x9d4\xad;\xf58\tmg\xda\xf1\xe0&\
S\xd7\xd14\xf5\x84\x16\x19\x8a\xed\x12\xdb\xd5\x0bI d@B\x12\xe8I\x84\xde\xbb\
\xda\xd5\xdd\xbd\xf7\xdc\xd3?v\xafX-\x02C\x8c\x93\xc9L\xcf\xcc\x99\xbbsu\xef\
9\x9f\xef\xef\xfb\xfb\x9d{\xef\x91PJ\xf1\x9b\xdc\xb4_7\xc0\'m\xff/\xe0\xd7\
\xdd~\xa5\x02ZZZ\xb2[ZZ\x1e\xbd\x95c\xfe\xca\x04\x9c8q\xe2\t\xc7q\xce\xd9\
\xb6\xfd\xa5[9\xee\xa7.\xe0\xe4\xc9\x93k\xdb\xdb\xdb\x8fJ)\xdfp\x1c\xa7XJ\t@\
gg\xe7\xaa[1\xbf\xf8\xb4\x96\xd1\x8b\x17/f\x84\xc3\xe1o[\x96\xf5\'\xb6m\xfb\
\xe2\xf18\x03\x03\x03dee\x1d\xae\xa8\xa8\xf8\x99eY\x7f\x15\x8b\xc5Jv\xec\xd8\
a~\x92y\x8c[\x05\x9c\xda\xba\xbb\xbb\x1f\x92R\x1e\x90R\xae\xb1m\x9b\x91\x91\
\x11:::\x10B\xb0{\xf7\xee{m\xdb\xfe\x9c\xeb\xc4\'m\xb7T@OOO\x89\x94\xf2\x15\
\xa5\xd4c\x8e\xe3099I{{;\x13\x13\x13\xd4\xd7\xd7S[[\x8b\x942\xd74M\xc6\xc6\
\xc6\xf0x<\xe2\x93\xceyKR\xa8\xa1\xa1A\xaf\xab\xab\xfb\xba\x10\xe2%\xa5\xd4\
\x8a\x85\x85\x05:::8{\xf6,\x15\x15\x15\xdcs\xcf=x\xbd^\xe2\xf18}}}\x9c:u\x8a\
\xcc\xccL\xee\xbc\xf3\xceL\xd34WI)7h\x9aV\xb8w\xef\xde\x7f\xbe\xd9\xb9?\xb1\
\x03g\xce\x9c\xd9\xba~\xfd\xfa\x7f\x00\xea\x1d\xc7app\x90\xe6\xe6f\x00\x1e\
\xdc\xbd\x93\xd2\xe2rl\xdbfxx\x98\xf6\xf6v\xa6\xa7\xa7\xc9\xca\xca"\x18\x0c\
\x12\x8f\xc7\x07\x85\x10\xabt]G)\xf5#\xe0\xd3\x17 \x84\x10\x00MMMy\x81@\xe0\
\xbbB\x88\xe7\x00maa\x81\xa6\xa6&\x86\x86\x86\xb8\xe3\x8e\xdb\xd9\xb0q#\x9a\
\xd0\x98\x9d\x9d\xa5\xb9\xb9\x99\x91\x91\x11\xf2\xf3\xf3\xd9\xb2e\x0b\x99\
\x99\x99(\xa5PJ\xadRJ\xe18\x0eJ\xa9\xf7n\x96\xe5\x86\x04\xb8\xc0\xa9\xad\xab\
\xab\xebK\x9a\xa6\xbd\x0c\x04\x1d\xc7\xe1\xfc\xf9\xf3\x9c8q\x82\xfc\xfc|>\
\xff\xc5\x87\xc9\xcf)\xc0\xb6m\xba\xbb\xbb\xe9\xec\xec\xc4\xeb\xf5\xb2a\xd3\
\x1d\xac\xcc\r\xba\xb0K\xba\x10\x02\xc7q\xde\xbd\x1e\xc7\xf7_y\xa5R7\x8c\xd1\
\xaf}\xe3\x1b\xd6\x12\xbek\xd5\xc02\xe0\xa2\xad\xad\xad\xce\xef\xf7\x1f\x00\
\xb6\x03LNN\xd2\xd2\xd2\xc2\xfc\xfc<\x9b6\xd7\xb3\xb6\xba\x06\x80\x89\x89\t>\
\xfc\xf0CB\xa1\x10\xab\xd7Tq[q)\xc0\xb2\xf0\xc9s\x17\xf7\xec\xd9S\x95\xce\
\xf0\x83W_-\x90R\x1eq\xa4\xdc\xa0\x94\xd2\x85\x10Jh\xda\x88\xa6i\xbf\xf7G/\
\xbexjY\x01i\xe0\x02\xe0\xb5\xd7^\xcb\xba\xfb\xee\xbb\xffT\xd7\xf5o\x01\x9ex\
<Ngg\'\xbd\xbd\xbd\xd4\xd4\xacec\xfd\x06|^?\x96e\xd1\xd9\xd9\xc9\xb9s\xe7\
\xa8\xa8(\xa7\xb2\xaa\n]\xd3\xd3aY\xb0\x15\x17\xe6\x15\xebV,\x9e;\xf4\xc8#\
\x8f|>\x95\xe3\xef\x7f\xf8\xc3{b\xa6y\xdcq\x1c\xef2\xc1U\xc5\xb7\xdd\xf6\x07\
\x7f\xf8\xe4\x93?5RN^\x05\x0e\x88\x8e\x8e\x8e\xdf\xf5x<\xdf\x17BT(\xa5\xb8x\
\xf1"mmmdff\xb2\xebw\x1e$XP\x84R\x8a\xc1\xc1A\xda\xda\xda\xf0\xfb\xfd|\xe6\
\xbemde\x06\xae\x8at\xc4\x86\x8e)\xc9G3\x0e\xebs54M \x84@)\xd5\x9b\n\xf87\
\xdf\xfb\xde\x8b\x99\x99\x99/;\x8e\xa3\xa7\xc3\x03(\xa5\xc4|8\xfc\x06\xe03\
\xae\x01/\x8e\x1d;V\x1e\x0c\x06_\xd14\xed\xf7\x01\xe6\xe6\xe6hmmM\xac\xe9\
\x9b6P\xbb\xae\x0e!4\xc2\xe10\xad\xad\xadLMMq\xfb\x1d\xeb).*\xb9*M\xe6L\x9b\
\xa6q\x9b\xb33\x12\xa9\x14\x1e]\xa3&\xd7@\xd7\x17\xaf9/\x84\x10\x7f\xf9\x9d\
\xef\xf8\xf3\xf2\xf2\x0eh\xba\xfe\x8c\x15\x8f/\xc7\x0e@FF\x06\xa1\xb99\xef\
\x8f^\x7f\xbdF\xa4F\xdb=\x1e:t\xa8\xb0\xaa\xaa\xaa\x17\xc8r\x8b\xb1\xbb\xbb\
\x9b\x8a\x8a\n6m\xae\'\xcb\x1f@J\xc9G\x1f}Dww7UUU\xd4\xd6\xd5b\xe8\xc6\x92<w\
\x94\xa2\xed\xd2\x02\x1f\x8c\x99\xc4\x1d\x85\xa1i\xf8<:~\x8f\xc6\x93\x95\x1a\
$\xaf\x8b\xc5b;{\xce\x9e\x1d\xf2z\xbd\r\xd3\xd3\xd3\x1b\xcb+*\x98\x9b\x99\
\xb9\xa6\x80\x9au\xeb\xe8\xed\xe9\xa1\xa8\xb8\xf8\xdbn\n\x89\xd4\xae\x94\xca\
\x00\xb2FGGimmE)\xc5\x8e\x9d\xf7SZ\\\x0e\xc0\xa5K\x97hii\xc1\xe3\xf1\xf0\xd9\
\x9d;\xc8\xcb\xc9_L\x93dJ0\x12\x8asx \xccx\xd4F\xd7\x04\x99^\x03\xaf\xa1\xe3\
3tV\xf9u\x0c=q\xfd\xc4\xc4\x04mmm_.\x0c\x06\xf7dgg\xfbOwws\xe7]w\x11\x9a\x9d\
e\xb9\x05\xc6\xe3\xf1\xe0\xf5&\xca\xc24\xcd\xb7\x8ctx@\x0b\x87\xc38\x8e\xc3;\
\xef\xbcC]]\x1d\x9b\xee\xde\x84\xae\xe9\x98\xa6I[[\x1b\xa3\xa3\xa3\xd4\xd7o\
\xa4\xbaz\x8d\x9b\x93\x8b\xcb\xe1\x82%\xf9\xef\x81\x10\xed\xe3\x0b\x08\xc0\
\x9f\x02\x9e8j\xac\xca\xd2\x98\x99\xb9Lcc#>\x9f\x8f\xca\x8a\x8a\xbd\xf7o\xdf\
\x8e\x10\x82\xb3==\xcc\xce\xce\xa2\xe9:\xd2\xb6\xc9\xce\xce&\x1a\x8db\xdb6\
\xab\x82A\xd6\xac]\xcb\x99\xeen\xb2\xb2\xb2\xe4\xb3\xcf=w.\xdd\x01\r\xd0/_\
\xbe\xac%k\x83\xca\xcaJ4\xa1\xd1\xdb\xdbKgg\'eee|\xf1\x91/\x90\xe1\xf3_U\xa4\
\xa7\xc6#4\xf6\xcd\x12\xb5$\xbe\x14h\xaf\xa1\xe3\xf3\xe8\x8bB\x9c\xcb\xfd\
\x1c\xfc\xd9\x9b\xe4dgSW[\xcb\xbd\xdb\xb6QPP\xc0\x85\x81\x01V\xe6\xe734<\xcc\
\xee\x87\x1e\xe2tW\x17\xe1p\x98\xb2\xf2rrss1c1:\xdb\xdb\x89\xc7\xe3\xac\n\
\x06\xbf\x02\x89\x07\x99\x96\x84\xd7]\x01\x13\x13\x13\x8b\x02\xa4\x94\xf4\
\xf5\xf5\xd1\xdd\xdd\xcdC\x0f=Haa\xd1UEzy>\xce\xbf\x7f4\xce\xc0\xf4\x02^\x8f\
N \xc3\xbb$\xean\xe4\xbd\x86\x8e\xdf\x9c\xa5\xe5\xc8[x\x0c\x83`a!\xf3\xf3\
\xf3x<\x1e\xfa\xfb\xfa\xe8ho\'\xb0b\x05EEELNO\xb3c\xe7N\xbaN\x9dbdd\x84\xa1\
\xc1A\x84\x10\xe4\xe4\xe6\xaa`a\xe17\xf7<\xfe\xf8AW\x80\x1by-)\xc2\x98\x9e\
\x9e\x16\xae\x00\x17\xb2\xa8\xa8\x88\xd2\xd2\xb2%E\x1a\xb7%G\xfb\xa6x\xb7\
\x7f\nC\xd3\x92\xe0\xda\x95tI\x89\xba\xd7\xd0\xc9\xcb0\x18=\xd9\xcc\xe4\xe4$\
%%%\xf8|>\xa4\x94\x1c;v\x8ch$BEE\x05\xf7n\xdb\x86\xd7\xeb\xa5\xb7\xb7\x97\
\x0f>\xf8\x80\x82\x82\x02\xb6l\xdd\xea~K\xcc\x06\x02\x81-\xbbv\xed\xeask"U\
\x80\x0ex\x00\xcf\xa5K\x97\x96<<\\!\xba\xae/\xfe>;\x1e\xe6\x8d\x93#\x84c6~\
\xaf\x91\x16m=\xcd\x01\r\xd3\x98F\xf8\xe6\x19\x1b\x1a\xc44M\x04000\xc0\xb6m\
\xdb\x18\x1b\x1bc\xcb\xe6\xcdl\xac\xaf\xa7\xa7\xa7\x873g\xceP\\\\\xcc\xf6\
\xed\xdb\x89\xc5b\x8c\x8f\x8fSVZ\xfa\xe6g\x1fx\xe0\x89\xf4\xa26R\xe0\r\xc0\
\x0bd\x8c\x8d\x8d\x05\xdc\x0b\x1c\xc7Y,TM\xd3\x16\x05\xfc\xfc\xc2\x14\xa6\
\xad\x08\xf8\xae\xa4K\xc0\x1f\'\x18\x18g>^\x8e\xaey\x90F\x84\xa3\xe2\x9fhW\
\x8dD\xc3!\xbee\xfe1\xb6m\x13\x8b\xc5\x98\x9b\x9b\xc3\xe3\xf5\x12\x08\x04\
\xd8\xbd{7eee\xbc\xff\xfe\xfbtuu!\x84\xa0\xa6\xa6&1\x97\xe3X\xd2\xb6\x9f\xd9\
\xb9k\xd7\xbf^\xb5$\xa5\x080\x80\x0c \x0b\x08LMM\xe5\xb9\xd0\xae\x03\xa9n\
\x08!\x08dx\x08dx\xf0\x19:\xab\xf3\x07\xd8\\\xf6s\xaaW\x9e\xc2\xd0m\x1c<\x9c\
\x89h<\x7f\xa1\x9f\x0b\xb3\xf3\x10\x05\xa2PVSJtE\x84X,\xc6\xd8\xa5K<\xfc\xf0\
\xc3\xf4\xf7\xf7S__\x8fR\x8a\xe2\xe2b,\xcb\xa2\xb6\xb6\x96\x92\x92\x12\x86\
\x86\x86B\xb333w>\xf2\xe8\xa3C\xcb\xc1\xbb\x02<I\xf8\x15@\x1e\x90\x1f\x0e\
\x87\x8b\xa4\x94K\xd6v\xd7\t\xb7\xf9=\x1e\x02>/\x1bok\xe5\xc1\xb5\xff\x82\
\xae9h\x02\x10\x82Yu\x91|\x7f\x88W+\x05/|\x00\xa3\x13\t\x01\x91\xaa(>\x9f\
\x8f\xcc\xccL&\'\'1M\x93g\x9f}\x96C\x87\x0eQ^^NAA\x01\xb7\xdf~;\xa3\xa3\xa34\
77;\xfb\xf6\xed\xdb\x12\x8b\xc5\x86\xaf\xf7\xd1e\x00> \x1b(\x00\x82@A<\x1e_%\
\xa5\xc4q\x9c\xc5\xa2M\xff\x86\xf5{u\xb6U\xfd\x0f\xf7U6 4\x85\x86@\x08\x98\
\x92\xa3D\xed\x10((6\x14\xdf]/\xf8\xf2O\x80\x05h\xe9i\xe13\xb5\xdb\xa8\x0f\
\xd7\xd3\xd8\xd8\xc8\xc1\x83\x07\xe9\xef\xef\xe7\xa9\xa7\x9e\xa2\xba\xba\x9a\
\xfe\xfe~z{{ill\xa4\xa3\xa3\xe3\xcfb\xb1X?\xc97\x1du\r\x15\x06\x90\t\xe4\x02\
\x85@\x11P`\x9af\x8e\xeb\x80\xebB\xba\x03%9C\xfcVi\x03\x9a\x00!4\x94\x90\xfc\
\xc2\x1e$\xee,$*J\x01\x1a\xac/VT\xd5\n.\xf4@<\x06\x8f\xedy\x9c\xd7\xc7\x0f\
\xf2\xcc3\xcfp\xf8\xf0a\x8e\x1c9\xc2\xe1\xc3\x87\x91R"\xa5\xc4\xef\xf7\xb3u\
\xeb\xd6\x86H$\xf2\xf25\xc3\x9e&\xc0C"\xf7s\x81| \xcf\xb6\xed\x15\xb6m\xa3\
\x94\xc2\xb2,\\7\xae4\xc5]\xc5?F\xd7\xc0\x11\x929g\x92\xb0=\x9d\xa8\x19\x058\
I\x01\xc9\xfe\x85b\x0fy\xc5\xfb\xd9{\xd7\x93\x08\t/\xbc\xf0\x02333<\xfd\xf4\
\xd3455q\xfa\xf4iB\xa1\x10\xd5\xd5\xd5\x96\x94\xf2/\xf6\xed\xdb\xf7w7\x02\
\xef\np\xad\xd1H\xa4\x93_)\x95\xe9:\xe0\xc2\xa7\xa6P\x86\xf1\x1eY\xfay\xc2v\
\x94Ik\x04\xa9\xec%\xc0\x8b\xdd\x11\xe4zr\xf9\xf3{\x1f&l\xee]t4\x1a\x8d"\xa5\
\x9c\x0b\x85B\xc3\x9b6m\xd2jkkC\x96e5544\xfc\xe0\xc0\x81\x03\x93\xc9inh\xc7\
\xc2\x00\xe2\xc0B\xb2\xdb\x80\xe68\x8e\xcf\xb6m\x1c\xc7\xc1\xb6m\x80%\x0e\
\xf8=\xff\xc9\xa45\xc3ek\x0c\x1c\xb5,|\x86\xf0S\x99W\x81W\xf7b%\xc5\x0b!\x88\
D"fCC\xc3\xdb/\xbd\xf4\xd2\x9b\xf1x|\x04\x98!\xb1N\x99@\xecF#\x9f* \x06\x84\
\x81Y D\xa2\x90u)\xa5r\x1cG\xd8\xb6\x8d\x10bQ\x88\x10Q\x0c\xed<\xa6\x1d\x01y\
5\xbc\xaetJW\x94\x92\x93\x91\xb38\x89\x106\x8e\xe3\xa8\xe3\xc7\x8fw\xee\xdf\
\xbf\xff\xc7\x03\x03\x03\xe7\x81i \x02X\\I\xba\x9bnFr\x80H2\x12SI\x01A\xcb\
\xb2\x16\x1dHn{\x00\xe0\xd1N\x03\x0eB\t\x90\xa9\xf0\x82\x95\x19+\xb9-\xbb\
\xe4\xaaI\xe6\xe7\'\xa2_}\xfe\xab\xff\xd8\xd8\xd8\xd8\x9a\x9c\xc3\x8d\xb8\
\x9d\x84O\xab\x9a\xc5~C\x02\xec\xe4`s\xc0$0\x01\x04\xe3\xf1\xb8\xb2,K\x98\
\xa6\x89\xdf\xef_L!\xaf\xd1\r\x90\x10\xe0$\x8e~=\x93\xca\xbc\n\x0cm\xe9&\x87\
\x94\xb6\x13\x99\xbf472\xd4\xd5\xd5\xd8\xa8\xdeK\x06*\x96\x0c\x9aL\x81O\xed7\
\x0c\x0f\x89\xc2u\xb8\xe2\xc2\x140\x0eL\xc4\xe3q\xb5\xb0\xb0@$\x12AJy%\x85XH\
\xdc\xa8\x04+\x8cl\xd6\xad\\\xc7\x9a\x95\xd5i\xf0\x8a\xc8\xfc\xc4|h\xf6\xdc\
\xa8`fzu\x15\xc5\xef\xfe\x97\xf6@\x12\xdeN\xeb\xa9B\x96sA]\xeb\x19\x00\t\x07\
dR\x80I\xa2\x0e~\x01\xe4K)\x1d\xa5\x94\x88F\xa3NNN\x8eq\xe5\x9d(\xf1\x9eW\
\x14(\xbc*\xe2\x0013\x1c\x8bF\xc7\xa6u-\xb6\xe0\xf5bk\x1aJ\x08T]\x8d\xda\x04\
\xbc\x91\x84\xb6nP\xc8\xc76w\x19\x95$V#\xd7\x85\xe1\xde\xde\xde\xce\xa3G\x8f\
\x8e\x97\x96\x96\xde\xeb8\xce\xcaE\x01\xf8\x127\xa6\xa7\x8b\x1d\x97\xf3\x91\
\xb1\x19\x9cP\xc8\xebAj\x1a\x8e\x10\t\x08!P\x03\x17E\x13(\x17\xdcJ\x13q-\xf8\
\x8f\x15a$o\x12\xc9Ab$\\\x18\xdb\xbf\x7f\xff_\x03k\xbc^\xef:)\xe5J\x8f\xc7\
\xe3\x00\x9a\xa3r\x97\x0c\xa0\x94\xa3\xa2\x91\x89\xb0e]\x9e\xf6\x18\xca\xd2\
\x8c\x04\xb8\x0b\x0f\xc8\xf3}\xe2\xc8\x8e\xcf9\xff\x96\x06\x9d*B^G\xc4u\x9b\
\xc6\x95g\xa7M\xc2\x85(\x89B\x1e\x00N\xfa\xfd\xfe\xcb\x17.\\\xe8?~\xfcx\x17@\
\xcc\xbe\x0f\xf7\x1f+\xa69\xb7\x10\x9a\xeb\x19A\x8d\x8fg\xf8\x94i\x18\xd8\
\xba\x9e\x88\xbem3{\xb6G\xfc\xf4+_W_\xbb\xfb~\xe75\xcb\xc2L\x8e\xef\xf6\xeb9\
\x90\x12\xa0\xebo\x9f\xbb)\xe4\xba`\xbb\xf7%\'\x88\x1e8p\xe0o\x87\x87\x877o\
\xd9\xb2\xe5\xb7\x01\x1c\x95\xcflhMT\xe7\xed\x90&\xe6\xc3\x19\xbeD\x9e\xbb\
\x13\x87\xc2\xf4u\x9cRo?\xffM\xfewdD\xc5\x93c\xbb\x80.l\xfa\xd1\xfd\xfb/\xb5\
\x8c\xba\x17\xba\x8fZW\x84\x04\xec\xe1\xe1\xe1~ ?##\xa3,\x1a\x8d.\x1c:t\xe8?\
:\x9a\xdf:\xfa\xc4cVA\xb0\x00_V\x96\xe6\x0f\xcd9S\xe7\xfa\x19\xfc\xc9[\x0c\
\xbe\xfd6\xe1\x14\x80\xd4\xe5Q.\xd3S\xc5]\x95>\x1f\x17}\xb8\xf29\xb9d[\x85+_\
i:\x89\x17\xbd\xf2\xd5\xabW\xaf\xce\xce\xce\x8e\x9e<yr\x80\xc4\x93[\xa6\x8d\
\xe3\xb6%oC\\Y$R\x85\xa4\xffN\x7f\x05\xe4f\x04\\\xab\xbbB\x0c\xc0O\xe2E\xcf\
\xcdY\x95vmjKut9\'\xd2\xa3\x9d\x9e:7\x0c\x9f*\x80\xb4c\xba3z\xca\xb9\xe5\x84\
/\'`9\'\xae\x05\xfdK\xc1Cr{}\xb9\xcd\xdd\x1b\xe8\xe9\x01\xb8\x9e\x80\xeb\xf5\
\xd4{n\n~Q\x00\\{{}\x99\xdf\xcb9\xb6\x9c\x80T\x11\xe9\x82\xd2\xffv\xd3\xe0n\
\xfb?v\xdd\xb1w\xe0HK\x87\x00\x00\x00\x00IEND\xaeB`\x82\x16\xb5\xedB'
