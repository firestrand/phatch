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
# Follows PEP8

"""
Store internally as a string.
Provide validation routines.
"""

try:
    _
except NameError:
    _ = unicode

import os

from PIL import Image

from lib.formField import files_dictionary, Form, Field, \
    ImageDictionaryReadFileField, \
    ImageDictionaryField, rotation_title_parser
from lib.reverse_translation import _t
from config import PATHS
from lib import openImage
from lib.desktop import DESKTOP_FOLDER, USER_FOLDER
if DESKTOP_FOLDER == USER_FOLDER:
    DESKTOP_FOLDER = os.path.expanduser('~/phatch')

from safeGlobals import safe_globals
Field.set_globals(safe_globals())


def init():
    pass


def negative(value):
    """Returns the negative value of a string expression.

    :param value: int or float expression
    :type value: str
    :returns: negative value of expression
    :rtype: str

    >>> negative('5')
    '-5'
    >>> negative('-5')
    '5'
    """
    negative_value = value.strip()
    if negative_value:
        if negative_value[0] == '-':
            negative_value = negative_value[1:]
        else:
            negative_value = '-' + negative_value
    else:
        negative_value = value
    return negative_value


class Action(Form):
    all_layers = False
    pil = None
    author = 'Stani'
    cache = False
    email = 'spe.stani.be@gmail.com'
    init = staticmethod(init)
    version = '0.1'
    tags = []
    tags_hidden = []
    valid_last = False
    __doc__ = 'Action base class.'
    metadata = []

    def values(self, info, pixel_fields=None, exclude=None):
        return self.get_fields(info, convert=True,
            pixel_fields=pixel_fields, exclude=exclude)

    def apply(self, photo, setting, cache):
        """Can be overwritten always returns the photo.

        If this method is not overwritten a pil method should be
        required."""
        values = self.values(photo.info)
        if self.cache:
            values['cache'] = cache
        if self.all_layers:
            photo.apply_pil(self.pil, **values)
        else:
            photo.get_layer().apply_pil(self.pil, **values)
        return photo

    def is_done(self, photo):
        """Method used for resuming when a batch was interrupted.
        Check if this image has been done already."""
        #check if there are not forbidden tags (new.*)
        try:
            #is_done_info is only available on save actions
            folder, filename, typ = self.is_done_info(photo.info)
        except KeyError:
            return False
        #check if file exists
        if not os.path.exists(filename):
            return False
        #check if file is valid
        return openImage.verify_image({'path': filename}, [], [])

    # for save actions

    def ensure_path_or_desktop(self, folder, photo, filename, desktop=False):
        """Ensures that folder exists. If it can't create the path,
        it will log an error in the photo and propose to save it in the
        desktop folder instead.

        :param folder: folder path
        :type folder: str
        :param folder: photo to log to
        :type folder: core.pil.Photo
        :param filename: targeted filename
        :type filename: str
        :param desktop: force saving on desktop
        :type desktop: bool
        :returns: same filename, or on desktop in case of errors
        :rtype: str
        """
        error = False
        if not desktop:
            try:
                self.ensure_path(folder)
            except OSError, message:
                desktop = error = True
        if desktop:
            base = os.path.basename(filename)
            if error:
                photo.log('Could not save "%s" in "%s":\n%s\n'\
                    % (base, folder, message))
                photo.log('Will try to save in "%s" instead.\n'\
                    % DESKTOP_FOLDER)
            self.ensure_path(DESKTOP_FOLDER)
            filename = os.path.join(DESKTOP_FOLDER, base)
        return filename

    # field classes which are specific to Phatch and
    # do not belong to formField
    class HighlightFileField(ImageDictionaryReadFileField):
        dialog = PATHS["USER_HIGHLIGHTS_PATH"]  # _('Select Highlight')

        def init_dictionary(self):
            self.dictionary = files_dictionary(
                paths=[PATHS["PHATCH_HIGHLIGHTS_PATH"],
                               PATHS["USER_HIGHLIGHTS_PATH"]],
                extensions=self.extensions)

    class MaskFileField(ImageDictionaryReadFileField):
        dialog = PATHS["USER_MASKS_PATH"]  # _('Select Mask')

        def init_dictionary(self):
            self.dictionary = files_dictionary(
                paths=[PATHS["PHATCH_MASKS_PATH"],
                        PATHS["USER_MASKS_PATH"]],
                extensions=self.extensions)

    class WatermarkFileField(ImageDictionaryReadFileField):
        dialog = PATHS["USER_WATERMARKS_PATH"]  # _('Select Watermark')

        def init_dictionary(self):
            self.dictionary = files_dictionary(
                paths=[
                    PATHS["PHATCH_IMAGE_PATH"],
                    PATHS["USER_WATERMARKS_PATH"],
                ],
                extensions=self.extensions)

    class PerspectiveField(ImageDictionaryField):
        dialog = _t('Select Projection')

        def init_dictionary(self):
            self.dictionary = files_dictionary(
                paths=[
                    PATHS["PHATCH_PERSPECTIVE_PATH"],
                ],
                extensions=self.extensions)

    class BlenderField(ImageDictionaryField):
        icon_size = (128, 128)
        option_name = None
        use_user_option = False
        title_parser = None

        def get_path(self):
            return os.path.join(PATHS['PHATCH_BLENDER_PATH'], 'preview',
                self.option_name)

        def init_dictionary(self):
            self.dictionary = files_dictionary(paths=[self.get_path(), ],
                extensions=self.extensions, title_parser=self.title_parser)

            if self.use_user_option:
                self.dictionary['User'] = os.path.join(
                    PATHS['PHATCH_DATA_PATH'], 'user.png')

    class BlenderObjectField(BlenderField):
        dialog = _t('Select Object')
        option_name = 'object'

    class BlenderRotationField(BlenderField):
        dialog = _t('Select Rotation')
        option_name = 'rotation'
        title_parser = rotation_title_parser
        # FIXME: these should be instance, not class variables!
        use_user_option = True
        selected_object = 'Box'

        def get_path(self):
            return os.path.join(PATHS['PHATCH_BLENDER_PATH'], 'preview',
                self.option_name, self.selected_object.lower())


