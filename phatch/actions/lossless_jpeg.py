# -*- coding: utf-8 -*-
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
# Phatch recommends SPE (http://pythonide.stani.be) for editing python.

# Embedded icon is designed by Alexandre Moore(http://nuovext.pwsp.net).

# Follows PEP8

try:
    _
except NameError:
    _ = unicode

from core import models
from lib.reverse_translation import _t

#no need to lazily import these as they are always imported
from lib import system

AUTOMATIC = _t('Automatic (use exif orientation)')
COPY = _t('Copy')
CROP = _t('Crop')
ROTATE = _t('Rotate')
FLIP = _t('Flip')
GRAYSCALE = _t('Grayscale')
THUMB = _t('Regenerate thumbnail')
TRANSPOSE = _t('Transpose')
TRANSVERSE = _t('Transverse')

ROTATE_AMOUNTS = ('90 degrees', '180 degrees', '270 degrees')
HORIZONTAL = _t('Horizontal')
VERTICAL = _t('Vertical')
FLIP_DIRECTIONS = (HORIZONTAL, VERTICAL)
LOSSLESS_JPEG_FORMAT_ERROR = \
    _('Lossless JPEG transformation does not work on a %s image:')


class Arguments(list):
    """List with tweaked append behaviour to make it suitable for
    command line arguments."""

    def __str__(self):
        return ' '.join(self)

    def append(self, *options):
        option = '-%s' % options[0]
        if len(options) > 1:
            option += ' %s' % ' '.join(options[1:])
        super(Arguments, self).append(option)


class Exiftran(object):
    name = 'Exiftran (with exif support)'
    command = system.find_exe('exiftran')
    angles = {'90 degrees': '9', '180 degrees': '1',
                        '270 degrees': '2', }
    directions = {HORIZONTAL: 'F', VERTICAL: 'f'}
    transformations = (AUTOMATIC, ROTATE, FLIP, THUMB, TRANSPOSE,
                        TRANSVERSE)

    def interface(self, action, fields):
        fields[_t('Transformation')] = action.ChoiceField(
            self.transformations[0], choices=self.transformations)
        fields[_t('Angle')] = action.ChoiceField(ROTATE_AMOUNTS[0],
            choices=ROTATE_AMOUNTS)
        fields[_t('Direction')] = action.ChoiceField(FLIP_DIRECTIONS[0],
            choices=FLIP_DIRECTIONS)
        fields[_t('Preserve Timestamp')] = action.BooleanField(True)
        fields[_t('Show Advanced Options')] = action.BooleanField(False)
        fields[_t('Update JPEG')] = action.BooleanField(True)
        fields[_t('Update Exif Thumbnail')] = action.BooleanField(True)
        fields[_t('Update Orientation Tag')] = action.BooleanField(True)

    def get_relevant_field_labels(self, action):
        advanced = action.get_field_string('Show Advanced Options') \
            in ('yes', 'true')
        relevant = ['Transformation']
        transformation_fields = {ROTATE: 'Angle', FLIP: 'Direction'}
        transformation = action.get_field_string('Transformation')
        if transformation in transformation_fields:
            relevant.append(transformation_fields[transformation])
        if transformation == THUMB:
            relevant.append('Preserve Timestamp')
        else:
            relevant.append('Show Advanced Options')
            if advanced:
                relevant.extend(['Update JPEG', 'Update Exif Thumbnail',
                    'Update Orientation Tag'])
        return relevant

    def get_command_line_args(self, action, photo):
        info = photo.info
        values = action.values(info)
        args = Arguments()
        #transformation
        transformation = values['transformation']
        if transformation == AUTOMATIC:
            args.append('a')
        elif transformation == THUMB:
            args.append('g')
        elif transformation == ROTATE:
            args.append(self.angles[values['angle']])
        elif transformation == FLIP:
            args.append(self.directions[values['direction']])
        elif transformation == TRANSPOSE:
            args.append('t')
        elif transformation == TRANSVERSE:
            args.append('T')
        #options
        if not values['update_jpeg']:
            args.append('ni')
        if not values['update_exif_thumbnail']:
            args.append('nt')
        if not values['update_orientation_tag']:
            args.append('no')
        if values['preserve_timestamp']:
            args.append('p')
        #done!
        return args

    def get_command_line(self, action, photo, input, output):
        return '%s -i %s %s -o %s' % (self.command, system.fix_quotes(input),
            self.get_command_line_args(action, photo),
            system.fix_quotes(output))


