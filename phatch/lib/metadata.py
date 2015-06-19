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
# Phatch recommends SPE (http://pythonide.stani.be) for python editing.

# Follows PEP8


# import rpdb2; rpdb2.start_embedded_debugger('x')

#TODO: PROVIDE THESE AS EXTRACT METHOD, exif rotation
#synchronize between exif automatically? pil manual
#sphinx doc everything

import datetime
import os
import re
import time

try:
    import pyexiv2
    import _pyexiv2
except ImportError:
    pyexiv2 = None
    _pyexiv2 = None

import imtools
import odict
import unicoding
from desktop import DESKTOP_FOLDER
from metadataTest import DateTime, INFO_TEST, is_string, MONTHS, now, WEEKDAYS
from reverse_translation import _t

RE_VAR = re.compile('<.+?>')


DATETIME_KEYS = ['year', 'month', 'day', 'hour', 'minute', 'second']
RE_DATETIME_KEYS = re.compile('(%s)$' % ('|'.join(['[.]' + key
    for key in DATETIME_KEYS])))

RE_PYEXIV2_TAG = re.compile('^(Exif|Iptc)_.+')
RE_PYEXIV2_TAG_EDITABLE = re.compile('^(Exif|Iptc)_\w+$')

ORIENTATION_TAGS = ['orientation', 'Pexif_Orientation', 'Zexif_Orientation']
WRITABLE_TAGS = ['dpi', 'transparency'] + ORIENTATION_TAGS


def is_editable_tag(tag):
    if RE_PYEXIV2_TAG_EDITABLE.match(tag):
        value = INFO_TEST.get(tag, 1)
        return type(value) in (str, unicode, int, float) \
            or isinstance(value, DateTime)
    return False


def is_writable_tag(tag):
    return tag in WRITABLE_TAGS or \
        (RE_PYEXIV2_TAG_EDITABLE.match(tag) and not(tag in (
            'Exif_Photo_PixelXDimension',
            'Exif_Photo_PixelYDimension',
            'Exif_Image_Software')))


def is_writeable_not_exif_tag(tag, mode):
    return tag in ('dpi', 'orientation') \
        or (mode == 'P' and tag == 'transparency')


RE_DATETIME_COLON = \
re.compile('[0-9]{4,4}:[0-9]{2,2}:[0-9]{2,2} [0-9]{2,2}:[0-9]{2,2}:[0-9]{2,2}')


class InfoProvideError(Exception):
    """When the variable can't be provided by the current info
    instances.
    """
    pass


# Keep this outside _InfoCache to avoid self reference
def _update_static_source(self):
    """Update static cache does not do anything. This is just
    a dummy function which can be assigned to
    :method:``_update_source`` if the source is not callable."""
    pass


def _update_callable_source(self):
    """Update dynamic cache updates ``self._source`` with
    ``self._get_source_dynamic``. This can be assigned to
    :method:``_update_source`` if the source is callable.

    .. see also: :method:`_set_source`
    """
    self._set_source(self._get_source_dynamic())


class _InfoCache(object):

    def __init__(self, source=None, vars=None):
        """Creates a cached info. The base is the source from which
        all variables are extracted on demand. When all variables
        have to be extracted use the :method:``extract_all`` method.
        The source can be a static object or a callable for cases
        where the object is manipulated and the variables remain
        valid (e.g. when resizing an image the mode stays valid)

        The difference between ``get`` and ``extract`` is that ``get``
        returns a value, while ``extract`` extracts it and places it in
        ``dict``. ``extract`` allows for multiple, related values to
        be extracted simultaneously.

        ``__getitem__``is installed by :method:`enable_cache` or
        :method:`disable_cache`

        :param source: retrieve source from which to extract data
        :type source: object or callable
        """
        if not (source is None):
            if is_string(source):
                source = self.get_source_from_file(source)
            self.set_source(source)
        else:
            self.dict = self.empty_dict.copy()
        self.set_vars(vars)

    def _set_extract_methods(self):
        """To be overwritten if the info has preknown variables."""
        self._extract_methods = {}

    def dump(self, source=None):
        if source:
            self.set_source(source)
        self.extract_vars()
        return self.dict.copy()

    @classmethod
    def provides(cls, var):
        """Wether this info (might) provide the ``var`` variable.

        :returns: if this info should handle this variable
        :rtype: bool
        """
        return var in cls.possible_vars or var[:cls._prefix_n] == cls.prefix

    def set_source(self, source):
        """Sets the source of this info. This allows reuse of the same
        info if needed.

        :param source: retrieve source from which to extract data
        :type source: object or callable

        .. see also: :method:`_set_source`
        """
        if is_string(source):
            #source is a filename
            source = self.get_source_from_file(source)
        if callable(source):
            self._get_source_dynamic = source
            self._update_source = _update_callable_source
            source = None
        else:
            self._get_source_dynamic = None
            self._update_source = _update_static_source
        self._set_source(source)
        self.disable_cache()
        self.dict = self.empty_dict.copy()

    def _set_source(self, source):
        """Sets the source at the lowest level. Helper method for
        :method:`set_source` and :method:`_update_callable_source`.

        :param source: retrieve source from which to extract data
        :type source: object or callable
        """
        self._source = source

    def set_vars(self, vars):
        self.vars = vars

    def enable_cache(self):
        """Enable the static cache so that the expensive
        :method:``_get_source_dynamic`` does not get called for
        every var access.

        This makes only sense for callable sources.
        """
        self._update_source(self)
        type(self).__getitem__ = type(self)._get_var_from_source_without_update

    def disable_cache(self):
        """Turn off static caching.

        This makes only sense for callable sources.
        """
        type(self).__getitem__ = type(self)._get_var_from_source_with_update

    def _get_var_from_source_with_update(self, var):
        """If the variable ``var`` is not present in the ``dict``,
        this method updates the ``source`` first and afterwards
        extracts the variable ``var`` from source.

        :param var: variable
        :type var: string
        """
        try:
            return self.dict[var]
        except KeyError:
            self._update_source(self)
            return self._get_var_from_source(var)

    def _get_var_from_source_without_update(self, var):
        """If the variable ``var`` is not present in the ``dict``,
        this extracts the variable ``var`` from source without updating
        the ``source`` (as it is static).

        :param var: variable
        :type var: string
        """
        try:
            return self.dict[var]
        except KeyError:
            return self._get_var_from_source(var)

    def _get_var_from_source(self, var):
        """

        :param var: variable
        :type var: string
        """
        self._extract_var_with_method_or_other(var)
        return self.dict[var]

    def _extract_var_with_method_or_other(self, var):
        """Extract var and store it in a dictionary.

        :param var: variable
        :type var: string
        """
        if var in self._extract_methods:
            self._extract_methods[var](self)
        else:
            self._extract_other_method(var)

    def _extract_other_method(self, var):
        """Extract only one var"""
        if var[:self._prefix_n] == self.prefix:
            self.dict[var] = self._get_other(var[self._prefix_n:])
        else:
            raise KeyError(var)

    def _extract_other(self, var):
        """Extract only one other ``var`` into ``dict``. This raises a
        ``KeyError`` by default. Helper function for
        :method:`_extract_other_method`. (to be overwritten)

        :param var: variable
        :type var: string
        """
        raise KeyError(self.prefix + var)

    def _extract_others(self):
        """Extract all other vars. Does nothing by default.
        (to be overwritten)"""

    def extract_vars(self, vars=None):
        if vars is None:
            vars = self.vars
        self.enable_cache()
        for var in self.vars:
            self[var]
        self.disable_cache()

    def extract_all(self):
        """Extract all values, which is usefull for inspector."""
        for var, extract in self._extract_methods.items():
            if not(var in self.dict):
                extract(self)
        self._extract_others()

    @classmethod
    def load_module(cls):
        """Load module lazily on demand and redirect
        :method:`get_source_from_file`
        from :method:`_get_source_from_file_and_module` to
        :method:`_get_source_from_file`.
        """
        cls._load_module()
        cls.get_source_from_file = cls._get_source_from_file

    def load_filename(self, filename):
        """Load source from filename.

        :param filename: filename of the source file
        :type filename: string
        """
        self.set_source(self.get_source_from_file(filename))

    def _get_source_from_file_and_module(self, filename):
        """Loads module and get source from file. Normally this is only
        called the first time as :method:`get_source_from_file`. Afterwards
        :method:`_get_source_from_file` is called.

        :param filename: filename of the source file
        :type filename: string

        .. see also:: :method:`load_module`
        """
        self.load_module()
        return self._get_source_from_file(filename)

    @classmethod
    def _load_module(cls):
        """Code to load the dependent module. (To be overwritten.)"""

    def _get_source_from_file(self, filename):
        """If the source can be loaded from a file, specify the load
        method here. (To be overwritten.)

        :param filename: filename of the source file
        :type filename: string
        """
        return filename

    @classmethod
    def needs_orientation(cls, vars):
        """Whether this info needs orientation"""
        return False

    get_source_from_file = _get_source_from_file_and_module
    empty_dict = {}

    type = 'cache'
    _extract_methods = {}

    prefix = type + '_'
    _prefix_n = len(prefix)
    possible_vars = sorted(_extract_methods.keys())


