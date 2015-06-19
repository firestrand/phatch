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

"""
Store internally as a string.
Provide validation routines.
"""

#TODO: move all Phatch references to models

#---import modules

#standard library
import glob
import os
import re
import safe
import system
import textwrap
import types


if '_' not in dir():
    _ = str

#gui independent (lib)
import system
import unicoding
from odict import odict as Fields

NO_FIELDS = Fields()
_t = unicode
USE_INSPECTOR = _('Use the Image Inspector to list all the variables.')
USE_EXTENSIONS = _('You can only use files with the following extensions')

#---image
ALIGN_HORIZONTAL = [_t('left'), _t('center'), _t('right')]
ALIGN_VERTICAL = [_t('top'), _t('middle'), _t('bottom')]

FONT_EXTENSIONS = ['ttf', 'otf', 'ttc']
GEO_EXTENSIONS = ['gpx']

ICON_SIZE = (64, 64)

IMAGE_EXTENSIONS = ['bmp', 'gif', 'jpe', 'jpeg', 'jpg', 'im',
    'pcx', 'png', 'pbm', 'pgm', 'ppm', 'tif', 'tiff', 'xbm']
IMAGE_READ_EXTENSIONS = IMAGE_EXTENSIONS + ['cur', 'dcx', 'fli', 'flc', 'fpx',
    'gbr', 'gd', 'ico', 'imt', 'mic', 'mcidas', 'pcd',
    'psd', 'bw', 'rgb', 'cmyk', 'sun', 'tga', 'xpm']
IMAGE_READ_EXTENSIONS.sort()
IMAGE_READ_MIMETYPES = ['image/' + ext for ext in IMAGE_READ_EXTENSIONS]
IMAGE_WRITE_EXTENSIONS = IMAGE_EXTENSIONS + ['eps', 'ps', 'pdf']
IMAGE_WRITE_EXTENSIONS.sort()
IMAGE_MODES = [_t('Monochrome (1-bit pixels, black and white)'),
    _t('Grayscale (8-bit pixels)'),
    _t('LA (8-bit pixels, grayscale with transparency mask)'),
    _t('RGB (3x8-bit pixels, true color)'),
    _t('RGBA (4x8-bit pixels, RGB with transparency mask)'),
    _t('CMYK (4x8-bit pixels, color separation)'),
    _t('P (8-bit pixels, mapped using a color palette)'),
    _t('YCbCr (3x8-bit pixels, color video format)')]
IMAGE_EFFECTS = [_t('blur'), _t('contour'), _t('detail'),
    _t('edge enhance'), _t('edge enhance more'),
    _t('emboss'), _t('find edges'), _t('smooth'),
    _t('smooth more'), _t('sharpen')]
IMAGE_FILTERS = [_t('nearest'), _t('bilinear'), _t('bicubic')]
IMAGE_RESAMPLE_FILTERS = IMAGE_FILTERS + [_t('antialias')]
IMAGE_TRANSPOSE = [_t('Rotate 90'), _t('Rotate 180'), _t('Rotate 270'),
    _t('Flip Left Right'), _t('Flip Top Bottom')]

ORIENTATION = [_t('Normal')] + IMAGE_TRANSPOSE

TIFF_COMPRESSIONS = ['<compression>', _t('none'), 'g3', 'g4', 'jpeg',
    'lzw', 'packbits', 'zip']

IMAGE_WRITE_EXTENSIONS = ['<type>'] + IMAGE_WRITE_EXTENSIONS

IMAGE_READ_EXTENSIONS.sort()
IMAGE_WRITE_EXTENSIONS.sort()

RANK_SIZES = [3, 5]

RE_FILE_IN = re.compile('file_in([.]\w+)')
RE_FILE_OUT = re.compile('file_out([.]\w+)')


