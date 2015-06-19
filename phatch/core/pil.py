# Phatch - Photo Batch Processor
# Copyright (C) 2007-2009 www.stani.be
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

# Follows PEP8

"""All PIL related issues."""

#FIXME:
# - info should be defined on layer level
#   -> move call afterwards also to layer level
#   -> adapt image inspector

import datetime
import os
import re
import types

import Image

#todo make this lazy
from lib import formField
from lib import imtools
from lib import metadata
from lib import openImage
from lib import system
from lib import thumbnail
from lib import unicoding
from lib.reverse_translation import _t
from lib.formField import RE_FILE_IN, RE_FILE_OUT

from ct import TITLE
from config import USER_BIN_PATH

#from other import EXIF

system.set_bin_paths([USER_BIN_PATH])

try:
    import pyexiv2
    from lib import _pyexiv2 as exif
except:
    pyexiv2 = None
    exif = False
WWW_PYEXIV2 = 'http://tilloy.net/dev/pyexiv2/'
NEEDS_PYEXIV2 = _('pyexiv2 needs to be installed') + ' (%s)' % WWW_PYEXIV2

CONVERTED_MODE = \
_('%(mode)s has been converted to %(mode_copy)s to save as %(format)s.')

DYNAMIC_VARS = set(('width', 'height', 'size', 'mode', 'transparency'))
IMAGE_DEFAULT_DPI = 72
SEPARATOR = '_'  # should be same as in core.translations
MONTHS = (_t('January'), _t('February'), _t('March'), _t('April'),
    _t('May'), _t('June'), _t('July'), _t('August'), _t('September'),
    _t('October'), _t('November'), _t('December'))
WEEKDAYS = (_t('Monday'), _t('Tuesday'), _t('Wednesday'), _t('Thursday'),
    _t('Friday'), _t('Saturday'), _t('Sunday'))
DATETIME_KEYS = ['year', 'month', 'day', 'hour', 'minute', 'second']
re_DATETIME = re.compile(
                '(?P<year>\d{4})[-:](?P<month>\d{2})[-:](?P<day>\d{2}) '
                '(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})')

re_TAG = re.compile('(Pil|Exif|Iptc|Pexif|Zexif)([.]\w+)+')
re_KEY = re.compile('(#*)((\w|[.])*$|[$])')
TRANSPARENCY_ERROR = _('Only palette images have transparency.')

IMAGE_READ_EXTENSIONS = set(formField.IMAGE_READ_EXTENSIONS)\
    .union(openImage.WITHOUT_PIL.extensions)
IMAGE_READ_EXTENSIONS = list(IMAGE_READ_EXTENSIONS)
IMAGE_READ_EXTENSIONS.sort()

IMAGE_EXTENSIONS = [ext for ext in IMAGE_READ_EXTENSIONS
    if ext in formField.IMAGE_WRITE_EXTENSIONS]

BASE_VARS = ['dpi', 'compression', 'filename', 'format',
    'orientation', 'path', 'transparency', 'type']


def split_data(d):
    """Provide attribute access to the variables.

    :param d: a dumped metadata dictionary
    :type d: dict

    >>> d = {'date': '2008-11-27 13:54:33', 'tuple': (1, 2)}
    """
    value = d.values()[0]
    #tuples or list
    if type(value) in (types.ListType, types.TupleType):
        if len(value) > 1:
            for k, v in d.items():
                for i, x in enumerate(v):
                    d['%s.%d' % (k, i)] = v[i]
        return
    #datetime strings
    done = False
    for k, v in d.items():
        if type(v) in types.StringTypes:
            dt = re_DATETIME.match(v)
            if dt:
                for key in DATETIME_KEYS:
                    d['%s.%s' % (k, key)] = dt.group(key)
                    done = True
    if done:
        return
    #date time values
    if type(value) == datetime.datetime:
        for k, v in d.items():
            for key in DATETIME_KEYS:
                d['%s.%s' % (k, key)] = getattr(v, key)