class UnknownTypeError(Exception):
    pass


class InfoFile(_InfoCache):
    """Wraps a lazy file path access around an image filename.

    >>> info = InfoFile('/home/phatch/test.png')
    >>> info['foldername']
    u'phatch'
    >>> sorted(info.dict.keys())
    ['foldername', 'root']
    >>> info['type']
    u'png'
    >>> sorted(info.dict.keys())
    ['filename', 'foldername', 'root', 'type']
    >>> info.set_source('/home/gimp/world.jpg')
    >>> info['type']
    u'jpg'
    >>> sorted(info.dict.keys())
    ['filename', 'type']
    """

    def _set_source(self, source):
        if is_string(source):
            self._source_path = source
            self._source_parent = os.path.dirname(self._source_path)
        else:
            self._source_path, self._source_parent = source
        self._source_path = unicoding.ensure_unicode(self._source_path)
        self._source_parent = unicoding.ensure_unicode(self._source_parent)
        self._source_parent = self._source_parent.rstrip(os.path.sep)

    def _extract_path(self):
        """Extracts the full path from the source."""
        self.dict['path'] = self._source_path

    def _extract_folder(self):
        """Extracts the parent folder from the source."""
        self.dict['folder'] = self._source_parent

    def _extract_root(self):
        """Extracts the root folder from the source. The root folder
        is the parent of the parent folder."""
        self.dict['root'], self.dict['foldername'] = \
            os.path.split(self._source_parent)

    def _extract_filename(self):
        """Extracts the filename (without type) and type from the source."""
        filename = os.path.basename(self._source_path)
        self.dict['filename'], typ = \
            os.path.splitext(filename)
        self.dict['type'] = typ[1:]

    def _extract_stat(self):
        """Extracts the file size and date information from the source."""
        try:
            file_stat = os.stat(self._source_path)
            self.dict['filesize'] = file_stat.st_size
            st_mtime = time.localtime(file_stat.st_mtime)[:7]
        except:
            self.dict['filesize'] = 0
            st_mtime = (0, ) * 7
        self.dict['year'], self.dict['month'], self.dict['day'], \
            self.dict['hour'], self.dict['minute'], self.dict['second'], \
            self.dict['weekday'] = st_mtime
        self.dict['weekdayname'] = WEEKDAYS[self.dict['weekday']]
        self.dict['monthname'] = MONTHS[self.dict['month'] - 1]

    def _extract_subfolder(self):
        """Extracts the ``subfolder`` from the source. ``subfolder`` is the
        child folder from ``folder``.
        """
        self.dict['subfolder'] = \
            os.path.dirname(self._source_path)[len(self._source_parent) + 1:]

    def _extract_desktop(self):
        self.dict['desktop'] = DESKTOP_FOLDER

    @classmethod
    def split_vars(cls, vars):
        vars = set(vars)
        #known, unknown
        return (vars.intersection(cls.possible_vars),
            vars.difference(cls.possible_vars))

    type = 'File'
    _extract_methods = {
        _t('day'): _extract_stat,
        _t('desktop'): _extract_desktop,
        _t('foldername'): _extract_root,
        _t('filename'): _extract_filename,
        _t('filesize'): _extract_stat,
        _t('folder'): _extract_folder,
        _t('hour'): _extract_stat,
        _t('minute'): _extract_stat,
        _t('month'): _extract_stat,
        _t('monthname'): _extract_stat,
        _t('path'): _extract_path,
        _t('root'): _extract_root,
        _t('second'): _extract_stat,
        _t('subfolder'): _extract_subfolder,
        _t('type'): _extract_filename,
        _t('weekday'): _extract_stat,
        _t('weekdayname'): _extract_stat,
        _t('year'): _extract_stat,
        }

    prefix = type + '_'
    _prefix_n = len(prefix)
    possible_vars = sorted(_extract_methods.keys())


class _InfoPil(_InfoCache):

    @classmethod
    def _load_module(cls):
        """Code to load the PIL Image module."""
        try:
            import openImage
            cls.Image = openImage
        except ImportError:
            import Image
            cls.Image = Image

    @classmethod
    def _get_source_from_file(cls, filename):
        """Load the PIL source from a file.

        :param filename: filename of the source file
        :type filename: string
        """
        return cls.Image.open(filename)


class InfoPil(_InfoPil):
    """Wraps a lazy PIL var access to an image.

    :param image: Pil.Image or callable to retrieve it
    :type image: Pil.Image/function

    >>> import pprint
    >>> import Image
    >>> image = Image.new('L',(1,2))
    >>> info = InfoPil(image)
    >>> info['format']
    >>> info.provides('formatdescription')
    True
    >>> pprint.pprint(info.possible_vars)
    ['aspect',
     'compression',
     'dpi',
     'format',
     'formatdescription',
     'gamma',
     'height',
     'interlace',
     'mode',
     'size',
     'transparency',
     'width']
    >>> sorted(info.dict.keys())
    ['format', 'orientation']
    >>> info['mode']
    'L'
    >>> info['height']
    2
    >>> info['format']
    >>> info['dpi']
    72
    >>> sorted(info.dict.keys())
    ['dpi', 'format', 'height', 'mode', 'orientation', 'size', 'width']
    >>> info.reset_geometry()
    >>> sorted(info.dict.keys())
    ['dpi', 'format', 'mode', 'orientation']
    >>> info.extract_all()
    >>> pprint.pprint(sorted(info.dict.keys()))
    ['aspect',
     'compression',
     'dpi',
     'format',
     'formatdescription',
     'gamma',
     'height',
     'interlace',
     'mode',
     'orientation',
     'size',
     'transparency',
     'width']
    """

    def _extract_aspect(self):
        self.dict['aspect'] = self._source.info.get('aspect', None)

    def _extract_compression(self):
        self.dict['compression'] = \
            self._source.info.get('compression', 'none')

    def _extract_dpi(self):
        self.dict['dpi'] = \
            self._source.info.get('dpi', (72, ))[0]

    def _extract_format(self):
        self.dict['format'] = self._source.format

    def _extract_formatdescription(self):
        self.dict['formatdescription'] = \
            self._source.format_description

    def _extract_gamma(self):
        self.dict['gamma'] = self._source.info.get('gamma', None)

    def _extract_interlace(self):
        self.dict['interlace'] = \
            self._source.info.get('interlace', None)

    def _extract_mode(self):
        self.dict['mode'] = self._source.mode

    def _extract_size(self):
        """Extract size of image with PIL"""
        #we don't translate dotted attributes
        size = self._source.size
        if self.dict['orientation'] > 4:
            size = (size[1], size[0])
        self.dict['width'], self.dict['height'] = \
            self.dict['size'] = size

    def _extract_transparency(self):
        self.dict['transparency'] = \
            self._source.info.get('transparency', None)

    def _get_other(self, var):
        """Get only one variable which is not defined in
        :method:`_extract_methods`.

        :param var: name of the variable
        :type var: string
        """
        try:
            return self._source.info[var]
        except KeyError:
            raise KeyError(self.prefix + var)

    def _extract_others(self):
        """Extract all other possible vars"""
        for key, value in self._source.info.items():
            if not(key in self.vars_skip):
                self.dict[self.prefix + key] = value

    def reset_geometry(self):
        for var in ('width', 'height', 'size'):
            if var in self.dict:
                del self.dict[var]

    def set_orientation(self, orientation):
        self.dict['orientation'] = orientation
        self.reset_geometry()

    @classmethod
    def needs_orientation(cls, vars):
        """InfoPil always needs to know the orientation.

        :returns: True
        :rtype: bool
        """
        return True

    read_only = ('aspect', 'dpi', 'gamma', 'interlace', 'transparency')
    empty_dict = {'orientation': 1}
    type = 'Pil'
    _extract_methods = {
        _t('aspect'): _extract_aspect,
        _t('compression'): _extract_compression,
        _t('dpi'): _extract_dpi,
        _t('gamma'): _extract_gamma,
        _t('height'): _extract_size,
        _t('interlace'): _extract_interlace,
        _t('mode'): _extract_mode,
        _t('width'): _extract_size,
        _t('format'): _extract_format,
        _t('formatdescription'): _extract_formatdescription,
        _t('size'): _extract_size,
        _t('transparency'): _extract_transparency}

    prefix = type + '_'
    _prefix_n = len(prefix)
    possible_vars = sorted(_extract_methods.keys())
    vars_skip = possible_vars + ['exif']  # skip for writing png metadata

#Initialize PIL metadata
#This can't be lazily loaded as it is needed by the provide method.
try:
    from ExifTags import TAGS, GPSTAGS
    EXIFTAGS = {}
    EXIFTAGS.update(TAGS)
    EXIFTAGS.update(GPSTAGS)
    del TAGS
    del GPSTAGS
except:
    #older versions of PIL
    EXIFTAGS = {'Orientation': 'Orientation'}
EXIFTAGS_REVERSE = {}
for key, item in EXIFTAGS.items():
    EXIFTAGS_REVERSE[item] = key