class Jpegtran(models.CropMixin):
    name = 'Jpegtran (without exif support)'
    command = system.find_exe('jpegtran')
    transformations = (COPY, CROP, FLIP, GRAYSCALE, ROTATE, TRANSPOSE,
                        TRANSVERSE)
    copy_choices = (_t('None'), _t('Comments'), _t('All'))
    directions = {HORIZONTAL: 'horizontal', VERTICAL: 'vertical'}
    angles = {'90 degrees': '90', '180 degrees': '180',
                        '270 degrees': '270'}

    def interface(self, action, fields):
        # Juho: space hacks. get rid of those with ids later
        fields[_t('Transformation ')] = action.ChoiceField(
            self.transformations[1], choices=self.transformations)
        fields[_t('Copy')] = action.ChoiceField(self.copy_choices[1],
            choices=self.copy_choices)
        fields[_t('Angle ')] = action.ChoiceField(ROTATE_AMOUNTS[0],
            choices=ROTATE_AMOUNTS)
        fields[_t('Direction ')] = action.ChoiceField(FLIP_DIRECTIONS[0],
            choices=FLIP_DIRECTIONS)
        super(Jpegtran, self).interface(fields, action)

    def get_relevant_field_labels(self, action):
        relevant = ['Transformation ']
        transformation = action.get_field_string('Transformation ')
        transformation_fields = {
            COPY: ['Copy'],
            CROP: \
                models.CropMixin.get_relevant_field_labels(self, action),
                #specify explicitly from crop mixin
            ROTATE: ['Angle '],
            FLIP: ['Direction '],
        }
        if transformation in transformation_fields:
            relevant.extend(transformation_fields[transformation])
        return relevant

    def get_command_line_args(self, action, photo):
        info = photo.info
        args = Arguments()
        #pixelfields defined in the CropMixin
        values = models.CropMixin.values(self, info, action=action)
        #transformation
        transformation = values['transformation_']
        if transformation == COPY:
            args.append('copy', values['copy'].lower())
        elif transformation == CROP:
            mode = values['mode']
            if mode == 'Auto':
                bbox = photo.get_flattened_image().getbbox()
                values['left'], values['top'], values['width'], \
                    values['height'] = bbox
            else:
                if mode == 'All':
                    values['left'] = values['top'] = values['right'] = \
                        values['bottom'] = values['all']
                values['width'], values['height'] = info['size']
                values['width'] -= values['right'] + values['left'] + 1
                values['height'] -= values['bottom'] + values['top'] + 1
            args.append('crop',
                '%(width)sx%(height)s+%(left)s+%(top)s' % values)
        elif transformation == ROTATE:
            args.append('rotate', self.angles[values['angle_']])
        elif transformation == FLIP:
            args.append('flip', self.directions[values['direction_']])
        else:
            #grayscale,transpose,transverse
            args.append(transformation.lower())
        #done!
        return args

    def get_command_line(self, action, photo, input, output):
        return '%s %s %s > %s' % (self.command,
            self.get_command_line_args(action, photo),
                system.fix_quotes(input),
                system.fix_quotes(output))


def utilities_dict(*utilities):
    d = {}
    for utility in utilities:
        d[utility.name] = utility
    return d


class UtilityMixin(object):
    file_in = 'file_in.tif'
    file_out = 'file_out.png'

    def interface(self, fields):
        super(UtilityMixin, self).interface(fields)
        names = self.utilities.keys()
        fields[_t('Utility')] = self.ChoiceField(names[0],
            choices=names)
        for utility in self.utilities.values():
            utility.interface(self, fields)

    def get_relevant_field_labels(self, relevant=None):
        if relevant is None:
            relevant = []
        utility_name = self.get_field_string('Utility')
        utility = self.utilities[utility_name]
        relevant.append('Utility')
        relevant.extend(utility.get_relevant_field_labels(self))
        return relevant

    def apply(self, photo, setting, cache):
        info = photo.info
        utility_name = self.get_field('Utility', info)
        utility = self.utilities[utility_name]
        self.call(photo, info, utility)
        return photo

    def call(self, photo, info, utility):
        """This is decoupled from the apply method so we can overwrite it."""
        photo.call(utility.get_command_line(self, photo,
            self.file_in, self.file_out))