def fix_EXIF(tag):
    if not tag.startswith('EXIF'):
        tag = 'EXIF.' + tag
    return tag.replace(' ', SEPARATOR)


def image_to_dict(filename, im=None):
    folder, name = os.path.split(filename)
    d = {'path': filename, 'filename': name}
    if im:
        width, height = im.size
        d['width'] = width
        d['height'] = height
        d['mode'] = im.mode
    return d


def get_photo(filename):
    return Photo(metadata.InfoExtract(filename, vars=BASE_VARS).dump())


def split_vars_static_dynamic(vars):
    vars = set(vars)
    static = vars.difference(DYNAMIC_VARS)
    dynamic = vars.intersection(DYNAMIC_VARS)
    return list(static), list(dynamic)


class NotWritableTagError(Exception):
    pass


class InfoPhoto(dict):

    def __init__(self, info, info_to_dump, get_pil, image=None):
        """The ``get_pil`` parameter is necessary for tags as width,
        height, size and mode.

        :param info: pil, pyexiv2, ... tag, value info
        :type info: dict
        :param get_pil: method to retrieve the pil image
        :type get_pil: callable
        """
        #parameters
        self.get_pil = get_pil
        path = info['path']
        #sources
        if image == None:
            image = get_pil()
        sources = {
            metadata.InfoPil: image,
            metadata.InfoPexif: image,
            metadata.InfoZexif: image}
        #check format -> readable/writable metadata with pyexiv2
        if exif and exif.is_readable_format(image.format):
            self.pyexiv2 = pyexiv2.Image(path)
            self.pyexiv2.readMetadata()
            self.writable_exif = exif.is_writable_format_exif(image.format)
            self.writable_iptc = exif.is_writable_format_exif(image.format)
            self.writable = self.writable_exif or self.writable_iptc
            if self.writable_exif:
                self.pyexiv2['Exif.Image.Software'] = TITLE
            sources[metadata.InfoExif] = sources[metadata.InfoIptc] =\
                self.pyexiv2
        else:
            self.pyexiv2 = None
            self.writable = self.writable_exif = self.writable_iptc = False
        #retrieve dump info
        try:
            info_dumped = info_to_dump.open(path, sources).dump(free=True)
        except Exception, details:
            reason = unicoding.exception_to_unicode(details)
            #log error details
            message = u'%s:%s:\n%s' % (_('Unable extract variables from file'),
                path, reason)
            raise Exception(message)
        self.update(info, explicit=False)
        self.update(info_dumped, explicit=False)
        #private vars
        self._original_size = image.size  # to compare if changed later
        self._dirty = False
        self._log = ''
        self._flushed = True

    def close(self):
        """Remove circular reference."""
        del self.get_pil

    def is_dirty(self):
        """The photo can become dirty in two ways:

        * new metadata has been set
        * the image has changes size

        In case the image size has changed it will update the
        ``Exif.Photo.PixelXDimension`` and ``Exif.Photo.PixelYimension``
        accordingly.

        :returns: True, if dirty
        :rtype: boolean
        """
        if self._dirty:
            return True
        self.update_size()
        return self._dirty

    def set(self, tag, value):
        super(InfoPhoto, self).__setitem__(tag, value)

    def update(self, d, explicit=True):
        """Do this explicitly so __setitem__ gets called."""
        if explicit:
            for key, value in d.items():
                self[key] = value
        else:
            super(InfoPhoto, self).update(d)

    def update_size(self):
        """If the image is exif writable and if the size has changed,
        it will update ``Exif.Photo.PixelXDimension`` and
        ``Exif.Photo.PixelYimension``.
        """
        if not self.writable_exif:
            return
        size = width, height = self.get_pil().size
        if self._original_size != size:
            self.pyexiv2['Exif.Photo.PixelXDimension'] = width
            self.pyexiv2['Exif.Photo.PixelYDimension'] = height
            self._dirty = True

    def __getitem__(self, tag):
        """If a dynamic tag (size, mode) is requested, it will
        extract it from the image. Otherwise get it normally.

        :param tag: metadata tag
        :type tag: string
        :returns: value
        """
        if tag in DYNAMIC_VARS:
            #this can maybe be optimized if necessary
            if tag == 'size':
                return self.get_pil().size
            elif tag in ('width', 'Exif_Photo_PixelXDimension'):
                return self.get_pil().size[0]
            elif tag in ('height', 'Exif_Photo_PixelYDimension'):
                return self.get_pil().size[1]
            elif tag == 'mode':
                return self.get_pil().mode
            elif tag == 'transparency':
                self.assert_transparency()
                return self.get_pil().info['transparency']
            else:
                raise KeyError('Fatal Error: tag "%s" is not dynamic?!' % tag)
        elif tag in metadata.ORIENTATION_TAGS:
            #give priority to writable tag
            if 'Exif_Image_Orientation' in self:
                return super(InfoPhoto, self).\
                    __getitem__('Exif_Image_Orientation')
            else:
                return super(InfoPhoto, self).__getitem__(tag)
        else:
            return super(InfoPhoto, self).__getitem__(tag)

    def __contains__(self, tag):
        """
        """
        if super(InfoPhoto, self).__contains__(tag):
            return True
        if tag == 'transparency' and tag in self.get_pil().info:
            return self['mode'] == 'P'
        return tag in DYNAMIC_VARS

    def __delitem__(self, tag):
        """Delete a tag after :method:`InfoPhoto.assert_writable`.

        :param tag: metadata tag
        :type tag: string
        """
        self.assert_writable(tag)
        if tag == 'transparency':
            self.assert_transparency()
            del self.get_pil().info[tag]
            return
        pyexiv2_tag = self._fix(tag)  # pexiv2 demands str
        # a bit clumsy but pyexiv2 does not support get or in
        try:
            pyexiv2_tag_value = self.pyexiv2[pyexiv2_tag]
        except KeyError:
            pyexiv2_tag_value = None
        if self.pyexiv2 and pyexiv2_tag_value != None:
            self.pyexiv2[pyexiv2_tag] = None
        if tag in self:
            super(InfoPhoto, self).__delitem__(tag)

    def __setitem__(self, tag, value):
        """Delete a tag after :method:`InfoPhoto.assert_writable`.

        :param tag: metadata tag
        :type tag: string
        :param value: new value
        """
        self.assert_writable(tag)
        if tag in metadata.ORIENTATION_TAGS:
            if self.pyexiv2 is None and value == 1:
                #allow to ignore this (e.g. transpose method)
                return
            #redirect to writable tag
            tag = 'Exif_Image_Orientation'
        if tag in DYNAMIC_VARS:
            if tag == 'transparency':
                self.assert_transparency()
                self.get_pil().info['transparency'] = value
            else:
                raise KeyError(_('Tag "%s" is read only.') % tag)
        else:
            super(InfoPhoto, self).__setitem__(tag, value)
        if metadata.RE_PYEXIV2_TAG_EDITABLE.match(tag):
            try:
                self.pyexiv2[self._fix(tag)] = value
            except Exception, message:
                raise KeyError('%s:\n%s'
                    % (_('Impossible to write tag "%s"') % tag, message))
        self._dirty = True
        self._flushed = False

    def assert_transparency(self):
        """Raise a ``KeyError`` for ``'transparency'`` when ``image.mode``
        is not ``'P'``.
        """
        if self['mode'] != 'P':
            raise KeyError(TRANSPARENCY_ERROR)

    def log(self, message):
        """Log a message

        :param message: message
        :type message: string
        """
        self._log += message + '\n'

    def clear_log(self):
        """Clears the log."""
        self._log = ''

    def get_log(self):
        """Get the log contents.

        :returns: the log
        :rtype: string
        """
        return self._log

    @classmethod
    def _fix(cls, tag):
        """Phatch uses ``_`` as a separator while pyexiv2 uses a
        dot (``.``). Moreover pyexiv2 demands str.

        >>> InfoPhoto._fix('Exif_Photo_PixelXDimension')
        'Exif.Photo.PixelXDimension'

        :param tag: tag in info notation
        :type tag: string
        :returns: tag in pyexiv2 notation
        :rtype: string
        """
        return str(tag.replace('_', '.'))

    def assert_writable(self, tag):
        """Assert that the tag is writable. This can raise an
        ``NotWritableTagError`` because of several reasons:

        * Tag might be read-only (e.g. Exif_Photo_PixelXDimension)
        * Tag might be not Exif or Iptc
        * Image file format might not allow writing of this tag

        :param tag: tag name
        :type tag: string
        :returns: True, if writable
        :rtype: bool
        """
        if not metadata.is_writable_tag(tag):
            raise NotWritableTagError(_('Tag "%s" is not writable.') % tag)
        if not ((self.writable_exif and tag.startswith('Exif'))
            or (self.writable_iptc and tag.startswith('Iptc'))
            or metadata.is_writeable_not_exif_tag(tag, self['mode'])):
            raise NotWritableTagError(
                _('Format %(format)s does not support overwriting "%(tag)s".')\
                % {'format': self['format'], 'tag': tag})

    def save(self, target, target_format=None, thumbdata=None):
        """
        :param target: target filename
        :type target: string
        :param target_format: target format e.g. obtained by PIL
        :type target_format: string
        :param thumbdata: new thumbnail (eg with StringIO, see :mod:`imtools`)
        :type thumbdata: string
        """
        if not exif:
            raise ImportError(NEEDS_PYEXIV2)
        if not pyexiv2:
            #FIXME: when starting with a not exif image png
            #but save as exif jpg
            return
        if target == self['path']:
            if self.is_dirty() and not self._flushed:  # includes update_size
                warnings = exif.flush(self.pyexiv2, thumbdata)
                self._flushed = True
        else:
            self.update_size()
            warnings = exif.write_metadata(self.pyexiv2, target,
                self['format'], target_format, thumbdata)
        return warnings