def convert_from_string(value):
    """If value is recongized as a datetime string, convert value
    into :class:`DateTime` instance.

    :param value: any value
    :type value: string
    :returns: same value or converted in date
    :rtype: string/:class:`DateTime`
    """
    if is_string(value) and RE_DATETIME_COLON.match(value):
        return DateTime(value)
    return value


class _InfoPilMetadata(_InfoPil):

    def _extract_orientation(self):
        """Extract orientation from source image as integer."""
        self.dict['orientation'] = self._source.get(self.orientation, 1)

    def _set_source(self, source):
        """Sets the source at the lowest level. Helper method for
        :method:`set_source` and :method:`_update_callable_source`.

        :param source: retrieve source from which to extract data
        :type source: object or callable
        """
        try:
            self._source = source._getexif()
        except:
            self._source = {}
            return
        if not self._source:
            self._source = {}

    orientation = EXIFTAGS_REVERSE['Orientation']
    _extract_methods = {
        _t('orientation'): _extract_orientation}

    possible_vars = sorted(_extract_methods.keys())


class InfoPexif(_InfoPilMetadata):
    """Wraps a lazy PIL exif var access to an image.

    >>> import pprint
    >>> filename = '../tests/input/exĩf ïptç.jpg'
    >>> info = InfoPexif(filename)
    >>> info['orientation']
    8
    >>> info['Pexif_DateTimeOriginal']
    DateTime('2010:03:03 11:03:08')
    >>> pprint.pprint(info.dict.keys())
    ['Pexif_DateTimeOriginal', 'orientation']
    >>> import Image
    >>> image = Image.open(filename)
    >>> info = InfoPexif(image)
    >>> info['Pexif_DateTimeOriginal']
    DateTime('2010:03:03 11:03:08')
    >>> pprint.pprint(info.dict.keys())
    ['Pexif_DateTimeOriginal']
    >>> info.extract_all()
    >>> info['Pexif_DateTimeOriginal']
    DateTime('2010:03:03 11:03:08')
    >>> pprint.pprint(info.dict.keys())
    ['orientation',
     'Pexif_Make',
     'Pexif_Flash',
     'Pexif_YResolution',
     'Pexif_DateTimeDigitized',
     'Pexif_ExifImageWidth',
     'Pexif_FocalPlaneYResolution',
     'Pexif_MaxApertureValue',
     'Pexif_MeteringMode',
     'Pexif_ExifVersion',
     'Pexif_MakerNote',
     'Pexif_FNumber',
     'Pexif_FocalPlaneResolutionUnit',
     'Pexif_SensingMethod',
     'Pexif_Orientation',
     'Pexif_FocalLength',
     'Pexif_XResolution',
     'Pexif_ExifOffset',
     'Pexif_FileSource',
     'Pexif_CompressedBitsPerPixel',
     'Pexif_ExifImageHeight',
     'Pexif_ResolutionUnit',
     'Pexif_ExifInteroperabilityOffset',
     'Pexif_ApertureValue',
     'Pexif_ExposureTime',
     'Pexif_ColorSpace',
     'Pexif_YCbCrPositioning',
     'Pexif_Model',
     'Pexif_DateTime',
     'Pexif_ComponentsConfiguration',
     'Pexif_FlashPixVersion',
     'Pexif_FocalPlaneXResolution',
     'Pexif_DateTimeOriginal',
     'Pexif_UserComment']
    """

    @classmethod
    def provides(cls, var):
        return var == 'orientation' or \
            (var[:cls._prefix_n] == cls.prefix and
            var[cls._prefix_n:] in EXIFTAGS_REVERSE)

    def _get_other(self, var):
        """Get only one variable which is not defined in
        :method:`_extract_methods`.

        :param var: name of the variable
        :type var: string
        """
        try:
            key = EXIFTAGS_REVERSE[var]
        except KeyError:
            # re raise: give full name to key error
            raise KeyError(self.prefix + var)
        return convert_from_string(self._source[key])

    def _extract_others(self):
        """Extract all other possible vars"""
        for key, value in self._source.items():
            if key in EXIFTAGS:
                self.dict['Pexif_' + EXIFTAGS[key]] = \
                    convert_from_string(value)

    type = 'Pexif'

    prefix = type + '_'
    _prefix_n = len(prefix)


class InfoZexif(_InfoPilMetadata):
    """Wraps a lazy PIL exif var access to an image.

    >>> import pprint
    >>> filename = '../tests/input/exĩf ïptç.jpg'
    >>> info = InfoZexif(filename)
    >>> info['Zexif_0x9202']
    (128, 32)
    >>> import Image
    >>> image = Image.open(filename)
    >>> info = InfoZexif(image)
    >>> info['Zexif_0x9202']
    (128, 32)
    >>> pprint.pprint(info.dict.keys())
    ['Zexif_0x9202']
    >>> info.extract_all()
    >>> pprint.pprint(info.dict.keys())
    ['Zexif_0x9202',
     'Zexif_0x0128',
     'orientation',
     'Zexif_0x9205',
     'Zexif_0x9101',
     'Zexif_0xa001',
     'Zexif_0xa002',
     'Zexif_0x9209',
     'Zexif_0xa20f',
     'Zexif_0xa005',
     'Zexif_0xa20e',
     'Zexif_0x9000',
     'Zexif_0xa217',
     'Zexif_0x9003',
     'Zexif_0x9004',
     'Zexif_0xa210',
     'Zexif_0x011b',
     'Zexif_0x9286',
     'Zexif_0x9207',
     'Zexif_0x829d',
     'Zexif_0x829a',
     'Zexif_0xa404',
     'Zexif_0xa406',
     'Zexif_0xa401',
     'Zexif_0xa402',
     'Zexif_0xa403',
     'Zexif_0xa000',
     'Zexif_0x9102',
     'Zexif_0x0110',
     'Zexif_0x0112',
     'Zexif_0x0132',
     'Zexif_0x920a',
     'Zexif_0x8769',
     'Zexif_0x010f',
     'Zexif_0x927c',
     'Zexif_0xa300',
     'Zexif_0x0213',
     'Zexif_0x011a',
     'Zexif_0xa003']
    """

    @classmethod
    def provides(cls, var):
        return var == 'orientation' or \
            (var[:cls._prefix_n] == cls.prefix and
            cls.regex.match(var[cls._prefix_n:]))

    def _get_other(self, var):
        """Get only one variable which is not defined in
        :method:`_extract_methods`.

        :param var: name of the variable
        :type var: string
        """
        return convert_from_string(self._source[eval(var)])

    def _extract_others(self):
        """Extract all other vars"""
        for key, value in self._source.items():
            self.dict['Zexif_0x%04x' % key] = convert_from_string(value)

    type = 'Zexif'
    regex = re.compile('0x[a-f0-9]{4,4}')

    prefix = type + '_'
    _prefix_n = len(prefix)


class _InfoPyexiv2(_InfoCache):

    @classmethod
    def provides(cls, var):
        return cls.regex.search(var)

    def convert(self, value):
        if value.__class__ == datetime.datetime:
            value = DateTime(value)
        return value

    def _get_other(self, var):
        """Get only one variable which is not defined in
        :method:`_extract_methods`.

        :param var: name of the variable
        :type var: string
        """
        return self.convert(self._source['%s.%s' \
            % (self.type, var.replace('_', '.'))])

    def _extract_others_from_keys(self, exif_keys):
        """Extract all other vars"""
        for var in exif_keys:
            _var = var.replace('.', '_')
            if not(_var in self.dict):
                try:
                    value = self._source[var]
                except:
                    continue
                self.dict[_var] = self.convert(value)

    @classmethod
    def _load_module(cls):
        """Code to load the pyexiv2 module."""
        import pyexiv2
        import _pyexiv2
        cls.pyexiv2 = pyexiv2
        cls._pyexiv2 = _pyexiv2

    @classmethod
    def _get_source_from_file(cls, filename, all=False):
        """Load the pyexiv2 source from a file.

        :param filename: filename of the source file
        :type filename: string
        :param all: cache all tags
        :type all: bool
        """
        format = imtools.get_format(os.path.splitext(filename)[-1][1:])
        if cls._pyexiv2.is_readable_format(format):
            source = cls.pyexiv2.Image(filename)
            source.readMetadata()
            if all:
                source.cacheAllExifTags()
                source.cacheAllIptcTags()
            return source
        else:
            return {}