class LossLessSaveUtilityMixin(models.LosslessSaveMixin, UtilityMixin):
    """For lossless JPEG operations, this has to work on the source jpeg files
    immediately, otherwise it makes no sense. So we need to overwrite the
    call method."""

    format = 'JPEG'

    def call(self, photo, info, utility):
        """This is called by the apply method."""
        format = info['format']
        if format != self.format:
            raise Exception('%s:\n%s' \
                % (LOSSLESS_JPEG_FORMAT_ERROR % format, info['path']))

        system.call(utility.get_command_line(self, photo, info['path'],
            self.get_lossless_filename(photo, info)))

    def get_relevant_field_labels(self):
        """This should work like a save action. So it needs a filename and
        folder, while the file type is fixed (e.g. JPEG)."""
        return super(LossLessSaveUtilityMixin, self)\
            .get_relevant_field_labels(['File Name', 'In'])


#---Phatch
class Action(LossLessSaveUtilityMixin, models.Action):
    label = _t('Lossless JPEG')
    author = 'Juho Vepsäläinen'
    email = 'bebraw@gmail.com'
    version = '0.1'
    tags = [_t('transform'), _t('size')]
    __doc__ = _t('Rotate, flip, grayscale and crop')

    utilities = utilities_dict(Exiftran(), Jpegtran())

    def init(self):
        self.find_exe('exiftran')
        self.find_exe('jpegtran')

    icon = \