def files_dictionary(paths, extensions, title_parser=None):
    """Collects files with a certain extension in different folders and
    stores the files in a dictionary of which the keys are titled
    versions of the filename.

    Phatch uses this for fonts, highlights and masks.

    ..  seealso:::func:`system.filename_to_title`

    >>> files_dictionary(['/etc/apt'], ['.list'])
    {'Sources': '/etc/apt/sources.list'}
    """
    if title_parser is None:
        title_parser = system.filename_to_title

    files = []
    for path in paths:
        if path:
            for extension in extensions:
                files += glob.glob(os.path.join(path, '*' + extension))
    d = {}
    for filename in files:
        d[title_parser(filename)] = filename
    return d

# TODO: move this to some nicer place!


def rotation_title_parser(field, filename):
    filename = os.path.splitext(os.path.basename(filename))[0]

    return filename.replace('_', ' ').title()

#---form


class Form(object):
    """A form contains different fields for user input. It can
    retrieve and set single values. It can also dump all fields to
    a dictionary or do the reverse: load all fields from a dictionary.
    It provide common default values (CONSTANTS) and some tools
    such as ensure_path.

    ..  note::

        This is independent of any GUI toolkit.
    """
    #todo: move this as instance attributes
    label = 'label'
    icon = 'ART_TIP'
    tags = []
    exe = {}
    __doc__ = ''

    #default values <value>
    FILENAME = '<%s>' % _t('filename')
    FOLDER = '<%s>' % _t('folder')
    DESKTOP = '<%s>' % _t('desktop')
    FOLDER_PHATCH = '%s/phatch' % DESKTOP
    DPI = '<%s>' % _t('dpi')
    DATE = '<%s>-<##%s>-<##%s>' % (_t('year'), _t('month'), _t('day'))
    DATETIME = DATE + '_<##%s>-<##%s>-<##%s>'\
        % (_t('hour'), _t('minute'), _t('second'))
    EXIF_DATE = '<Exif_Photo_DateTimeOriginal.year>-' + \
        '<##Exif_Photo_DateTimeOriginal.month>-' + \
        '<##Exif_Photo_DateTimeOriginal.day>'
    ROOT = '<%s>' % _t('root')
    BYSIZE = '<%s>x<%s>' % (_t('width'), _t('height'))
    SUBFOLDER = '<%s>' % _t('subfolder')
    DEFAULT_FOLDER = '%s/%s' % (FOLDER_PHATCH, SUBFOLDER)
    TYPE = '<%s>' % _t('type')
    COMPRESSION = '<%s>' % _t('compression')

    # choices
    DPIS = [DPI, '<dpi/2>', '72', '144', '300']
    PIXELS = ['10', '25', '50', '100', '200']
    PIXELS_X = ['16', '32', '64', '128', '256', '640', '800', '1024',
        '1280', '1280', '1440', '1600', '1680', '1920', '1920']
    PIXELS_Y = ['16', '32', '64', '128', '256', '480', '600', '768',
        '960', '1024', '900', '1200', '1050', '1080', '1200']
    SMALL_PIXELS = ['1', '2', '5', '10']
    OFFSET_PIXELS = ['-75', '-50', '-25', '-10', '-5',
                        '0', '5', '10', '25', '50', '75', '100']
    FILENAMES = [
        FILENAME,
        '%s_phatch' % FILENAME,
        '%s<###index>' % _('Image'),
        EXIF_DATE,
        DATETIME,
    ]
    FOLDERS = [
        '%s_phatch/%s' % (FOLDER, SUBFOLDER),
        '%s/%s' % (FOLDER, SUBFOLDER),
        DESKTOP,
        FOLDER_PHATCH,
        DEFAULT_FOLDER,
        '%s/%s' % (FOLDER_PHATCH, BYSIZE),
        '%s/%s' % (FOLDER_PHATCH, DATE.replace('-', '/')),
        '%s/phatch/%s' % (ROOT, SUBFOLDER),
    ]
    STAMPS = [
        'Phatch',
        'Phatch (c)<%s> www.stani.be' % _t('year'),
        EXIF_DATE,
        DATE,
        DATETIME,
        FILENAME,
        '<%s>' % _t('path'),
    ]
    EXIF_IPTC = ['Exif_Image_Artist', 'Exif_Image_Copyright',
        'Exif_Image_ImageDescription', 'Exif_Image_DateTime',
        'Exif_Image_Make', 'Exif_Image_Model', 'Exif_Image_Orientation',
        'Exif_Photo_UserComment', 'Exif_Photo_WhiteBalance',
        'Iptc_Application2_Byline', 'Iptc_Application2_BylineTitle',
        'Iptc_Application2_Caption', 'Iptc_Application2_CaptionWriter',
        'Iptc_Application2_Category', 'Iptc_Application2_City',
        'Iptc_Application2_Copyright', 'Iptc_Application2_CountryName',
        'Iptc_Application2_DateCreated', 'Iptc_Application2_Keywords',
        'Iptc_Application2_ObjectName',
        'Iptc_Application2_ProvinceState', 'Iptc_Application2_Writer']

    def __init__(self, **options):
        """For the possible options see the source code."""
        fields = Fields()
        fields['__enabled__'] = BooleanField(True, visible=False)
        self.interface(fields)
        self._fields = fields
        self._fields.update(options)

    def interface(self, fields):
        """Describe here the fields. This is called from the __init__
        method.

        :param fields: an (usually empty) ordered dictionary
        :type fields: odict"""
        pass

    def __cmp__(self, other):
        """Comparison method for sorting.

        :param fields: an (usually empty) ordered dictionary
        :type fields: odict
        """
        label = _(self.label)
        other_label = _(other.label)
        if label < other_label:
            return -1
        elif label == other_label:
            return 0
        else:
            return 1

    def _get_fields(self):
        return self._fields

    def get_field_labels(self):
        return self._get_fields().keys()

    def _get_field(self, label):
        return self._fields[label]

    def get_field(self, label, info=None):
        if info is None:
            info = {}
        return self._get_field(label).get(info, label)

    def get_fields(self, info, convert=False, pixel_fields=None, exclude=None):
        if exclude is None:
            exclude = []
        if pixel_fields is None:
            pixel_fields = {}
        result = {}
        for label in self.get_field_labels():
            if label[:2] != '__' and not (label in exclude):
                param = None
                #skip hidden fields such as __enabled__
                if label in pixel_fields:
                    #pixel size -> base, dpi needed
                    param = pixel_fields[label]
                    if type(param) != types.TupleType:
                        param = (param, info['dpi'])
                elif self._get_field(label).__class__ == PixelField:
                    param = (1, 1)
                if param:
                    value = self.get_field_size(label, info, *param)
                else:
                    #retrieve normal value
                    value = self.get_field(label, info)
                #convert field labels to function parameters
                if convert:
                    label = label.lower().replace(' ', '_')
                result[label] = value
        return result

    def get_field_size(self, label, info, base, dpi):
        return self._get_field(label).get_size(info, base, dpi, label)

    def get_field_string(self, label):
        return self._get_field(label).get_as_string()

    def is_enabled(self):
        return self.get_field('__enabled__', None)

    def is_field_true(self, label):
        return self.get_field_string(label) in ('yes', 'true')

    def _set_field(self, label, field):
        self._fields[label] = field

    def set_field(self, label, value):
        self._get_field(label).set(value)
        return self

    def set_fields(self, **options):
        for label, value in options.items():
            self.set_field(label, value)

    def set_field_as_string(self, label, value_as_string):
        self._get_field(label).set_as_string(value_as_string)
        return self

    def set_field_as_string_dirty(self, label, value_as_string):
        self._get_field(label).set_as_string_dirty(value_as_string)
        return self

    def load(self, fields):
        """Load dumped, raw strings."""
        invalid_labels = []
        for label, value in fields.items():
            if label in self._fields:
                self.set_field_as_string(label, value)
            else:
                invalid_labels.append(label)
        return invalid_labels

    def dump(self):
        """Dump as raw strings"""
        fields_as_strings = {}
        for label in self.get_field_labels():
            fields_as_strings[label] = self.get_field_string(label)
        return {'label': self.label, 'fields': fields_as_strings}

    #tools
    def ensure_path(self, path):
        return system.ensure_path(path)

    def find_exe(self, program, name=None):
        if name is None:
            name = system.title(program)
        path = system.find_exe(program)
        if not path:
            raise Exception('You need to install "%s" first.' % name)
        self.exe[program] = path