class OffsetMixin(object):
    CENTER = _t('Center')
    CUSTOM = _t('Custom')
    MIDDLE = _t('Middle')
    LEFT = _t('Left')
    RIGHT = _t('Right')
    TOP = _t('Top')
    BOTTOM = _t('Bottom')
    POSITION = [CENTER, _t('Bottom Left'), _t('Bottom Right'),
        _t('Top Left'), _t('Top Right'), CUSTOM]
    HORIZONTAL_JUSTIFICATION = [LEFT, MIDDLE, RIGHT]
    VERTICAL_JUSTIFICATION = [TOP, MIDDLE, BOTTOM]

    def interface(self, fields):
        fields[_t('Orientation')] = \
            self.OrientationField(self.ORIENTATION[0])
        fields[_t('Position')] = self.ChoiceField(self.POSITION[0],
            self.POSITION)
        fields[_t('Offset')] = self.PixelField('5%',
            choices=self.OFFSET_PIXELS)
        fields[_t('Horizontal Offset')] = self.PixelField('50%',
            choices=self.OFFSET_PIXELS)
        fields[_t('Vertical Offset')] = self.PixelField('50%',
            choices=self.OFFSET_PIXELS)
        fields[_t('Horizontal Justification')] = self.ChoiceField(
            self.HORIZONTAL_JUSTIFICATION[1], \
            self.HORIZONTAL_JUSTIFICATION)
        fields[_t('Vertical Justification')] = self.ChoiceField(
            self.VERTICAL_JUSTIFICATION[1], self.VERTICAL_JUSTIFICATION)

    def get_relevant_field_labels(self):
        relevant = ['Orientation', 'Position']
        position = self.get_field_string('Position')
        if position == self.CUSTOM:
            relevant += ['Horizontal Offset', 'Vertical Offset',
                    'Horizontal Justification', 'Vertical Justification']
        elif position != self.CENTER:
            relevant += ['Offset']
        return relevant

    def values(self, info, pixel_fields=None, exclude=None):
        if exclude is None:
            exclude = []
        #transform position, offset to custom
        position = self.get_field_string('Position')
        exclude.extend(['Position', 'Offset'])
        # place in center of image
        if position == self.CENTER:
            self.set_field_as_string('Horizontal Offset', '50%')
            self.set_field_as_string('Horizontal Justification', self.MIDDLE)
            self.set_field_as_string('Vertical Offset', '50%')
            self.set_field_as_string('Vertical Justification', self.MIDDLE)
        # place in a corner of the image
        elif position != self.CUSTOM:
            offset = self.get_field_string('Offset')
            # horizontal
            if 'Left' in position:
                self.set_field_as_string('Horizontal Offset', offset)
                self.set_field_as_string('Horizontal Justification', self.LEFT)
            else:  # Right
                self.set_field_as_string('Horizontal Offset', negative(offset))
                self.set_field_as_string('Horizontal Justification',
                    self.RIGHT)
            # vertical
            if 'Top' in position:
                self.set_field_as_string('Vertical Offset', offset)
                self.set_field_as_string('Vertical Justification', self.TOP)
            else:  # Bottom
                self.set_field_as_string('Vertical Offset', negative(offset))
                self.set_field_as_string('Vertical Justification', self.BOTTOM)
        # continue as normal values but exclude position & offset
        if pixel_fields is None:
            pixel_fields = {}
        x, y = info['size']
        pixel_fields.update({
                'Horizontal Offset': x,
                'Vertical Offset': y,
            })
        return super(OffsetMixin, self).values(info,
            pixel_fields=pixel_fields, exclude=exclude)