'x\xda\x01\x17\r\xe8\xf2\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x000\x00\
\x00\x000\x08\x06\x00\x00\x00W\x02\xf9\x87\x00\x00\x00\x04sBIT\x08\x08\x08\
\x08|\x08d\x88\x00\x00\x0c\xceIDATh\x81\xedZil\\\xd7u\xfe\xee\xbdo\x997\xf3f\
\xe56\x1c\xaeCR2IQKJ\x15\xb6\x1b&u\x92\x06F\x9dn^\xe5\xd8N+\x07\x08R$E\xba\
\x04\x90\x91\xa4Nb#\x0eZ@\x0e\x0c\xd5h\xd0\xd4\x89\x9b\xf4G\x1at\xf3R\xc5H\
\xd0:\x8e\xc4T\x85*\xcb\x91c9\xb5D\x8a\xa4\xc4u4\x1b\xc9yo\xdev\xef\xed\x8f\
\xe1p\xb1e\x8a5\xa9\x7f=\x7f\xee\x1b\xcc\x9ds\xcf7\xe7;\xdb\x9d\x01\xfe_\xb6\
&CCC\x00\x80\x8e\x8e\x0e5\x1e\x8f\xd3h4\xba#z\x95\x1d\xd1\xb2\x05\xd1u\x1d\
\x86a\xd0;>\xf6\xb1{\xaa\xd5\xea\x9b\xcdMM\xe7\x8e\x1e=\xbam\xbdt\x07l\xdb\
\xdaA\x94\xc2\xf3\\\xed\xa6\xdd\xfd\xbf\xd9\xdf\xdf\x7f\xdf\xd1\xa3G\xe9\x9e\
={\xb6\xadwG<\xc0\x18#\x8c\xb1$\xe7|\x89s\x1e\\kOgW7R\r\x8d\xd1x<\x9e5<\xbdk\
dd$\x19\x8dF\x0b\xe7\xcf\x9f\xdf\xd6\xd9;\xe2\x01\xce\xb9\xde\xd5\xd5\xf5POO\
\xcf\xd0\xcd7\xdf|\xcd=Q3\x8a\x86\x86\x86\xa4\x1e\xd2[\xc2a\xa3\xa7\xaf\xaf\
\xaf\xa3\xaf\xaf\x0f\xbbv\xed\xda\xd6\xd9\x1b<0\xfaw\xab\x8fi\x00\x05\x00\
\xfe\xc8\xe1-\xe9\x91\xad\xad\xad\xd9x<\xde\xf2\xe2\x8b/\xbe\x11\x89D\x02\
\xcb\xb26l\xe8\xcef1?7\xd7\xc4\x18\x8b\x13\xa8\x86i\x9a\xcdmmm\x88\xc5b\xdb\
\x02\xf0\x0e\x0fH\tH\x89\xfb\xa4\xc4\x1d\x00p\xf2\xd9-\xe9\xf1\t!\xcb\x99L\
\xe6\xf7\x86\x86\x86\x06\x86\x87\x877\xbc\xd9\xdb\xdb\x8b\x87>q\x18\x99\xb6\
\xf6.EQb\x94R\xcd4\xcd\xcc\x03\x0f<\x00)\xe5\xce\x02 \x04 \x04\xcd\x00\xbe*%\
vak\xfa\x85m\xdbW#\x91Hw\x7f\x7f\xff=\'N\x9c\xd8\xa07\x1a\x8d\xa27\xdb\x0eEa\
\x19F\xa9\xc6\x18S\r\xc3\xc8ttt@U\xd5\x9d\x06@\x00@\x98\x89\xc4\x01EU\xff\\\
\x08\x98\xd7\xf3\xc2\xb1c\xc7P,\x16g\x84\x10A&\x93\xb9gpp\xf0\xa6\x91\x91\
\x91\xb5C(\x05!D\x8d\xc5\xe3=\xb5\x97\x94\x86B\xa1\x0c!\x84m\xcb\xfaM\x00\
\xa0\xb1\xb5\x1d\xa9t\xe6\x10\xa5\xf8\xa4[\xdd\x9cJO?\xfd4\xca\xe5\xf2l\xb5Z\
-\xc6b\xb1\xfe\xc1\xc1\xc1\xbbGGG\xa9\xa6i\x00\x00!\x04\xb2==\xa1\xb0\x11\
\xee\xc4\x8aKUUmH\xa7\xd3\x1ac\xdb\xc3p\xcd,$%\xc0\x14\x05\x99\x9e]\xba\x99L\
\x1eQ5\xdc\x06\xf9\xee r\xb9\x1cJ\xa5\xd2\xd5J\xa5\x92c\x8c\xd1L&s\xef\xd0\
\xd0P_=\x16z{\xfb08\xb0\'\xa6(\xacy\xf5`J\xd5p8Lw<\x06VA@\xc20M\xb4\xf5\xeej\
\x0b\x85C\x8fs\x8e\xf6w\xdb[.\x97!\x84(\x94J\xa51\xce9\xa2\xd1\xe8\xe0\xc0\
\xc0\xc0]\xa7N\x9d"\x86a`\xef\xfe\xf7\xa1\xa7\xaf\xaf%\xa4\xebi)%\x08! \x84P\
UU\xc9\xb6\xac\xdf\x0c@\r\x85D\xa2\xa9\x05\xcd\x9d]#\x8aF\x1e\x11\x1c\xa1M\
\xa8T\xc9\xe5r\xaf{\x9e\xe7)\x8a\xa2d2\x99C\xfb\xf6\xed\xeb\x19\x1e\x1e\xc6\
\xee\xdd\xfd\xd04\xbd\x892\xb6\x9a3\t!LQ\x94\x1b\x0c\xa0v\x10\xd2]Y\x92lN?L(\
\xee\xd7B\x91kR\xe9\x85\x17\xfe-(\x14\no8\x8eS\x96R\xc24\xcd=\x03\x03\x03w\
\x8e\x8e\x8e\xe2\xe3\x87\xeeBsSS7\xa5\xd4\xa8Sf\x05\xc0\xb6\x0b\xe9u\x15H\
\x00\x8a\xaa\xa1\xadww$\x12\x8b}\xc9\xb1\xac\x83\xd7\x8a\x87C\x87\xee\xc5\
\xd4\xd4\xd4\x85r\xb9|\t\x00\x18cj:\x9d>\xb4g\xcf\x9en\x00\x88D"]\x94@\xab\
\xef\'\x840\xc6\xd8\xce{@\xae{\x90@-\xa2\x01Dbqdz\xfa\xfa4C}\x8cs4\xbe\xfds\
\xd5j\x15B\x88\xd9\xe9\xe9\x99SA\x10p\x00\x88F\xa3\xfb\xf6\xee\xdd\xfb\xbb\
\x84\x90\x90\xa6\xeb\x1bbH\x08\x11\xf8\xbe/\xeaYo\xc7\x00\xac\xda/%\xa4\x10\
\x1b\xd6T\xba\x15Mm\x9d\xb7+*\xfe\x84\x07P\xaeA%kb\xe2\xd2\xc9J\xa5R\x00\x00\
J\xa9\x96N\xa7\xef?x\xf0W\x07L\xd3\xec\x94R\xac\xea\xf6}\xbf<>>\xee\x05\xc15\
{\xbf\x9d\x00 j\x86\x0b\x01\xb1\xb2\x02\x04\xe9\xae,\x8b54}\x86R\xfc\x0e!t\
\x03\x95\xc2\x91\x08&&&\xce\xe5rWW[\xcch4\xba\xbf\xb7\xaf\xf7AJH\x93\x94\x12\
\xf5\xef\xdb\xf3\xbc\xa2m\xdb\xbe\xef\xfb7\n\x80\x84\x10|\xd5x!8\x04\xe7P4\r\
\x99l_\xd20\xc3_\xe1\x81\x18\x80\\k\x02\xedZ\x037;33\xfd\xb3\xbae\x84\x10\
\xa3\xbb\xab\xfb\xe3\x94\xd26)%@\x08\x84\x102\x08\x82"\x00\xae(\xdb\xeb\xe8\
\xaf\x03@@\xae\x03!\x85\x80\xe0\x1c\x91x\x1c-\x9d\xdd\xfbT\x9d}\x99s\xc4\xd6\
\xd7")\xa535u\xf9g\x95J%\x07\x00R\x08\x84\x0c\xa3UU\x95\xd8\xba=\x81\xe7yE)%\
(\xdd^"\xban\x0c\x88u4Z\xff\x9cjiE\xb2\xa5\xf5.\xa6\xe0\xd3<\x00\xa9S)\x1a\
\x8d\xe2\xf2\xe5\xa97\xf2\xf9\xc2/\x80ZATUU\x12BV;O!D\xe08N\xf1\xb5\xd7^\x83\
\xe7y7\x08\xc0z\x83%\x07\x0f\x825op\x0e\x10\x8a\x96\x8e.\xcd\x8c\'\xfe\x8cP\
\xfc\x06P\xa3R\xa5R\x01\x80\x85\x99\x99\x99\x93A\xc0=!$"\x91(\x18[;J\x08\x11\
\xd8\xb6]:}\xfa\xf4\x8d\xf3\x006x@\xc2Z*c\xb9\\\x82\x14r\xc5\x1b\x1c\xaa\x1e\
BKgw:d\xe8\x8f\t\x8en)\x01J\x81\'\xbe\xfe\x17\xfe\xd8\xf8\xd8h\xa5R\x99\x91R\
Ba\x84\x84\r\x03!=\x04R\x8b\x01\xc7u\xdd\xe5\\.\xb7-\xe37\x05P\x0f\xe2:\xf7}\
\xc7\xc5\xc2\xe5Ix\x8e\xbdF/\xce\x11I$\xd0\x90i\xbbUQ\xe9\x17\x04\x87\xf1\
\xd3o\x03_~\xf4K\x98\x9d\x99\xf9e.\x97\xfbo\x80@\n!\x17\x17\xcb\xc4\x0fj\x19\
\x87s^\r\x82\xa0R*\x95\xb0\xb8\xb8\xb8\xc3\x00V\x02R\xbe\x9d\xfb\x90\xb0\x97\
\xca\x8b\xf9\xd9i\x9f\xf3`]`K\xa4ZZ\x11kh|\x88P|"\x1c\x8f\xe2\xd7\x879\x00\
\x14&&&^v]\xafb\x18\x06U\x14\x05\x8c1\x08!\xc09\xb7]\xd7\xb5\x96\x96\x96066\
\xb6\xc3\x00\xea8\xd6e\xa1:\x18\x00?*\xe5\x16~\xb2\\,\xac\x03\xc7A(ES[G8\x1c\
\x8d|\xc1*-\xdf\xfa\xd5?\x04\x06\x06\x06\xc5\xf9\xf3\xe7O\x95J\xa51M\xd7!\
\x84\xc0\xdc\xfc\x02\x82 \x00\xe7\xdc*\x97\xcbv\xb9\\\xde\x96\xf1\xef\x02@\
\xae\x00\x10\x1b\x8c\x94R\x00\x84\xccz\xae\xff\xb5\xfc\xec\xf4\xac[\xb5\xd7\
\xf6p\x01-d\xa0\xb1\xb5\xbd[\xd5\xd5\xc7\xa4@\xfa\xce_{\x13\x95\xca\xf2\x84S\
\xb5_\xd7T\x15\x9cs$\x13q)\x84\xc0\xc2\xc2Bebb\xc2\x99\x9c\x9c\xbc\x11\x00V`\
\xacz\xa0\x0eB\x02\x00\xed?x\xf0\xa4\xbd\xbc|\xac0?\xeb\xd72S\xbdVp\x98\x89\
\x14\x12M\xcd\x1fa\n>\x7f\xf7G\xa0\x02\xb0\xdb\xda\xdb\n\x8a\xaa \x08\x82\
\xa0P(x\x85B\x01\x9e\xe7\xe9\xba\xae\xd3\xed\xce\xc3\xc0&\x17[RJ\x08\xce\x01\
\xac\x8c\x99\xb5\x1cN&\xdf|\x03\x82\xe3[K\x85\xfc\xfbC\xe1\xc8o\xc7R\rk{@\
\x90lNS\xd7\xb6?U)\x97\xce\x10%y\xdcs\xbd\xeeB\xbe\x80b\xa9\xf8\xe3\x8b\x17/\
\x8eG\xa3\xd1\x87\xcf\x9c9\xd3\x9f\xcf\xe7o\xd14\xed\x85T*\x85b\xb1x\x03\x00\
\xd4\x83t\xc58)\x05 \x01\xc6\x18(C)\xf0\x82\xaf\x95\x16\xe6\xf6\xea!\xa3[3\
\x8c\xd5"E\x19C*\xdd\x1a\xf7\xbd\xea\xa3G\xfe\xc0\xe7\xdf\x7f\xfe\x85\xfd\
\xcf=\xff\x9c\x08\x85B\xff\xea\xba\xee\xa8\xe7y\x1f\xcd\xe5r\xfd\x91H\xe4\
\xcel6\xfbC\xdb\xb6\xb7\xd5\xcdm\x89B\xf5lS\x17B\x80\x85i\x9cvl\xfb\xc9Rn\
\xce\xe5\xbe\xbf\xa1\xd5\xd0\x8d0\x92\xcd\xe9\xc1\xceV<f[\x8b\xcd\xd3\xd3\
\xd3Ksss\x17\xa7\xa6\xa6&\x00\x9cd\x8c\xc1u\xdd\x0f]\xbdzu\xf7v\x87\xfaM)$W\
\xd2\'!\x14B\n\xd4\x1a\x03\x89\x91\xc3\xb5\x81F\x08|w\xb9\\\x1a\xd1\x8d\xf0\
\xa1h\xaa\x11\x94\xd6\xa9$\x11O%\t\xd1\xc5 \xe7E\x10B\xc6\x01L\x0f\r\r\xb9\
\x85B\xe1x(\x14\xba\xd7\xb2\xacN\xc7qn\xcfd2\xd3\x00\xde\xef\xba\xeen)\xa5\
\xa7i\xda\x99D"q\xce\xf7}o|||{\x00\x84\xa8\xc5\x00\x88\\\xbbA[Y\x08\x01(\xc5\
2\xf7\xc5\x13\x8b\x85\xab\x07\x14\xcd\xb8i6\xaf\xe3\xe7\xbf\xf4\x91/\td\x9a\
\x15L\xce\x1bp\\\x01EaE]c\xe5+W.\x83Rv:\x14\n\xfd\xdc\xb2\xac\xdb\\\xd7}xff\
\xe6v\xdb\xb6?@\x08\t\x13B\xa4eY\x05\xc7q\xbe\x95H$\xfe\xb2\xb3\xb3s\xe9\xf2\
\xe5\xcb\xef\x11\xc0\xdbc\xa0V\x07\x90j\xd5\xf1\xfc\xd7m\x14f\x01\xd7\x07\
\xee\x7f\xaa\xef\x17\xff\xf2\x95\xc9c\xff\xf8\x1f\xa5\xa7\x9e{\x99\xabSW*\
\xf0\x03\x81\x90\xc6\x10\x8f\x1bp=\x0f\x07v#\xf9\xc7\x0fVZ.L\xa1\xf0\xc4\xdf\
\x06\x0b\x99L\xe6%]\xd7G,\xcb\xda\xeb8\xce\x90i\x9ac\x9a\xa6\x9d\xa4\x94\xaa\
\xbe\xef\x7f\xd8\xb2\xac#\x8a\xa2\x14\xf3\xf9\xfc\x93\x8d\x8d\x8d\xc8\xe7\
\xf3\xef\xd5\x03b\xed\xeb\x86\x04\x08\xf9\xd0\xfcD\xf9o\x1a\xdb(\xa9{\xe6\
\x95o\\\x12O}?\xde\xfd\xd2\x89eT\x1d\x07aCE"\xa6\xc1q\x05\x16r\x8b\x90\x1280\
h\xf4\xed\xeat\x8e\xf4\xb5\x8b\xcf\x8e\xcd\xb6Z\xaf\x9c\xe1\xffn\x18\xc6\xa7\
m\xdb\xee\xd1u}N\xd7\xf5\xcf\xe7r\xb9\x9f\x00PZ[[\xef\xe3\x9c?Y\xadV\xef\xce\
f\xb3\xcfr\xce7MQ[\x02@\x08\xa0h:\x12M-C\x00\x86\x00\x80\x00\xa0\x94\xe0\x7f\
.I\x9c{\xab\x82\xaa\xe3`\xcfMq\x1c\xfa\xad\x18\xb2\x1d\n\xc6\xa6\x80g~P\xc6\
\xdc|\x19\xbd\xbdIDb\xd6\xa1\xa5R\xf9\xd5\x1f\x1c\x9f\xfd+\xca\xb4\xb7Z\x9a\
\x1b\x7f\xaaiZ\x0f\x80\x82\xa6ig\xdb\xdb\xdb+\x9e\xe7A\x08\xf1\x12c\xecs\xbe\
\xefg<\xcfK\x10B\xde+\x80\xd5\xf6\x01\x12\x00%\x14\xba\x11\xae\x8d\x84+\x838\
!\x04\xe7.\xba\x98\x9c\xa9\xa2\xb9\xd1\xc0\xe7\x0e\'\xf0\xe1[5h\x1aE\xcc\x14\
`\x94B\xd7(\xba\xda4\xc4R\xa1\x90\xeb8GN~\x87\x9c\xcb\xd9\xbbO\xfc\xd1\x13\
\xcb\xc7C\xa1\xd0=\xd5j\xb5\xd3\xf3\xbc~\xdf\xf7gL\xd3\x04\xa54Z\xadVc\x84\
\x10\x1b\x00\xbf\xde\xcd\xdd\xa6\xed\xb4X\xa9\xb0\xebG\xca\xfa*\x05G\xb5\x1a\
\xe0\xfc\x05\x0f<\xe080\x18\xc1\xcd\xfb\x15(TBp\x81\\A`\xb9\xe2!\x1aaH\xc6\
\x08\x98\xaa"\x9alhg*{\xbc3q!\x93/V\xff3\x1c\x0e\xbf\n nY\xd6#\x86a\xbc\x8f1\
6`Y\xd6\x11\xc7q:TU}\xd3q\x9c\xc2\xca|\xf1\x7f\x07 \x85\\\xcb\xedr\xe34V\xbb\
\xa5\x10p\\\x81|)\x00@\xb1;\xab"\x1c\x92\xe0+\xb5`vA\xc0\xae\x06hL1\xa4\xe2\
\x00\x0fj\xf5!\x12K|\xd0\xe3\xe4\x91\xc7?U.\x03\xe4{\xa6i\x96\x1c\xc7\xf9h>\
\x9f\xff\xd1\xfc\xfc\xfc\xcb\x8b\x8b\x8b\xbf\xafi\xdaUM\xd3\xfe!\x9f\xcfW\
\xae\xd7n\xbf\x83Bkc_m\n\x03\x00\x10\xb2\x91:  \x14\x08| \x08j4\xa3DBr\x1f\\\
\x10p\x0e\xcc\xe5\x00\xcf\xe3hL\xe9\x08\x878\x02_\x02\x040"&\xf1\x1c\xfb\x93\
\x1f<X=\xfb\xc5\xbf.>\xd7\xdc\x94\xcc$\x93\xc9\x07=\xcfK\x03\x90\xaa\xaa\xfe\
\x17\xa5\xf4\xbb\x8b\x8b\x8b\xc7M\xd3\xdc\xd4\xf8k\x03\xa8-K\x8em\xcdy\x8e\
\xc37\xbc\xb9\xee\x0e\x8a\x10\xc0\xb2\t\xd1\x15=\x01 2q\xb9\xea\xe5\xe7\xcby\
U\x95\xa2b\x13:y%\xd6(%\xd7\xa2!o\xc9*.,\xb9J\xad\x9d"\x04\xe0A\xc0\xa4\xc4\
\xe1\x93\xdfqGG\x0e\xe7\x9e\x8a\xc7\xa3/i\x9a\xd6.\xa5\xac\xba\xae{\xc9\xb2\
\xac+\x8a\xa2xo\xff\x99jK\x00\x88\x04@\xf0\xed\xc0\xe7\xff\x0c\xc9\xaf\xf1\
\x91\x9aP\x02,-\x82^\x9a1?\xab(\xe4OG\xcf\xfa\x8b\xcf$#\x9fy\xf4p\xe1\xd5\
\x7f\xfa\xb1\xd9~~\x1c\xdf\xa3\x14\xbb^\xbf\x80oj\xc4\xf9\xa6m\x81\xd6\xe3\
\x91\xd0\xda\xe8\t w\xf2Ya}\xe0\xe1\xc5\xb3\x00\xce\xae\xd7\xbf\xdd\xfb\xa2-\
\xc9\xf0\xf00\x1a\x1b\x1bo3Ms\x9a1&\x1b\x1a\x9a\xfe\xbe3\xfb+\xa9\xee\xec\
\xae\xdbS\xa9T\x89R\xea\x99\xa6\xf9P<\x1e\xbf\xf1\xc6\xbc\x17QU\x15\x9a\xa6\
\x99\r\r\rG5MsUU\xf5\x1b\x1a\x1aN777\xbf\xa5\xaa\xaaT\x14e\xd24\xcd\xfd;\xf5\
\xb7\x82\x1b"\xb7\xdcr\x0bL\xd3\xcc\xa6R\xa9g\x0c\xc3Xb\x8cIJ\xa9d\x8c\x15\r\
\xc3\xf8\xa2a\x18!\xc30n\xd8\xf9\xdb\xbe\xde\xae\x8ba\x18m\x86a\xdc\xc19\xbf\
5\x08\x02_J\xf9J\x10\x04?\xd4u}qyyy\xa7\x8ey\x87\xec\x18\x80\x15Q\x01\x84\
\x01\x08\x00\xd6\xcazC\xe5\x7f\x01O\x0b\xe24\x81\xa5^\x08\x00\x00\x00\x00IEN\
D\xaeB`\x82_\xcbCb'