#---errors


class ValidationError(Exception):

    def __init__(self, expected, message, details=None):
        """ValidationError for invalid input.

        expected - description of the expected value
        message  - message why validation failed
        details  - eg. which variables are allowed"""
        self.expected = expected
        self._message = message
        self.details = details

    def __str__(self):
        return self._message

    def __unicode__(self):
        if self.details:
            return '%s\n%s' % (self._message, self.details)
        else:
            return self._message

#---field mixins


class PilConstantMixin:

    def to_python(self, x, label):
        return x.upper().replace(' ', '_')


class TestFieldMixin:
    """ Mixin class, the to_python method should

    def to_python(self, x, label, test=False):
        "test parameter to signal test-validate"
        return x

    See set_form_field_value in treeEdit.py
    """

    def get(self, info=None, label='?', value_as_string=None, test=False):
        """Use this method to test-validate the user input, for example:
            field.get(IMAGE_TEST_INFO, value_as_string, label, test=True)"""
        if value_as_string is None:
            value_as_string = self.value_as_string
        return self.to_python(self.interpolate(value_as_string, info, label),
                label, test)

#---fields


def set_safe(state):
    Field.safe = state


def get_safe():
    return Field.safe


class Field(object):
    """Base class for fields. This needs to be subclassed but,
    never used directly.

    Required to overwrite:
    description - describes the expected value

    Optional to overwrite
    to_python   - raise here exceptions in case of validation errors (defaults
                  to string).
    to_string   - (defaults to string)

    Never overwrite:
    validate    - will work right out of the box as exceptions are raised by
                  the to_python method
    get         - gets the current value as a string
    set         - sets the current value as a string

    You can access the value by self.value_as_string

    This field interpolates <variables> within a info.
    << or >> will be interpolated as < or >

    :param value: initial value
    :type value: str
    :param visible: if the field will be visible as a field
    :type visible: str

    Invisible fields request a different kind of user interaction
    to change their values than a normal field. In Phatch this
    is used eg for enabling/disabling actions.

    A get_relevant_* method of a Form will show/hide fields
    which depend on other conditions.
    """

    allow_empty = False
    description = '<?>'
    safe = True
    _globals = {}

    def __init__(self, value, visible=True):
        self.visible = visible
        self.dirty = False
        if isinstance(value, (str, unicode)):
            self.set_as_string(value)
        else:
            self.set(value)

    def validate(self, names, _globals, _locals):
        """Helper method for :func:`safe.compile_expr`."""
        not_allowed = [name for name in names
            if not (name in _globals or name in _locals
                or name in safe.SAFE['all'])]
        return not_allowed

    def assert_safe(self, label, info):
        safe.assert_safe_expr(self.value_as_string,
            _globals=self._globals, _locals=info,
            validate=self.validate, preprocess=safe.format_expr)

    def interpolate(self, x, info, label):
        if info == None:
            return self.value_as_string
        else:
            try:
                return safe.compile_expr(x, _globals=self._globals,
                    _locals=info, validate=self.validate,
                    preprocess=safe.format_expr, safe=self.safe)
            except Exception, error:
                reason = unicoding.exception_to_unicode(error)
                raise ValidationError(self.description,
                    "%s: %s\n" % (_(label), reason), USE_INSPECTOR)

    def to_python(self, x, label):
        if x.strip() or self.allow_empty:
            return x
        raise ValidationError(self.description,
        '%s: %s.' % (
            _(label),
            _('can not be empty')))

    def to_string(self, x):
        return unicode(x)

    def fix_string(self, x):
        """For the ui (see 'write tag' action)"""
        return x

    def get_as_string(self):
        """For GUI: Translation, but no interpolation here"""
        return self.value_as_string

    def set_as_string(self, x):
        """For GUI: Translation, but no interpolation here"""
        self.value_as_string = x

    def set_as_string_dirty(self, x):
        """For GUI: Translation, but no interpolation here"""
        self.value_as_string = x
        self.dirty = True

    def get(self, info=None, label='?', value_as_string=None, test=False):
        """For code: Interpolated, but not translated
        - value_as_string can be optionally provided to test the expression

        Ignore test parameter (only for compatiblity with TestField)"""
        if value_as_string is None:
            value_as_string = self.value_as_string
        return self.to_python(self.interpolate(value_as_string, info, label),
                label)

    def set(self, x):
        """For code: Interpolated, but not translated"""
        self.value_as_string = self.to_string(x)

    @staticmethod
    def set_globals(_globals):
        Field._globals = _globals

    def eval(self, x, label):
        try:
            return safe.eval_safe(x)
        except SyntaxError:
            pass
        except NameError:
            pass
        raise ValidationError(self.description,
            '%s: %s.' % (_(label),
                _('invalid syntax "%s" for integer') % x))