class InfoExif(_InfoPyexiv2):
    """
    >>> import pprint
    >>> filename = '../tests/input/exĩf ïptç.jpg'
    >>> info = InfoExif(filename)
    >>> info['Exif_Image_DateTime']
    DateTime('2010:03:03 11:03:08')
    >>> import pyexiv2
    >>> exif = pyexiv2.Image(filename)
    >>> exif.readMetadata()
    >>> info = InfoExif(exif)
    >>> info['Exif_Image_DateTime']
    DateTime('2010:03:03 11:03:08')
    >>> print info['Exif_Image_DateTime']
    2010:03:03 11:03:08
    >>> info['Exif_Image_Orientation']
    8
    >>> info['Exif_Photo_MaxApertureValue'].__class__ == pyexiv2.Rational
    True
    >>> print info['Exif_Photo_MaxApertureValue']
    128/32
    >>> info.extract_all()
    >>> pprint.pprint(sorted(info.dict.keys()))
    ['Exif_CanonCs_0x0000',
     'Exif_CanonCs_0x0006',
     'Exif_CanonCs_0x0008',
     'Exif_CanonCs_0x0009',
     'Exif_CanonCs_0x0015',
     'Exif_CanonCs_0x001e',
     'Exif_CanonCs_0x001f',
     'Exif_CanonCs_0x0026',
     'Exif_CanonCs_0x0027',
     'Exif_CanonCs_0x0029',
     'Exif_CanonCs_0x002b',
     'Exif_CanonCs_0x002c',
     'Exif_CanonCs_0x002d',
     'Exif_CanonCs_AESetting',
     'Exif_CanonCs_AFPoint',
     'Exif_CanonCs_ColorTone',
     'Exif_CanonCs_Contrast',
     'Exif_CanonCs_DigitalZoom',
     'Exif_CanonCs_DisplayAperture',
     'Exif_CanonCs_DriveMode',
     'Exif_CanonCs_EasyMode',
     'Exif_CanonCs_ExposureProgram',
     'Exif_CanonCs_FlashActivity',
     'Exif_CanonCs_FlashDetails',
     'Exif_CanonCs_FlashMode',
     'Exif_CanonCs_FocusContinuous',
     'Exif_CanonCs_FocusMode',
     'Exif_CanonCs_FocusType',
     'Exif_CanonCs_ISOSpeed',
     'Exif_CanonCs_ImageSize',
     'Exif_CanonCs_ImageStabilization',
     'Exif_CanonCs_Lens',
     'Exif_CanonCs_LensType',
     'Exif_CanonCs_Macro',
     'Exif_CanonCs_MaxAperture',
     'Exif_CanonCs_MeteringMode',
     'Exif_CanonCs_MinAperture',
     'Exif_CanonCs_PhotoEffect',
     'Exif_CanonCs_Quality',
     'Exif_CanonCs_Saturation',
     'Exif_CanonCs_Selftimer',
     'Exif_CanonCs_Sharpness',
     'Exif_CanonCs_ZoomSourceWidth',
     'Exif_CanonCs_ZoomTargetWidth',
     'Exif_CanonSi_0x0000',
     'Exif_CanonSi_0x0001',
     'Exif_CanonSi_0x0003',
     'Exif_CanonSi_0x0006',
     'Exif_CanonSi_0x0008',
     'Exif_CanonSi_0x000a',
     'Exif_CanonSi_0x000b',
     'Exif_CanonSi_0x000c',
     'Exif_CanonSi_0x000d',
     'Exif_CanonSi_0x0010',
     'Exif_CanonSi_0x0011',
     'Exif_CanonSi_0x0012',
     'Exif_CanonSi_0x0014',
     'Exif_CanonSi_0x0017',
     'Exif_CanonSi_0x0018',
     'Exif_CanonSi_0x0019',
     'Exif_CanonSi_0x001a',
     'Exif_CanonSi_0x001b',
     'Exif_CanonSi_0x001c',
     'Exif_CanonSi_0x001d',
     'Exif_CanonSi_0x001e',
     'Exif_CanonSi_0x001f',
     'Exif_CanonSi_0x0020',
     'Exif_CanonSi_0x0021',
     'Exif_CanonSi_AFPointUsed',
     'Exif_CanonSi_ApertureValue',
     'Exif_CanonSi_FlashBias',
     'Exif_CanonSi_ISOSpeed',
     'Exif_CanonSi_Sequence',
     'Exif_CanonSi_ShutterSpeedValue',
     'Exif_CanonSi_SubjectDistance',
     'Exif_CanonSi_TargetAperture',
     'Exif_CanonSi_TargetShutterSpeed',
     'Exif_CanonSi_WhiteBalance',
     'Exif_Canon_0x0000',
     'Exif_Canon_0x0003',
     'Exif_Canon_0x000d',
     'Exif_Canon_0x0013',
     'Exif_Canon_0x0018',
     'Exif_Canon_0x0019',
     'Exif_Canon_0x001c',
     'Exif_Canon_0x001d',
     'Exif_Canon_0x001e',
     'Exif_Canon_0x001f',
     'Exif_Canon_0x0022',
     'Exif_Canon_0x0023',
     'Exif_Canon_0x0024',
     'Exif_Canon_0x0025',
     'Exif_Canon_0x0026',
     'Exif_Canon_0x0027',
     'Exif_Canon_0x0028',
     'Exif_Canon_FirmwareVersion',
     'Exif_Canon_FocalLength',
     'Exif_Canon_ImageNumber',
     'Exif_Canon_ImageType',
     'Exif_Canon_ModelID',
     'Exif_Canon_OwnerName',
     'Exif_Image_DateTime',
     'Exif_Image_ExifTag',
     'Exif_Image_Make',
     'Exif_Image_Model',
     'Exif_Image_Orientation',
     'Exif_Image_ResolutionUnit',
     'Exif_Image_XResolution',
     'Exif_Image_YCbCrPositioning',
     'Exif_Image_YResolution',
     'Exif_Iop_InteroperabilityIndex',
     'Exif_Iop_InteroperabilityVersion',
     'Exif_Iop_RelatedImageLength',
     'Exif_Iop_RelatedImageWidth',
     'Exif_MakerNote_ByteOrder',
     'Exif_MakerNote_Offset',
     'Exif_Photo_ApertureValue',
     'Exif_Photo_ColorSpace',
     'Exif_Photo_ComponentsConfiguration',
     'Exif_Photo_CompressedBitsPerPixel',
     'Exif_Photo_CustomRendered',
     'Exif_Photo_DateTimeDigitized',
     'Exif_Photo_DateTimeOriginal',
     'Exif_Photo_DigitalZoomRatio',
     'Exif_Photo_ExifVersion',
     'Exif_Photo_ExposureBiasValue',
     'Exif_Photo_ExposureMode',
     'Exif_Photo_ExposureTime',
     'Exif_Photo_FNumber',
     'Exif_Photo_FileSource',
     'Exif_Photo_Flash',
     'Exif_Photo_FlashpixVersion',
     'Exif_Photo_FocalLength',
     'Exif_Photo_FocalPlaneResolutionUnit',
     'Exif_Photo_FocalPlaneXResolution',
     'Exif_Photo_FocalPlaneYResolution',
     'Exif_Photo_InteroperabilityTag',
     'Exif_Photo_MakerNote',
     'Exif_Photo_MaxApertureValue',
     'Exif_Photo_MeteringMode',
     'Exif_Photo_PixelXDimension',
     'Exif_Photo_PixelYDimension',
     'Exif_Photo_SceneCaptureType',
     'Exif_Photo_SensingMethod',
     'Exif_Photo_ShutterSpeedValue',
     'Exif_Photo_UserComment',
     'Exif_Photo_WhiteBalance',
     'Exif_Thumbnail_Compression',
     'Exif_Thumbnail_JPEGInterchangeFormat',
     'Exif_Thumbnail_JPEGInterchangeFormatLength',
     'Exif_Thumbnail_ResolutionUnit',
     'Exif_Thumbnail_XResolution',
     'Exif_Thumbnail_YResolution',
     'orientation']
    """

    def _extract_orientation(self):
        """Extract orientation from source image as integer."""
        try:
            #be careful to use dots here instead of _
            self.dict['orientation'] = self._source['Exif.Image.Orientation']
        except KeyError:
            self.dict['orientation'] = 1

    def _extract_others(self):
        """Extract all other vars"""
        self._extract_others_from_keys(self._source.exifKeys())

    regex = re.compile('^Exif|^orientation$')
    type = 'Exif'
    _extract_methods = {
        _t('orientation'): _extract_orientation}

    prefix = type + '_'
    _prefix_n = len(prefix)
    possible_vars = sorted(_extract_methods.keys())


class InfoIptc(_InfoPyexiv2):
    """
    >>> import pprint
    >>> filename = '../tests/input/exĩf ïptç.jpg'
    >>> info = InfoIptc(filename)
    >>> info['Iptc_Application2_RecordVersion']
    0
    >>> import pyexiv2
    >>> exif = pyexiv2.Image(filename)
    >>> exif.readMetadata()
    >>> info = InfoIptc(exif)
    >>> info['Iptc_Application2_RecordVersion']
    0
    >>> info['Iptc_Application2_Copyright']
    'Copyright 2010, www.stani.be'
    >>> pprint.pprint(sorted(info.dict.keys()))
    ['Iptc_Application2_Copyright', 'Iptc_Application2_RecordVersion']
    >>> info.extract_all()
    >>> pprint.pprint(sorted(info.dict.keys()))
    ['Iptc_Application2_Byline',
     'Iptc_Application2_Caption',
     'Iptc_Application2_Copyright',
     'Iptc_Application2_ObjectName',
     'Iptc_Application2_RecordVersion']
    """

    def _extract_others(self):
        """Extract all other vars"""
        self._extract_others_from_keys(self._source.iptcKeys())

    type = 'Iptc'
    regex = re.compile('^Iptc_')

    prefix = type + '_'
    _prefix_n = len(prefix)