class StampMixin(OffsetMixin):
    LOGO = 'Phatch Small'
    METHODS = [_t('By Offset'), _t('Tile'), _t('Scale')]

    def interface(self, fields):
        fields[_t('Mark')] = self.WatermarkFileField(self.LOGO)
        fields[_t('Opacity')] = self.SliderField(100, 1, 100)
        fields[_t('Method')] = self.ChoiceField(self.METHODS[2], self.METHODS)
        super(StampMixin, self).interface(fields)

    def get_relevant_field_labels(self):
        relevant = ['Method', 'Mark', 'Opacity']
        if self.get_field_string('Method') == self.METHODS[0]:
            relevant.extend(OffsetMixin.get_relevant_field_labels(self))
        return relevant


class LosslessSaveMixin(object):
    valid_last = True

    def interface(self, fields):
        fields[_t('File Name')] = \
            self.FileNameField(choices=self.FILENAMES)
        fields[_t('In')] = \
            self.FolderField(self.DEFAULT_FOLDER, choices=self.FOLDERS)
        super(LosslessSaveMixin, self).interface(fields)

    def get_lossless_filename(self, photo, info):
        #get file values
        filename = self.get_field('File Name', info)
        folder = self.get_field('In', info)
        typ = info['type']
        filename = os.path.join(folder, '%s.%s' % (filename, typ))
        #ensure folder
        filename = self.ensure_path_or_desktop(folder, photo, filename)
        photo.append_to_report(filename)
        return filename

    def is_done(self, photo):
        """Method used for resuming when a batch was interrupted.
        For metadata there is no way to know if this image has been done
        already, so return False by default."""
        return False

    def is_overwrite_existing_images_forced(self):
        """Always force overwrite as we want to store the tags
        in existing images."""
        return True


class CropMixin(object):
    crop_modes = (_t('All'), _t('Auto'), _t('Custom'), )
    _choices = ('0', '1', '2', '5', '10', '20', )

    def interface(self, fields, action=None):
        if action is None:
            action = self
        fields[_t('Mode')] = action.ChoiceField(self.crop_modes[0],
            choices=self.crop_modes)
        fields[_t('All')] = action.PixelField('30%',  # works with jpegtran
            choices=self._choices)
        fields[_t('Left')] = action.PixelField('0px',
            choices=self._choices)
        fields[_t('Right')] = action.PixelField('0px',
            choices=self._choices)
        fields[_t('Top')] = action.PixelField('0px',
            choices=self._choices)
        fields[_t('Bottom')] = action.PixelField('0px',
            choices=self._choices)

    def get_relevant_field_labels(self, action=None):
        """If this method is present, Phatch will only show relevant
        fields.

        :returns: list of the field labels which are relevant
        :rtype: list of strings

        .. note::

            It is very important that the list of labels has EXACTLY
            the same order as defined in the interface method.
        """
        if action is None:
            action = self
        relevant = ['Mode']
        if action.get_field_string('Mode') == 'All':
            relevant.extend(['All'])
        elif action.get_field_string('Mode') == 'Custom':
            relevant.extend(['Top', 'Left', 'Bottom', 'Right'])

        return relevant

    def values(self, info, pixel_fields=None, exclude=None, action=None):
        if action is None:
            action = self
        if pixel_fields is None:
            pixel_fields = {}
        # pixel fields
        width, height = info['size']
        pixel_fields.update({
            'All': (width + height) / 2,
            'Left': width,
            'Right': width,
            'Top': height,
            'Bottom': height,
        })
        # pass absolute reference for relative pixel values such as %
        # do NOT use super here or lossless jpegtran will fail
        return Action.values(action, info, pixel_fields, exclude)