class CharField(Field):
    allow_empty = True
    description = _('string')

    def __init__(self, value=None, visible=True, choices=None):
        if value is None and choices:
            value = choices[0]
        if choices is None:
            choices = []
        if value == '':
            value = ' '
        super(CharField, self).__init__(value, visible)
        self.choices = choices


class NotEmptyCharField(CharField):
    allow_empty = False


class IntegerField(NotEmptyCharField):
    """"""
    description = _('integer')

    def to_python(self, x, label):
        error = ValidationError(self.description,
            '%s: %s.' % (_(label),
                _('invalid literal "%s" for integer') % x))
        try:
            return int(round(self.eval(x, label)))
        except ValueError:
            raise error
        except TypeError:
            raise error


class PositiveIntegerField(IntegerField):
    """"""
    description = _('positive integer')

    def to_python(self, x, label):
        value = super(PositiveIntegerField, self).to_python(x, label)
        if value < 0:
            raise ValidationError(self.description,
            '%s: %s.' % (_(label),
            _('the integer value "%s" is negative, but should be positive') \
            % x))
        return value


class PositiveNonZeroIntegerField(PositiveIntegerField):
    """"""
    description = _('positive, non-zero integer')

    def to_python(self, x, label):
        value = super(PositiveNonZeroIntegerField, self).to_python(x, label)
        if value == 0:
            raise ValidationError(self.description,
                '%s: %s.' % (_(label),
                _('the integer value "%s" is zero, but should be non-zero') \
                % x))
        return value