class Photo:
    """Use :func:`get_photo` to obtain a photo from a filename."""

    def __init__(self, info, info_to_dump=None):
        self.modify_date = None  # for time shift action
        self.report_files = []  # for reports
        self._exif_transposition_reverse = None
        #layer
        path = info['path']
        name = self.current_layer_name = _t('background')
        layer = Layer(path, load=True)
        self.layers = {name: layer}
        #info
        self.info = InfoPhoto(info, info_to_dump, self.get_flattened_image,
            layer.image)
        self.rotate_exif()

    def close(self):
        """Remove circular references."""
        self.info.close()
        del self.info

    def log(self, message):
        self.info.log(message)

    def clear_log(self):
        self.info.clear_log()

    def get_log(self):
        return self.info.get_log()

    def get_filename(self, folder, filename, typ):
        return os.path.join(folder, '%s.%s' % (filename, typ))\
            .replace('<', '%(').replace('>', ')s') % self.__dict__

    #---layers
    def get_flattened_image(self):
        return self.get_layer().image.copy()

    def get_layer(self, name=None):
        if name is None:
            name = self.current_layer_name
        return self.layers[name]

    def get_thumb(self, size=thumbnail.SIZE):
        return thumbnail.thumbnail(self.get_flattened_image(),
            size=size, checkboard=True)

    def set_layer(self, layer, name=None):
        if name is None:
            name = self.current_layer_name
        self.layers[name] = layer

    #---image operations affecting all layers
    def save(self, filename, format=None, save_metadata=True, **options):
        """Saves a flattened image"""
        #todo: flatten layers
        if format is None:
            format = imtools.get_format_filename(filename)
        image = self.get_flattened_image()
        image_copy = imtools.convert_save_mode_by_format(image, format)
        if image_copy.mode == 'P' and 'transparency' in image_copy.info:
            options['transparency'] = image_copy.info['transparency']

        if image_copy.mode != image.mode:
            self.log(CONVERTED_MODE % {'mode': image.mode,
                'mode_copy': image_copy.mode, 'format': format} + '\n')

        #reverse exif previously applied exif orientation
        #exif thumbnails are usually within 160x160
        #desktop thumbnails size is defined by thumbnail.py and is
        #probably 128x128
        save_metadata = save_metadata and exif \
            and exif.is_writable_format(format)
        if save_metadata:
            # Exif thumbnails are stored in their own format (eg JPG)
            thumb = thumbnail.thumbnail(image_copy, (160, 160))
            thumbdata = imtools.get_format_data(thumb, format)
            image_copy = imtools.transpose(image_copy,
                self._exif_transposition_reverse)
            #thumb = thumbnail.thumbnail(thumb, copy=False)
        else:
            thumbdata = None
            #postpone thumbnail production to see later if it is needed
            thumb = None

        if 'compression.tif' in options:
            compression = options['compression.tif']
            del options['compression.tif']
        else:
            compression = 'none'

        try:
            if compression.lower() in ['raw', 'none']:
                #save image with pil
                file_mode = imtools.save_check_mode(image_copy, filename,
                    **options)
                #did PIL silently change the image mode?
                if file_mode:
                    #PIL did change the image mode without throwing
                    # an exception.
                    #Do not save thumbnails in this case
                    # as they won't be reliable.
                    if image_copy.mode.endswith('A') and \
                            not file_mode.endswith('A'):
                        #force RGBA when transparency gets lost
                        #eg saving TIFF format with LA mode
                        mode = image_copy.mode
                        image_copy = image_copy.convert('RGBA')
                        file_mode = imtools.save_check_mode(image_copy,
                            filename, **options)
                        if file_mode:
                            # RGBA failed
                            self.log(CONVERTED_MODE % {'mode': mode,
                                'mode_copy': file_mode, 'format': format} \
                                + '\n')
                        else:
                            # RGBA succeeded
                            self.log(CONVERTED_MODE % {'mode': mode,
                                'mode_copy': 'RGBA', 'format': format} + '\n')
                    else:
                        self.log(CONVERTED_MODE % {'mode': image_copy.mode,
                            'mode_copy': file_mode, 'format': format} + '\n')
                elif thumbnail.is_needed(image_copy, format):
                    # save thumbnail in system cache if needed
                    if thumb is None:
                        thumb = image_copy
                    thumb_info = {
                        'width': image.size[0],
                        'height': image.size[1]}
                    thumbnail.save_to_cache(filename, thumb,
                        thumb_info=thumb_info, **options)
                # copy metadata if needed (problematic for tiff)
                # FIXME: if metdata corrupts the image, there should be
                # no thumbnail
                if save_metadata:
                    self.info.save(filename, thumbdata=thumbdata)
            else:
                # save with pil>libtiff
                openImage.check_libtiff(compression)
                self.log(openImage.save_libtiff(image_copy, filename,
                    compression=compression, **options))
            if self.modify_date:
                # Update file access and modification date
                os.utime(filename, (self.modify_date, self.modify_date))
            self.append_to_report(filename, image_copy)
        except IOError, message:
            # clean up corrupted drawing
            if os.path.exists(filename):
                os.remove(filename)
            raise IOError(message)
        #update info
        if hasattr(options, 'dpi'):
            self.info['dpi'] = options['dpi'][0]

    def append_to_report(self, filename, image=None):
        report = image_to_dict(filename, image)
        report[_t('source')] = self.info['path']
        self.report_files.append(report)

    def convert(self, mode, *args, **keyw):
        """Converts all layers to a different mode."""
        for layer in self.layers.values():
            if layer.image.mode == mode:
                continue
            if mode == 'P' and imtools.has_alpha(layer.image):
                layer.image = imtools.convert(layer.image, mode, *args, **keyw)
                self.info['transparency'] = 255
            elif mode == 'P':
                layer.image = imtools.convert(layer.image, mode, *args, **keyw)
                self.info['transparency'] = None
            else:
                layer.image = imtools.convert(layer.image, mode, *args, **keyw)

    def safe_mode(self, format):
        """Convert the photo into a safe mode for this specific format"""
        layer = self.get_layer()
        layer.image = imtools.convert_save_mode_by_format(layer.image, format)

    def resize(self, size, method):
        """Resizes all layers to a different size"""
        size = (max(1, size[0]), max(1, size[1]))
        for layer in self.layers.values():
            layer.image = layer.image.resize(size, method)

    def rotate_exif(self, reverse=False):
        layers = self.layers.values()
        if reverse:
            transposition = self._exif_transposition_reverse
            self._exif_transposition_reverse = ()
        else:
            transposition, self._exif_transposition_reverse = \
                imtools.get_exif_transposition(self.info['orientation'])
        if transposition:
            for layer in layers:
                layer.image = imtools.transpose(layer.image, transposition)

    #---pil
    def apply_pil(self, function, *arg, **keyw):
        for layer in self.layers.values():
            layer.apply_pil(function, *arg, **keyw)

    #---external
    def call(self, command, check_exe=True, shell=None, size=None,
            unlock=False, output_filename=None, mode=None):
        if shell is None:
            shell = not system.WINDOWS
        #get command line
        info = self.info
        layer = self.get_layer()
        image = layer.image
        if mode != image.mode:
            image = imtools.convert(image, mode)
        if size != None and size[0] < image.size[0]:
            image = image.copy()
            image.thumbnail(size, Image.ANTIALIAS)
        #loop over input -> save to temp files
        temp_files = []
        done = []
        error = None
        for match in RE_FILE_IN.finditer(command):
            source = match.group()
            if not(source in done):
                ext = match.group(1)
                target = system.TempFile(ext)
                try:
                    imtools.save_safely(image, target.path)
                except Exception, error:
                    pass
                temp_files.append((source, target))
                done.append(source)
                if error:
                    break
        # check if we have a file_in
        # clean up in case of error
        if error:
            for source, target in temp_files:
                target.close()  # os.remove(target)
            raise error
        # loop over output
        output = None
        for index, match in \
                enumerate(RE_FILE_OUT.finditer(command)):
            if index > 0:
                # only 1 is allowed
                raise Exception('Only one file_out.* is allowed.')
            source = match.group()
            ext = match.group(1)
            output = system.TempFile(ext, output_filename)
            command = command.replace(source, system.fix_quotes(output.path))

        # tweak command line
        for source, target in temp_files:
            command = command.replace(source, system.fix_quotes(target.path))
        # execute
        system.call(command, shell=shell)
        # give back filename
        if output and not os.path.exists(output.path):
            error = True
        else:
            error = False
        for source, target in temp_files:
            target.close()  # os.remove(target)
        if error:
            raise Exception(
                _('Command did not produce an output image:\n%s')\
                % command)
        if output:
            layer.open(output.path)
            # DO NOT REMOVE image.load() or output.close will fail on windows
            layer.image.load()
            output.close()


class Layer:

    def __init__(self, filename, position=(0, 0), load=True):
        self.open(filename)
        self.position = position
        # VERY IMPORTANT
        # do not remove load option, otherwise openImage.py won't work
        # correctly with group4 tiff compression
        if load:
            self.image.load()

    def open(self, uri):
        self.image = openImage.open(uri)
        if self.image.mode in ['F', 'I']:
            # Phatch doesn't support F and I
            # FIXME: It will better to add some sort of warning here
            self.image = self.image.convert('L')

    def apply_pil(self, function, *arg, **keyw):
        self.image = function(self.image, *arg, **keyw)