class InfoEXIF(_InfoCache):
    """
    >>> import pprint
    >>> filename = '../tests/input/exĩf ïptç.jpg'
    >>> info = InfoEXIF(filename)
    >>> pprint.pprint(sorted(info.dict.keys()))
    []
    >>> info['EXIF_Thumbnail_Compression']
    (0x0103) Short=JPEG (old-style) @ 3402
    >>> pprint.pprint(sorted(info.dict.keys()))
    ['EXIF_Thumbnail_Compression']
    >>> import pyexiv2
    >>> from other import EXIF
    >>> exif = EXIF.process_file(open(filename, 'rb'))
    >>> info = InfoEXIF(exif)
    >>> info['orientation']
    8
    >>> str(info['EXIF_Image_Orientation'])
    'Rotated 90 CCW'
    >>> info['EXIF_Thumbnail_Compression']
    (0x0103) Short=JPEG (old-style) @ 3402
    >>> pprint.pprint(sorted(info.dict.keys()))
    ['EXIF_Image_Orientation', 'EXIF_Thumbnail_Compression', 'orientation']
    >>> info.extract_all()
    >>> pprint.pprint(sorted(info.dict.keys()))
    ['EXIF_ApertureValue',
     'EXIF_ColorSpace',
     'EXIF_ComponentsConfiguration',
     'EXIF_CompressedBitsPerPixel',
     'EXIF_CustomRendered',
     'EXIF_DateTimeDigitized',
     'EXIF_DateTimeOriginal',
     'EXIF_DigitalZoomRatio',
     'EXIF_ExifImageLength',
     'EXIF_ExifImageWidth',
     'EXIF_ExifVersion',
     'EXIF_ExposureBiasValue',
     'EXIF_ExposureMode',
     'EXIF_ExposureTime',
     'EXIF_FNumber',
     'EXIF_FileSource',
     'EXIF_Flash',
     'EXIF_FlashPixVersion',
     'EXIF_FocalLength',
     'EXIF_FocalPlaneResolutionUnit',
     'EXIF_FocalPlaneXResolution',
     'EXIF_FocalPlaneYResolution',
     'EXIF_Image_DateTime',
     'EXIF_Image_ExifOffset',
     'EXIF_Image_Make',
     'EXIF_Image_Model',
     'EXIF_Image_Orientation',
     'EXIF_Image_ResolutionUnit',
     'EXIF_Image_XResolution',
     'EXIF_Image_YCbCrPositioning',
     'EXIF_Image_YResolution',
     'EXIF_InteroperabilityOffset',
     'EXIF_JPEGThumbnail',
     'EXIF_MakerNote',
     'EXIF_MakerNote_AFPointSelected',
     'EXIF_MakerNote_AFPointUsed',
     'EXIF_MakerNote_ContinuousDriveMode',
     'EXIF_MakerNote_Contrast',
     'EXIF_MakerNote_DigitalZoom',
     'EXIF_MakerNote_EasyShootingMode',
     'EXIF_MakerNote_ExposureMode',
     'EXIF_MakerNote_FirmwareVersion',
     'EXIF_MakerNote_FlashActivity',
     'EXIF_MakerNote_FlashBias',
     'EXIF_MakerNote_FlashDetails',
     'EXIF_MakerNote_FlashMode',
     'EXIF_MakerNote_FocalUnitsPerMM',
     'EXIF_MakerNote_FocusMode',
     'EXIF_MakerNote_FocusType',
     'EXIF_MakerNote_ISO',
     'EXIF_MakerNote_ImageNumber',
     'EXIF_MakerNote_ImageSize',
     'EXIF_MakerNote_ImageType',
     'EXIF_MakerNote_LongFocalLengthOfLensInFocalUnits',
     'EXIF_MakerNote_Macromode',
     'EXIF_MakerNote_MeteringMode',
     'EXIF_MakerNote_OwnerName',
     'EXIF_MakerNote_Quality',
     'EXIF_MakerNote_Saturation',
     'EXIF_MakerNote_SelfTimer',
     'EXIF_MakerNote_SequenceNumber',
     'EXIF_MakerNote_Sharpness',
     'EXIF_MakerNote_ShortFocalLengthOfLensInFocalUnits',
     'EXIF_MakerNote_SubjectDistance',
     'EXIF_MakerNote_Tag_0x0000',
     'EXIF_MakerNote_Tag_0x0001',
     'EXIF_MakerNote_Tag_0x0002',
     'EXIF_MakerNote_Tag_0x0003',
     'EXIF_MakerNote_Tag_0x0004',
     'EXIF_MakerNote_Tag_0x000D',
     'EXIF_MakerNote_Tag_0x0010',
     'EXIF_MakerNote_Tag_0x0013',
     'EXIF_MakerNote_Tag_0x0018',
     'EXIF_MakerNote_Tag_0x0019',
     'EXIF_MakerNote_Tag_0x001C',
     'EXIF_MakerNote_Tag_0x001D',
     'EXIF_MakerNote_Tag_0x001E',
     'EXIF_MakerNote_Tag_0x001F',
     'EXIF_MakerNote_Tag_0x0022',
     'EXIF_MakerNote_Tag_0x0023',
     'EXIF_MakerNote_Tag_0x0024',
     'EXIF_MakerNote_Tag_0x0025',
     'EXIF_MakerNote_Tag_0x0026',
     'EXIF_MakerNote_Tag_0x0027',
     'EXIF_MakerNote_Tag_0x0028',
     'EXIF_MakerNote_Unknown',
     'EXIF_MakerNote_WhiteBalance',
     'EXIF_MaxApertureValue',
     'EXIF_MeteringMode',
     'EXIF_SceneCaptureType',
     'EXIF_SensingMethod',
     'EXIF_ShutterSpeedValue',
     'EXIF_Thumbnail_Compression',
     'EXIF_Thumbnail_JPEGInterchangeFormat',
     'EXIF_Thumbnail_JPEGInterchangeFormatLength',
     'EXIF_Thumbnail_ResolutionUnit',
     'EXIF_Thumbnail_XResolution',
     'EXIF_Thumbnail_YResolution',
     'EXIF_UserComment',
     'EXIF_WhiteBalance',
     'orientation']
    """

    def _extract_orientation(self):
        """Extract orientation from source image as integer.

        .. note::

            This translates the EXIF orientation string back to a
            number.
        """
        try:
            orientation = self._orientation_dict[
                str(self._source['Image Orientation'])]
        except KeyError:
            orientation = 1
        self.dict['orientation'] = orientation

    def _get_other(self, var):
        """Get a variable which is not defined in
        :method:`_extract_methods`.

        :param var: name of the variable
        :type var: string
        """
        var = var.replace('_', ' ')
        try:
            return self._source['EXIF ' + var]
        except KeyError:
            return self._source[var]

    def _extract_others(self):
        """Extract all other vars"""
        for tag, value in self._source.items():
            tag = tag.replace(' ', '_')
            if not tag.startswith('EXIF'):
                tag = 'EXIF_' + tag
            self.dict[tag] = value

    @classmethod
    def _load_module(cls):
        """Code to load the EXIF module."""
        from other import EXIF
        cls.EXIF = EXIF

    @classmethod
    def _get_source_from_file(cls, filename):
        """Load the EXIF source from a file.

        :param filename: filename of the source file
        :type filename: string
        """
        return cls.EXIF.process_file(open(filename, 'rb'))

    type = 'EXIF'
    _extract_methods = {
        _t('orientation'): _extract_orientation}
    _orientation_dict = {
        'Horizontal (normal)': 1,
        'Mirrored horizontal': 2,
        'Rotated 180': 3,
        'Mirrored vertical': 4,
        'Mirrored horizontal then rotated 90 CCW': 5,
        'Rotated 90 CW': 6,
        'Mirrored horizontal then rotated 90 CW': 7,
        'Rotated 90 CCW': 8}

    prefix = type + '_'
    _prefix_n = len(prefix)
    possible_vars = sorted(_extract_methods.keys())


INFOS = [InfoFile]
if pyexiv2:
    INFOS.extend([InfoExif, InfoIptc])
INFOS.extend([InfoPil, InfoPexif, InfoZexif])
#, InfoEXIF] #EXIF disabled for now as it crashes
INFOS_WITH_ORIENTATION = [Info for Info in INFOS
    if 'orientation' in Info.possible_vars]
VARS_BY_INFO_EXIF = {}
for info in INFOS:
    #set to None so it defaults to all variables
    VARS_BY_INFO_EXIF[info] = None
VARS_BY_INFO = {InfoFile: None, InfoPil: None}


def get_vars_by_info(filename):
    format = imtools.get_format_filename(filename)
    if (_pyexiv2 and _pyexiv2.is_readable_format(format)) or format == 'JPEG':
        return VARS_BY_INFO_EXIF.copy()
    else:
        return VARS_BY_INFO.copy()


class InfoTest:

    def __getitem__(self, var):
        if self.provides(var):
            if '_DateTime' in var:
                return now()
            else:
                return INFO_TEST.get(var, '2')
        raise KeyError(var)

    def __contains__(self, var):
        return self.provides(var)

    @classmethod
    def provides(cls, var):
        if var in ('desktop', 'index', 'folderindex'):
            return True
        for Info in INFOS:
            if Info.provides(var):
                return True
        return False