class DpiField(PositiveNonZeroIntegerField):
    """PIL defines the resolution in two dimensions as a tuple (x, y).
    Phatch ignores this possibility and simplifies by using only one resolution
    """

    description = _('resolution')


class FloatField(Field):
    description = _('float')

    def to_python(self, x, label):
        try:
            return float(self.eval(x, label))
        except ValueError, message:
            raise ValidationError(self.description,
            '%s: %s.' % (_(label),
                _('invalid literal "%s" for float') % x))


class PositiveFloatField(FloatField):
    """"""
    description = _('positive integer')

    def to_python(self, x, label):
        value = super(PositiveFloatField, self).to_python(x, label)
        if value < 0:
            raise ValidationError(self.description,
            '%s: %s.' % (_(label),
            _('the float value "%s" is negative, but should be positive') % x))
        return value


class PositiveNonZeroFloatField(PositiveFloatField):
    """"""

    description = _('positive, non-zero integer')

    def to_python(self, x, label):
        value = super(PositiveNonZeroFloatField, self).to_python(x, label)
        if value == 0:
            raise ValidationError(self.description,
                '%s: %s.' % (_(label),
                _('the float value "%s" is zero, but should be non-zero') \
                % x))
        return value


class BooleanField(Field):
    description = _('boolean')

    def to_string(self, x):
        return ['no', 'yes'][int(x)]

    def to_python(self, x, label):
        if x.lower() in ['1', 'true', 'yes']:
            return True
        if x.lower() in ['0', 'false', 'no']:
            return False
        raise ValidationError(self.description,
            '%s: %s (%s, %s).' % (_(label),
                _('invalid literal "%s" for boolean') % x,
                _('true'), _('false')))


class ChoiceField(NotEmptyCharField):
    description = _('choice')

    def __init__(self, value, choices, **keyw):
        super(ChoiceField, self).__init__(value, **keyw)
        self.choices = choices

    def set_choices(self, choices):
        self.choices = choices
        if not (self.get_as_string() in choices):
            self.set_as_string_dirty(choices[0])


class FolderField(NotEmptyCharField):
    pass


class FileField(NotEmptyCharField):
    extensions = []

    def to_python(self, x, label):
        value = super(FileField, self).to_python(x, label).strip()
        if not value.strip() and self.allow_empty:
            return ''
        ext = os.path.splitext(value)[-1][1:]
        if not self.allow_empty and self.extensions \
                and not (ext.lower() in self.extensions):
            if ext:
                raise ValidationError(self.description,
                '%s: %s.\n\n%s:\n%s.' % (_(label),
                    _('the file extension "%s" is invalid') % ext,
                    USE_EXTENSIONS,
                    ', '.join(self.extensions)))
            else:
                raise ValidationError(self.description,
                '%s: %s.\n%s:\n%s.' % (
                    _(label),
                    _('a filename with a valid extension was expected'),
                    USE_EXTENSIONS,
                    textwrap.fill(', '.join(self.extensions), 70)))
        return value


class EmptyFileField(FileField):
    allow_empty = True


class ReadFileField(TestFieldMixin, FileField):
    """This is a test field to ensure that the file exists.
    It could also have been called the MustExistFileField."""

    def to_python(self, x, label, test=False):
        value = super(ReadFileField, self).to_python(x, label)
        if not value.strip() and self.allow_empty:
            return ''
        if (x == value or not test) and (not system.is_file(value)):
            raise ValidationError(self.description,
            '%s: %s.' % (_(label),
                _('the filename "%s" does not exist') % value))
        return value


class DictionaryReadFileField(ReadFileField):
    dictionary = None

    def init_dictionary(self):
        self.dictionary = {}

    def to_python(self, x, label, test=False):
        if self.dictionary is None:
            self.init_dictionary()
        try:
            x = self.dictionary[x]
        except KeyError:
            pass
        return super(DictionaryReadFileField, self).to_python(x, label, test)


class FontFileField(DictionaryReadFileField):
    extensions = FONT_EXTENSIONS
    allow_empty = True

    def init_dictionary(self):
        from fonts import font_dictionary
        self.dictionary = font_dictionary()


class GeoReadFileField(ReadFileField):
    extensions = GEO_EXTENSIONS
    allow_empty = False


class CsvFileField(FileField):
    extensions = ['csv']
    allow_empty = True


class ImageReadFileField(DictionaryReadFileField):
    extensions = IMAGE_READ_EXTENSIONS


class ImageDictionaryReadFileField(ImageReadFileField):
    icon_size = ICON_SIZE


class ImageDictionaryField(ImageDictionaryReadFileField):
    pass


class FileNameField(NotEmptyCharField):
    """Without extension"""
    pass