class InfoExtract:
    """Create an info like dictionary which uses a collection of several
    info instances and can evaluate Python expressions.

    >>> import Image
    >>> import pprint
    >>> list(InfoExtract.get_vars_by_info(['mode'])[0].values())
    [['mode', 'orientation']]
    >>> list(InfoExtract.get_vars_by_info(['width'])[0].values())
    [['width', 'orientation']]
    >>> vars = ['format', 'width', 'subfolder', 'orientation', 'crazy']
    >>> filename = '../tests/input/exĩf ïptç.jpg'
    >>> image = Image.open(filename)
    >>> info = InfoExtract(filename, vars + ['Pexif_DateTimeOriginal'])
    >>> info.types()
    ['File', 'Exif', 'Pil', 'Pexif']
    >>> info.vars_unknown
    ['crazy']
    >>> info['format']
    'JPEG'
    >>> pprint.pprint(sorted(info.dump(expand=False).items()))
    [('Pexif_DateTimeOriginal', DateTime('2010:03:03 11:03:08')),
     ('format', 'JPEG'),
     ('height', 640),
     ('orientation', 8),
     ('size', (480, 640)),
     ('subfolder', u''),
     ('width', 480)]
    >>> info['size']  # uses orientation
    (480, 640)
    >>> image.size  # ignores orientation
    (640, 480)
    >>> info['Pexif_DateTimeOriginal']
    DateTime('2010:03:03 11:03:08')
    >>> pprint.pprint(sorted(info.dump(expand=True).items()))
    [('Pexif_DateTimeOriginal', DateTime('2010:03:03 11:03:08')),
     ('Pexif_DateTimeOriginal.day', 3),
     ('Pexif_DateTimeOriginal.hour', 11),
     ('Pexif_DateTimeOriginal.microsecond', 0),
     ('Pexif_DateTimeOriginal.minute', 3),
     ('Pexif_DateTimeOriginal.month', 3),
     ('Pexif_DateTimeOriginal.monthname', 'March'),
     ('Pexif_DateTimeOriginal.second', 8),
     ('Pexif_DateTimeOriginal.weekday', 2),
     ('Pexif_DateTimeOriginal.weekdayname', 'Wednesday'),
     ('Pexif_DateTimeOriginal.year', 2010),
     ('format', 'JPEG'),
     ('height', 640),
     ('orientation', 8),
     ('size', (480, 640)),
     ('size[0]', 480),
     ('size[1]', 640),
     ('subfolder', u''),
     ('width', 480)]
    >>> info.extract_all()
    >>> pprint.pprint(sorted(info.dump(expand=False).keys()))
    ['Exif_CanonCs_0x0000',
     'Exif_CanonCs_0x0006',
     'Exif_CanonCs_0x0008',
     'Exif_CanonCs_0x0009',
     'Exif_CanonCs_0x0015',
     'Exif_CanonCs_0x001e',
     'Exif_CanonCs_0x001f',
     'Exif_CanonCs_0x0026',
     'Exif_CanonCs_0x0027',
     'Exif_CanonCs_0x0029',
     'Exif_CanonCs_0x002b',
     'Exif_CanonCs_0x002c',
     'Exif_CanonCs_0x002d',
     'Exif_CanonCs_AESetting',
     'Exif_CanonCs_AFPoint',
     'Exif_CanonCs_ColorTone',
     'Exif_CanonCs_Contrast',
     'Exif_CanonCs_DigitalZoom',
     'Exif_CanonCs_DisplayAperture',
     'Exif_CanonCs_DriveMode',
     'Exif_CanonCs_EasyMode',
     'Exif_CanonCs_ExposureProgram',
     'Exif_CanonCs_FlashActivity',
     'Exif_CanonCs_FlashDetails',
     'Exif_CanonCs_FlashMode',
     'Exif_CanonCs_FocusContinuous',
     'Exif_CanonCs_FocusMode',
     'Exif_CanonCs_FocusType',
     'Exif_CanonCs_ISOSpeed',
     'Exif_CanonCs_ImageSize',
     'Exif_CanonCs_ImageStabilization',
     'Exif_CanonCs_Lens',
     'Exif_CanonCs_LensType',
     'Exif_CanonCs_Macro',
     'Exif_CanonCs_MaxAperture',
     'Exif_CanonCs_MeteringMode',
     'Exif_CanonCs_MinAperture',
     'Exif_CanonCs_PhotoEffect',
     'Exif_CanonCs_Quality',
     'Exif_CanonCs_Saturation',
     'Exif_CanonCs_Selftimer',
     'Exif_CanonCs_Sharpness',
     'Exif_CanonCs_ZoomSourceWidth',
     'Exif_CanonCs_ZoomTargetWidth',
     'Exif_CanonSi_0x0000',
     'Exif_CanonSi_0x0001',
     'Exif_CanonSi_0x0003',
     'Exif_CanonSi_0x0006',
     'Exif_CanonSi_0x0008',
     'Exif_CanonSi_0x000a',
     'Exif_CanonSi_0x000b',
     'Exif_CanonSi_0x000c',
     'Exif_CanonSi_0x000d',
     'Exif_CanonSi_0x0010',
     'Exif_CanonSi_0x0011',
     'Exif_CanonSi_0x0012',
     'Exif_CanonSi_0x0014',
     'Exif_CanonSi_0x0017',
     'Exif_CanonSi_0x0018',
     'Exif_CanonSi_0x0019',
     'Exif_CanonSi_0x001a',
     'Exif_CanonSi_0x001b',
     'Exif_CanonSi_0x001c',
     'Exif_CanonSi_0x001d',
     'Exif_CanonSi_0x001e',
     'Exif_CanonSi_0x001f',
     'Exif_CanonSi_0x0020',
     'Exif_CanonSi_0x0021',
     'Exif_CanonSi_AFPointUsed',
     'Exif_CanonSi_ApertureValue',
     'Exif_CanonSi_FlashBias',
     'Exif_CanonSi_ISOSpeed',
     'Exif_CanonSi_Sequence',
     'Exif_CanonSi_ShutterSpeedValue',
     'Exif_CanonSi_SubjectDistance',
     'Exif_CanonSi_TargetAperture',
     'Exif_CanonSi_TargetShutterSpeed',
     'Exif_CanonSi_WhiteBalance',
     'Exif_Canon_0x0000',
     'Exif_Canon_0x0003',
     'Exif_Canon_0x000d',
     'Exif_Canon_0x0013',
     'Exif_Canon_0x0018',
     'Exif_Canon_0x0019',
     'Exif_Canon_0x001c',
     'Exif_Canon_0x001d',
     'Exif_Canon_0x001e',
     'Exif_Canon_0x001f',
     'Exif_Canon_0x0022',
     'Exif_Canon_0x0023',
     'Exif_Canon_0x0024',
     'Exif_Canon_0x0025',
     'Exif_Canon_0x0026',
     'Exif_Canon_0x0027',
     'Exif_Canon_0x0028',
     'Exif_Canon_FirmwareVersion',
     'Exif_Canon_FocalLength',
     'Exif_Canon_ImageNumber',
     'Exif_Canon_ImageType',
     'Exif_Canon_ModelID',
     'Exif_Canon_OwnerName',
     'Exif_Image_DateTime',
     'Exif_Image_ExifTag',
     'Exif_Image_Make',
     'Exif_Image_Model',
     'Exif_Image_Orientation',
     'Exif_Image_ResolutionUnit',
     'Exif_Image_XResolution',
     'Exif_Image_YCbCrPositioning',
     'Exif_Image_YResolution',
     'Exif_Iop_InteroperabilityIndex',
     'Exif_Iop_InteroperabilityVersion',
     'Exif_Iop_RelatedImageLength',
     'Exif_Iop_RelatedImageWidth',
     'Exif_MakerNote_ByteOrder',
     'Exif_MakerNote_Offset',
     'Exif_Photo_ApertureValue',
     'Exif_Photo_ColorSpace',
     'Exif_Photo_ComponentsConfiguration',
     'Exif_Photo_CompressedBitsPerPixel',
     'Exif_Photo_CustomRendered',
     'Exif_Photo_DateTimeDigitized',
     'Exif_Photo_DateTimeOriginal',
     'Exif_Photo_DigitalZoomRatio',
     'Exif_Photo_ExifVersion',
     'Exif_Photo_ExposureBiasValue',
     'Exif_Photo_ExposureMode',
     'Exif_Photo_ExposureTime',
     'Exif_Photo_FNumber',
     'Exif_Photo_FileSource',
     'Exif_Photo_Flash',
     'Exif_Photo_FlashpixVersion',
     'Exif_Photo_FocalLength',
     'Exif_Photo_FocalPlaneResolutionUnit',
     'Exif_Photo_FocalPlaneXResolution',
     'Exif_Photo_FocalPlaneYResolution',
     'Exif_Photo_InteroperabilityTag',
     'Exif_Photo_MakerNote',
     'Exif_Photo_MaxApertureValue',
     'Exif_Photo_MeteringMode',
     'Exif_Photo_PixelXDimension',
     'Exif_Photo_PixelYDimension',
     'Exif_Photo_SceneCaptureType',
     'Exif_Photo_SensingMethod',
     'Exif_Photo_ShutterSpeedValue',
     'Exif_Photo_UserComment',
     'Exif_Photo_WhiteBalance',
     'Exif_Thumbnail_Compression',
     'Exif_Thumbnail_JPEGInterchangeFormat',
     'Exif_Thumbnail_JPEGInterchangeFormatLength',
     'Exif_Thumbnail_ResolutionUnit',
     'Exif_Thumbnail_XResolution',
     'Exif_Thumbnail_YResolution',
     'Pexif_ApertureValue',
     'Pexif_ColorSpace',
     'Pexif_ComponentsConfiguration',
     'Pexif_CompressedBitsPerPixel',
     'Pexif_DateTime',
     'Pexif_DateTimeDigitized',
     'Pexif_DateTimeOriginal',
     'Pexif_ExifImageHeight',
     'Pexif_ExifImageWidth',
     'Pexif_ExifInteroperabilityOffset',
     'Pexif_ExifOffset',
     'Pexif_ExifVersion',
     'Pexif_ExposureTime',
     'Pexif_FNumber',
     'Pexif_FileSource',
     'Pexif_Flash',
     'Pexif_FlashPixVersion',
     'Pexif_FocalLength',
     'Pexif_FocalPlaneResolutionUnit',
     'Pexif_FocalPlaneXResolution',
     'Pexif_FocalPlaneYResolution',
     'Pexif_Make',
     'Pexif_MakerNote',
     'Pexif_MaxApertureValue',
     'Pexif_MeteringMode',
     'Pexif_Model',
     'Pexif_Orientation',
     'Pexif_ResolutionUnit',
     'Pexif_SensingMethod',
     'Pexif_UserComment',
     'Pexif_XResolution',
     'Pexif_YCbCrPositioning',
     'Pexif_YResolution',
     'aspect',
     'compression',
     'day',
     'desktop',
     'dpi',
     'filename',
     'filesize',
     'folder',
     'foldername',
     'format',
     'formatdescription',
     'gamma',
     'height',
     'hour',
     'interlace',
     'minute',
     'mode',
     'month',
     'monthname',
     'orientation',
     'path',
     'root',
     'second',
     'size',
     'subfolder',
     'transparency',
     'type',
     'weekday',
     'weekdayname',
     'width',
     'year']
    >>> info.set(filename='../tests/input/exĩf ïptç.jpg',
    ...     vars=vars) #exclude Pexif.* vars
    >>> pprint.pprint(sorted(info.dump(expand=False).items()))
    [('format', 'JPEG'),
     ('height', 640),
     ('orientation', 8),
     ('size', (480, 640)),
     ('subfolder', u''),
     ('width', 480)]
    >>> info['root']
    u'../tests'
    >>> d = info.dump(expand=False)
    >>> pprint.pprint(sorted(d.items()))
    [('foldername', u'input'),
     ('format', 'JPEG'),
     ('height', 640),
     ('orientation', 8),
     ('root', u'../tests'),
     ('size', (480, 640)),
     ('subfolder', u''),
     ('width', 480)]
    >>> type(d) == dict
    True
    >>> info.set(vars=vars + ['Iptc_Application2_Copyright'])
    >>> info.extract_all()
    >>> pprint.pprint(sorted(info.dump(expand=False).keys()))
    ['Exif_CanonCs_0x0000',
     'Exif_CanonCs_0x0006',
     'Exif_CanonCs_0x0008',
     'Exif_CanonCs_0x0009',
     'Exif_CanonCs_0x0015',
     'Exif_CanonCs_0x001e',
     'Exif_CanonCs_0x001f',
     'Exif_CanonCs_0x0026',
     'Exif_CanonCs_0x0027',
     'Exif_CanonCs_0x0029',
     'Exif_CanonCs_0x002b',
     'Exif_CanonCs_0x002c',
     'Exif_CanonCs_0x002d',
     'Exif_CanonCs_AESetting',
     'Exif_CanonCs_AFPoint',
     'Exif_CanonCs_ColorTone',
     'Exif_CanonCs_Contrast',
     'Exif_CanonCs_DigitalZoom',
     'Exif_CanonCs_DisplayAperture',
     'Exif_CanonCs_DriveMode',
     'Exif_CanonCs_EasyMode',
     'Exif_CanonCs_ExposureProgram',
     'Exif_CanonCs_FlashActivity',
     'Exif_CanonCs_FlashDetails',
     'Exif_CanonCs_FlashMode',
     'Exif_CanonCs_FocusContinuous',
     'Exif_CanonCs_FocusMode',
     'Exif_CanonCs_FocusType',
     'Exif_CanonCs_ISOSpeed',
     'Exif_CanonCs_ImageSize',
     'Exif_CanonCs_ImageStabilization',
     'Exif_CanonCs_Lens',
     'Exif_CanonCs_LensType',
     'Exif_CanonCs_Macro',
     'Exif_CanonCs_MaxAperture',
     'Exif_CanonCs_MeteringMode',
     'Exif_CanonCs_MinAperture',
     'Exif_CanonCs_PhotoEffect',
     'Exif_CanonCs_Quality',
     'Exif_CanonCs_Saturation',
     'Exif_CanonCs_Selftimer',
     'Exif_CanonCs_Sharpness',
     'Exif_CanonCs_ZoomSourceWidth',
     'Exif_CanonCs_ZoomTargetWidth',
     'Exif_CanonSi_0x0000',
     'Exif_CanonSi_0x0001',
     'Exif_CanonSi_0x0003',
     'Exif_CanonSi_0x0006',
     'Exif_CanonSi_0x0008',
     'Exif_CanonSi_0x000a',
     'Exif_CanonSi_0x000b',
     'Exif_CanonSi_0x000c',
     'Exif_CanonSi_0x000d',
     'Exif_CanonSi_0x0010',
     'Exif_CanonSi_0x0011',
     'Exif_CanonSi_0x0012',
     'Exif_CanonSi_0x0014',
     'Exif_CanonSi_0x0017',
     'Exif_CanonSi_0x0018',
     'Exif_CanonSi_0x0019',
     'Exif_CanonSi_0x001a',
     'Exif_CanonSi_0x001b',
     'Exif_CanonSi_0x001c',
     'Exif_CanonSi_0x001d',
     'Exif_CanonSi_0x001e',
     'Exif_CanonSi_0x001f',
     'Exif_CanonSi_0x0020',
     'Exif_CanonSi_0x0021',
     'Exif_CanonSi_AFPointUsed',
     'Exif_CanonSi_ApertureValue',
     'Exif_CanonSi_FlashBias',
     'Exif_CanonSi_ISOSpeed',
     'Exif_CanonSi_Sequence',
     'Exif_CanonSi_ShutterSpeedValue',
     'Exif_CanonSi_SubjectDistance',
     'Exif_CanonSi_TargetAperture',
     'Exif_CanonSi_TargetShutterSpeed',
     'Exif_CanonSi_WhiteBalance',
     'Exif_Canon_0x0000',
     'Exif_Canon_0x0003',
     'Exif_Canon_0x000d',
     'Exif_Canon_0x0013',
     'Exif_Canon_0x0018',
     'Exif_Canon_0x0019',
     'Exif_Canon_0x001c',
     'Exif_Canon_0x001d',
     'Exif_Canon_0x001e',
     'Exif_Canon_0x001f',
     'Exif_Canon_0x0022',
     'Exif_Canon_0x0023',
     'Exif_Canon_0x0024',
     'Exif_Canon_0x0025',
     'Exif_Canon_0x0026',
     'Exif_Canon_0x0027',
     'Exif_Canon_0x0028',
     'Exif_Canon_FirmwareVersion',
     'Exif_Canon_FocalLength',
     'Exif_Canon_ImageNumber',
     'Exif_Canon_ImageType',
     'Exif_Canon_ModelID',
     'Exif_Canon_OwnerName',
     'Exif_Image_DateTime',
     'Exif_Image_ExifTag',
     'Exif_Image_Make',
     'Exif_Image_Model',
     'Exif_Image_Orientation',
     'Exif_Image_ResolutionUnit',
     'Exif_Image_XResolution',
     'Exif_Image_YCbCrPositioning',
     'Exif_Image_YResolution',
     'Exif_Iop_InteroperabilityIndex',
     'Exif_Iop_InteroperabilityVersion',
     'Exif_Iop_RelatedImageLength',
     'Exif_Iop_RelatedImageWidth',
     'Exif_MakerNote_ByteOrder',
     'Exif_MakerNote_Offset',
     'Exif_Photo_ApertureValue',
     'Exif_Photo_ColorSpace',
     'Exif_Photo_ComponentsConfiguration',
     'Exif_Photo_CompressedBitsPerPixel',
     'Exif_Photo_CustomRendered',
     'Exif_Photo_DateTimeDigitized',
     'Exif_Photo_DateTimeOriginal',
     'Exif_Photo_DigitalZoomRatio',
     'Exif_Photo_ExifVersion',
     'Exif_Photo_ExposureBiasValue',
     'Exif_Photo_ExposureMode',
     'Exif_Photo_ExposureTime',
     'Exif_Photo_FNumber',
     'Exif_Photo_FileSource',
     'Exif_Photo_Flash',
     'Exif_Photo_FlashpixVersion',
     'Exif_Photo_FocalLength',
     'Exif_Photo_FocalPlaneResolutionUnit',
     'Exif_Photo_FocalPlaneXResolution',
     'Exif_Photo_FocalPlaneYResolution',
     'Exif_Photo_InteroperabilityTag',
     'Exif_Photo_MakerNote',
     'Exif_Photo_MaxApertureValue',
     'Exif_Photo_MeteringMode',
     'Exif_Photo_PixelXDimension',
     'Exif_Photo_PixelYDimension',
     'Exif_Photo_SceneCaptureType',
     'Exif_Photo_SensingMethod',
     'Exif_Photo_ShutterSpeedValue',
     'Exif_Photo_UserComment',
     'Exif_Photo_WhiteBalance',
     'Exif_Thumbnail_Compression',
     'Exif_Thumbnail_JPEGInterchangeFormat',
     'Exif_Thumbnail_JPEGInterchangeFormatLength',
     'Exif_Thumbnail_ResolutionUnit',
     'Exif_Thumbnail_XResolution',
     'Exif_Thumbnail_YResolution',
     'Iptc_Application2_Byline',
     'Iptc_Application2_Caption',
     'Iptc_Application2_Copyright',
     'Iptc_Application2_ObjectName',
     'Iptc_Application2_RecordVersion',
     'aspect',
     'compression',
     'day',
     'desktop',
     'dpi',
     'filename',
     'filesize',
     'folder',
     'foldername',
     'format',
     'formatdescription',
     'gamma',
     'height',
     'hour',
     'interlace',
     'minute',
     'mode',
     'month',
     'monthname',
     'orientation',
     'path',
     'root',
     'second',
     'size',
     'subfolder',
     'transparency',
     'type',
     'weekday',
     'weekdayname',
     'width',
     'year']
    """

    def __init__(self, filename=None, vars=None, sources=None):
        """Create an InfoExtract instance.

        :param filename: filename of the source file
        :type filename: string
        :param vars: variables that have to be extracted (e.g. orientation)
        :type vars: list
        """
        if vars is None:
            vars = []
        self.list = []
        self._vars = None  # list of possible vars which can occur
        self._vars_by_info = None
        self.set_vars(vars, filename)
        if filename:
            self.open(filename, sources)

    def __getitem__(self, var):
        # force var as string, otherwise py2exiv fails (eg with unicode)
        # eg u'Exif_Photo_DateTimeOriginal'
        var = str(var)
        for info in self.list:
            if info.provides(var):
                return info[var]
        raise KeyError(var)

    def set(self, filename=None, vars=None, sources=None):
        """Set new parameters for the info.

        :param filename: filename of the source file
        :type filename: string
        :param vars: variables that have to be extracted (e.g. orientation)
        :type vars: list
        """
        if not(vars is None):
            self.set_vars(vars)
            self.open(filename)
        elif not(filename is None):
            self.open(filename, sources)

    def open(self, filename, sources=None):
        """Feeds a new file as source for all info types.

        :param filename: filename of the source file
        :type filename: string

        .. note:: This will clear the cache.
        """
        if filename:
            self.filename = filename.replace('file://', '')
        if not self._vars:
            # ->all variables, which are image dependent
            self._vars_by_info = get_vars_by_info(filename)
        self.clear_cache()
        # ensure sources is a dict
        if not sources:
            sources = {}
        # load files
        self.list = [
            Info(sources.get(Info, self.filename), self._vars_by_info[Info])
            for Info in self._vars_by_info.keys()]  # use keys to respect order
        self.set_orientation()
        return self

    def clear_cache(self):
        """Clears the look up cache."""
        self._cache = {}

    @classmethod
    def get_vars_by_info(cls, vars, old_vars=None, filename='test.png'):
        """Organizes vars in a dictionary by Info class (e.g.
        :class:`InfoPil`, :class:`InfoExif`, ...).

        As this is a class method, ``old_vars`` has to be passed explicitly
        instead of being obtained from the instance.

        :param vars: variables
        :type vars: list of strings
        :param old_vars: previous variables
        :type old_vars: list of strings
        """
        # collect all requested infos
        if vars:
            vars_by_info, vars_unknown = cls.scan_infos(vars)
        else:
            vars_by_info = get_vars_by_info(filename)
            vars_unknown = []
        # check orientation
        set_vars_by_info = set(vars_by_info)
        if not set_vars_by_info.intersection(INFOS_WITH_ORIENTATION):
            needs_orientation = [Info
                for Info in set_vars_by_info.difference(INFOS_WITH_ORIENTATION)
                if Info.needs_orientation(vars_by_info[Info])]
            if needs_orientation:
                if not(vars_by_info[InfoPil] is None):
                    # orientation is included in None already
                    vars_by_info[InfoPil] += ['orientation']
        return vars_by_info, vars_unknown

    def set_vars(self, vars, filename='test.png'):
        """Limit the range of the possible variables which might
        be looked up.

        :param vars: variables that have to be extracted (e.g. orientation)
        :type vars: list
        """
        # collect all requested infos
        if vars != self._vars:
            self._vars_by_info, self.vars_unknown = \
                self.get_vars_by_info(vars, self._vars, filename)
        # update vars (needs to be after previous collect)
        if not vars:
            vars = []
        self._vars = list(set(vars).difference(self.vars_unknown))

    def set_orientation(self, orientation=None):
        if orientation is None:
            try:
                orientation = self['orientation']
            except:
                # no orientation needed
                return
        for info in self.list:
            if info.needs_orientation(info.vars):
                info.set_orientation(orientation)

    @classmethod
    def scan_infos(cls, vars):
        """Scan which info types the variables ``vars`` require.

        :param vars: variables which have to be provided
        :type vars: list
        :returns: variables by required info types
        :rtype: dict of lists
        """
        Infos = odict.odict()
        todo = vars[:]  # we don't want to change the orignal vars
        todo_temp = vars[:]
        # loop first over Infos so that the info order is kept
        for Info in INFOS:
            for var in todo:
                if Info.provides(var):
                    if Info in Infos:
                        Infos[Info].append(var)
                    else:
                        Infos[Info] = [var]
                    # var is provided, so don't look for it anymore
                    todo_temp.remove(var)
            # make a copy as we can't modify an looping iterable
            if todo_temp:
                todo = todo_temp[:]
            else:
                break
        # return vars by info, unknown vars
        return Infos, todo_temp

    def provides(self, var):
        """Whether this info provides this variable.

        :param var: name of the variable
        :type var: string
        :returns: if ``var`` is provided
        :rtype: bool
        """
        for info in self.list:
            if info.provides(var):
                return True
        return False

    def types(self):
        """Which info types are used by this instance.

        :returns: info types
        :rtype: list
        """
        return [info.type for info in self.list]

    def clear(self):
        """Clear alfl info types."""
        self.list = []

    def dump(self, filename=None, expand=False, free=False):
        """Dump as a dictionary.

        :param vars: list of variables as arguments
        :type vars: list
        """
        if filename:
            self.open(filename)
        if self._vars:
            #load vars
            for info in self.list:
                info.enable_cache()
            for var in self._vars:
                self[var]
            for info in self.list:
                info.disable_cache()
        else:
            self.extract_all()
        d = {}
        for info in self.list:
            d.update(info.dict)
        if expand:
            self.expand(d)
        if free:
            self.list = []
        return d

    @classmethod
    def expand(cls, d):
        for key, value in d.items():
            cls.expand_var(d, key, value)

    @classmethod
    def expand_var(cls, d, key, value):
        if isinstance(value, DateTime):
            for attr in DateTime.attrs:
                d['%s.%s' % (key, attr)] = getattr(value, attr)
        elif type(value) in (tuple, list) and len(value) < 10:
            for index, value_index in enumerate(value):
                d['%s[%d]' % (key, index)] = value[index]
        elif hasattr(value, 'denominator') and value.denominator != 1:
            d['%s.denominator' % key] = value.denominator
            d['%s.numerator' % key] = value.numerator

    def set_source(self, d):
        """Set source of an info from the collection. Raises an
        ``UnknownTypeError`` in case an unknown type is given.

        :param d: dictionary {type: source} or type
        :type d: dict/str
        """
        for info in self.list:
            if info.type in d:
                info.set_source(d[info.type])

    def extract_all(self):
        """Extract all variables provided by the info types."""
        for info in self.list:
            info.extract_all()


class DumpInfo(dict):
    """Dictionary like object which tracks changes.

    >>> d = DumpInfo({'hello': 'world'})
    >>> d['foo'] = 'bar'
    >>> d.changed
    ['foo']
    """

    def __init__(self, d=None):
        """:param d: initial dictionary or None
        :type d: dict/None"""
        if d:
            self.update(d)
        self.changed = []

    def __setitem__(self, var, value):
        """Sets the item of the dictionary and add var to the ``changed``
        list

        :param var: variable
        :type var: string
        :param value: any kind of value
        """
        super(DumpInfo, self).__setitem__(var, value)
        self.changed.append(var)