class CommandLineField(NotEmptyCharField):

    def __init__(self, *args, **keyw):
        super(CommandLineField, self).__init__(*args, **keyw)
        self.needs_exe = True
        self.needs_in = True
        self.needs_out = True

    def to_python(self, x, label):
        command = super(CommandLineField, self).to_python(x, label)
        #check if exists
        if self.needs_exe:
            exe = name = command.split()[0]
            if not os.path.isfile(exe):
                exe = system.find_exe(exe)
            if exe is None:
                raise self.raise_error_not_found(label, name)
        #check for in file
        if self.needs_in and not RE_FILE_IN.search(command):
            self.raise_error_file(label, 'file_in')
        #check for out file
        if self.needs_out:
            file_out = RE_FILE_OUT.findall(command)
            if not file_out:
                self.raise_error_file(label, 'file_out')
            elif len(file_out) > 1:
                self.raise_error_out_max(label, 'file_out')
        return command

    def raise_error_not_found(self, label, what):
        raise ValidationError(self.description, '%s: %s' % (_(label),
            _('"%s" can not be found.') % what))

    def raise_error_file(self, label, what):
        raise ValidationError(self.description, '%s: %s' % (_(label),
            _('Parameter "%s.*" is missing') % what))

    def raise_error_out_max(self, label):
        raise ValidationError(self.description, '%s: %s' % (_(label),
            _('Maximum one parameter "%s" is allowed')\
                % 'file_out.*'))


class ImageTypeField(ChoiceField):

    def __init__(self, value, **keyw):
        super(ImageTypeField, self).__init__(value, IMAGE_EXTENSIONS, **keyw)

    def fix_string(self, x):
        #ignore translation
        if x and x[0] == '.':
            x = x[1:]
        return super(ImageTypeField, self).fix_string(x)


class ImageReadTypeField(ChoiceField):

    def __init__(self, value, **keyw):
        super(ImageReadTypeField, self).__init__(\
            value, IMAGE_READ_EXTENSIONS, **keyw)


class ImageWriteTypeField(ChoiceField):

    def __init__(self, value, **keyw):
        super(ImageWriteTypeField, self).__init__(\
            value, IMAGE_WRITE_EXTENSIONS, **keyw)


class ImageModeField(ChoiceField):

    def __init__(self, value, **keyw):
        super(ImageModeField, self).__init__(value, IMAGE_MODES, **keyw)

    def to_python(self, x, label):
        return x.split(' ')[0].replace('Grayscale', 'L')\
            .replace('Monochrome', '1')


class ImageEffectField(PilConstantMixin, ChoiceField):

    def __init__(self, value, **keyw):
        super(ImageEffectField, self).__init__(\
            value, IMAGE_EFFECTS, **keyw)


class ImageFilterField(PilConstantMixin, ChoiceField):

    def __init__(self, value, **keyw):
        super(ImageFilterField, self).__init__(\
            value, IMAGE_FILTERS, **keyw)


class ImageResampleField(PilConstantMixin, ChoiceField):

    def __init__(self, value, **keyw):
        super(ImageResampleField, self).__init__(\
            value, IMAGE_RESAMPLE_FILTERS, **keyw)


class ImageResampleAutoField(PilConstantMixin, ChoiceField):

    def __init__(self, value, **keyw):
        super(ImageResampleAutoField, self).__init__(\
            value, IMAGE_RESAMPLE_FILTERS + [_t('automatic')], **keyw)


class ImageTransposeField(PilConstantMixin, ChoiceField):

    def __init__(self, value, **keyw):
        super(ImageTransposeField, self).__init__(\
            value, IMAGE_TRANSPOSE + [_t('Orientation')], **keyw)


class OptionalTransposeField(PilConstantMixin, ChoiceField):

    def __init__(self, value, **keyw):
        super(OptionalTransposeField, self).__init__(\
            value, [_t('None')] + IMAGE_TRANSPOSE, **keyw)


class OrientationField(PilConstantMixin, ChoiceField):

    def __init__(self, value, **keyw):
        super(OrientationField, self).__init__(\
            value, ORIENTATION, **keyw)

    def to_python(self, x, label):
        if x == _t('Normal'):
            return None
        return super(OrientationField, self).to_python(x, label)


class AlignHorizontalField(ChoiceField):

    def __init__(self, value, **keyw):
        super(AlignHorizontalField, self).__init__(\
            value, ALIGN_HORIZONTAL, **keyw)


class AlignVerticalField(ChoiceField):

    def __init__(self, value, **keyw):
        super(AlignVerticalField, self).__init__(\
            value, ALIGN_VERTICAL, **keyw)


class RankSizeField(IntegerField, ChoiceField):

    def __init__(self, value, **keyw):
        super(RankSizeField, self).__init__(\
            value, RANK_SIZES, **keyw)


class PixelField(IntegerField):
    """Can be pixels, cm, inch, %."""

    def get_size(self, info, base, dpi, label, value_as_string=None):
        if value_as_string is None:
            value_as_string = self.value_as_string
        for unit, value in self._units(base, dpi).items():
            value_as_string = value_as_string.replace(unit, value)
        return super(PixelField, self).get(info, label, value_as_string)

    def _units(self, base, dpi):
        return {
            'cm': '*%f' % (dpi / 2.54),
            'mm': '*%f' % (dpi / 25.4),
            'inch': '*%f' % dpi,
            '%': '*%f' % (base / 100.0),
            'px': '',
        }


class FileSizeField(IntegerField):
    """Can be in bytes (``bt``), kilo bytes (``kb``), mega bytes (``mb``),
    or giga bytes (``gb``).

    >>> FileSizeField('5kb').get()
    5120
    >>> FileSizeField('5mb').get()
    5242880
    """
    _units = {'kb': '*1024', 'gb': '*1073741824', 'mb': '*1048576', 'bt': ''}

    def to_python(self, x, label):
        for unit, value in self._units.items():
            x = x.replace(unit, value)
        return super(FileSizeField, self).to_python(x, label)


class SliderField(IntegerField):
    """A value with boundaries set by a slider."""

    def __init__(self, value, minValue, maxValue, **keyw):
        super(SliderField, self).__init__(value, **keyw)
        self.min = minValue
        self.max = maxValue


class FloatSliderField(FloatField, SliderField):
    """A value with boundaries set by a slider."""


class TiffCompressionField(ChoiceField):

    def __init__(self, value, **keyw):
        super(TiffCompressionField, self).__init__(value,
            TIFF_COMPRESSIONS, **keyw)


class ExifItpcField(NotEmptyCharField):

    def fix_string(self, x):
        #ignore translation
        if x and x[0] == '<' and x[-1] == '>':
            x = x[1:-1]
        return super(ExifItpcField, self).fix_string(x)

    def to_python(self, x, label):
        if not(x[:5] in ('Exif_', 'Iptc_')):
            raise ValidationError(self.description,
                _('Tag should start with "Exif_" or "Iptc_"'),
                USE_INSPECTOR)
        return super(ExifItpcField, self).to_python(str(x), label)


class ColorField(Field):

    pass

#todo
##class CommaSeparatedIntegerField(CharField):
##    """Not implemented yet."""
##    pass
##
##class DateField(Field):
##    """Not implemented yet."""
##    pass
##
##class DateTimeField(DateField):
##    """Not implemented yet."""
##    pass
##
##class EmailField(CharField):
##    """Not implemented yet."""
##    pass
##
##class UrlField(CharField):
##    """Not implemented yet."""
##    pass

#Give Form all the tools
FIELDS = [(name, cls) for name, cls in locals().items()
    if name[0] != '_' and \
    ((type(cls) == types.TypeType and issubclass(cls, Field)) or\
    type(cls) in [types.StringType, types.UnicodeType, types.ListType,
    types.TupleType])]

for _name, _Field in FIELDS:
    setattr(Form, _name, _Field)
