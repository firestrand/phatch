# Copyright (C) 2009 www.stani.be
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

import os
import re

import Image

import imtools
import system
import thumbnail

try:
    import pyexiv2
except:
    pyexiv2 = None


def check_libtiff(compression):
    if not(open_libtiff or compression.lower() in ['raw', 'none']):
        raise Exception('Libtiff tools are needed for "%s" compression'\
            % compression)


def open(uri):
    format = imtools.get_format_filename(uri)
    local = not system.is_www_file(uri)
    # svg, pdf, ...
    if local:
        image = open_image_without_pil(uri, WITHOUT_PIL)
        if image:
            image.info['Format'] = image.format
            image.format = format
            return image
    # pil
    try:
        image = open_image_with_pil(uri)
        ok = True
    except IOError, message:
        ok = False
    # interlaced png
    if ok and not(Image.VERSION < '1.1.7' and
            image.format == 'PNG' and 'interlace' in image.info):
        return image
    # png, tiff (which pil can only handle partly)
    if local:
        image = open_image_without_pil(uri, ENHANCE_PIL)
        if image:
            image.info['Format'] = image.format
            image.format = format
            return image
    else:
        image = None
    if image is None:
        raise IOError(message)
    return imtools.open_image(uri)


def open_image_exif(uri):
    return imtools.transpose_exif(open(uri))


def open_image_exif_thumb(uri):
    if pyexiv2:
        try:
            pyexiv2_image = pyexiv2.Image(uri)
            pyexiv2_image.readMetadata()
            thumb_data = pyexiv2_image.getThumbnailData()
            if thumb_data:
                return imtools.open_image_data(thumb_data)
        except Exception, details:
            pass
    return open_image_exif(uri)


def open_thumb(filename, image=None, open_image=open_image_exif_thumb,
        size=thumbnail.SIZE, save_cache=True):
    return thumbnail.open(filename=filename, image=image,
        open_image=open_image, size=size,
        save_cache=save_cache)


def open_image_with_pil(uri):
    image = imtools.open_image(uri)
    #types which PIL can open, but not load
    compression = image.info.get('compression', 'none')
    if hasattr(compression, 'startswith') and \
            compression.startswith('group'):
        # tiff image with group4 compression
        check_libtiff('g4')  # raise exception if openImage not present
        image = open_libtiff(uri)
    return image


def open_image_without_pil(filename, method_register):
    """Try to open images which PIL can't handle."""
    extension = system.file_extension(filename)
    if extension in method_register.extensions:
        methods = method_register.get_methods(extension)
        for open_method in methods:
            image = open_method(filename)
            if image:
                return image


def open_image_with_command(filename, command, app, extension='png',
        temp_ext=None):
    """Open with an external command (such as Inkscape, dcraw, imagemagick).

    :param filename: filename, from which a temporary filename will be derived
    :type filename: string
    :param command: conversion command with optional temp file interpolation
    :type command: string
    :param extension: file type
    :type extension: string
    :param temp_ext:

        if a temp file can not be specified to the command (eg dcraw),
        give the file extension of the command output

    :type temp_ext: string
    """
    temp = None
    temp_file = None
    if temp_ext:
        # eg dcraw
        temp_file = os.path.splitext(filename)[0] + '.' + temp_ext
    else:
        # imagemagick, ...
        if not extension.startswith('.'):
            extension = '.' + extension
        temp = system.TempFile(extension)
        temp_file = temp.path
        command.append(temp_file)
    try:
        output, error = system.shell(command)
        if os.path.exists(temp_file):
            image = Image.open(temp_file)
            image.load()  # otherwise temp file can't be deleted
            image.info['Convertor'] = app
            return image
    finally:
        if temp:
            temp.close(force_remove=False)
        elif temp_ext and os.path.exists(temp_file):
            os.remove(temp_file)
    message = _('Could not open image with %s.') % app + \
        '\n\n%s: %s\n\n%s: %s\n\n%s: %s' % \
        (_('Command'), command, _('Output'), output, _('Error'), error)
    raise IOError(message)


#libtiff

TIFFINFO = system.find_exe("tiffinfo")
TIFFCP = system.find_exe("tiffcp")

if TIFFINFO and TIFFCP:

    RE_TIFF_FIELD = re.compile('\s+(.*?):\s+(.*?)\n')
    RE_TIFF_FIELD_IMAGE = re.compile(' Image (.*?):\s+(.*?)$')

    TIFF_COMPRESSION = {
        'CCITT Group 3': 'g3',
        'CCITT Group 4': 'g4',
        'Deflate': 'zip',
        'JPEG': 'jpeg',
        'LZW': 'lzw',
        'PackBits': 'packbits',
        'None': 'none',
    }

    TIFF_COMPRESSION_TYPES = TIFF_COMPRESSION.values()
    TIFF_COMPRESSION_TYPES.sort()

    def get_info_libtiff(filename):
        """Get tiff info of a file with ``tiffinfo``, which needs to be
        installed on your system.

        :param filename: name of tiff image file
        :type filename: string
        :returns: info about the file
        :rtype: dict
        """
        result = {}

        def set(key, value):
            key = 'libtiff.' + key.lower().replace(' ', '.')
            if not (key in result):
                result[key] = value

        source, err = system.shell((TIFFINFO, filename))
        for match in RE_TIFF_FIELD.finditer(source):
            value = match.group(2)
            again = RE_TIFF_FIELD_IMAGE.search(value)
            if again:
                set('Image %s' % again.group(1), again.group(2))
                set(match.group(1), value[:again.start()])
            else:
                set(match.group(1), value)
        if not result:
            raise IOError('Not a TIFF or MDI file, bad magic number.')
        result['compression'] = \
            TIFF_COMPRESSION[result['libtiff.compression.scheme']]
        return result

    def open_libtiff(filename):
        """Opens a tiff file with ``tiffcp``, which needs to be installed
        on your system.

        :param filename: name of tiff image file
        :type filename: string
        :returns: PIL image
        :rtype: Image.Image
        """
        # get info
        info = get_info_libtiff(filename)
        # extract
        temp = system.TempFile()
        command = (TIFFCP, '-c', 'none', '-r', '-1', filename, temp.path)
        try:
            returncode = system.shell_returncode(command)
            if returncode == 0:
                image = Image.open(temp.path)
                image.load()  # otherwise temp file can't be deleted
                image.info.update(info)
                image.info['Convertor'] = 'libtiff'
                return image
        finally:
            temp.close(force_remove=False)
        raise IOError('Could not extract tiff image with tiffcp.')

    def save_libtiff(image, filename, compression=None, **options):
        """Saves a tiff compressed file with tiffcp.

        :param image: PIL image
        :type image: Image.Image
        :param filename: name of tiff image file
        :type filename: string
        :param compression: g3, g4, jpeg, lzw, tiff_lzw
        :type compression: string
        :returns: log message
        :rtype: string
        """
        if compression in ['raw', 'none']:
            image.save(filename, 'tiff', **options)
            return ''
        if compression is None:
            compression = image.info['compression']
        elif compression in ['g3', 'g4'] and image.mode != '1':
            image = image.convert('1')
        if compression == 'jpeg':
            option = ['-r', '16']
            if image.mode == 'RGBA':
                image = image.convert('RGB')
        else:
            option = []
            if compression == 'tiff_lzw':
                compression = 'lzw'
        temp = system.TempFile()
        try:
            image.save(temp.path, 'tiff', **options)
            input = [TIFFCP, temp.path, '-c', compression]
            if option:
                input.extend(option)
            input.append(filename)
            out, err = system.shell(input)
        finally:
            temp.close()
        if out or err:
            return 'Subprocess "tiffcp"\ninput:\n%s\noutput:\n%s%s\n'\
                % (input, out, err)
        return ''

else:
    open_libtiff = save_libtiff = get_info_libtiff = None


# inkscape

INKSCAPE = system.find_exe('inkscape')

if INKSCAPE:

    def open_inkscape(filename):
        """Open an Inkscape file."""
        command = [INKSCAPE, filename, '-e']
        return open_image_with_command(filename, command, 'inkscape')

else:

    open_inkscape = None

# imagemagick

IMAGEMAGICK_CONVERT = system.find_exe('convert')
IMAGEMAGICK_IDENTIFY = system.find_exe('identify')

if IMAGEMAGICK_CONVERT:

    def open_imagemagick(filename):
        """Open an image with Imagemagick."""
        command = [IMAGEMAGICK_CONVERT, filename, '-interlace', 'none',
            '-background', 'none', '-flatten']
        return open_image_with_command(filename, command, 'imagemagick')

else:

    open_imagemagick = None


if IMAGEMAGICK_IDENTIFY:

    def verify_imagemagick(filename):
        """Verify an image with Imagemagick."""
        command = (IMAGEMAGICK_IDENTIFY, '-quiet', filename)
        retcode = system.shell_returncode(command)
        if retcode == 0:
            return True
        return False

else:

    verify_imagemagick = None


# xcf tools (gimp)

XCF2PNG = system.find_exe('xcf2png')
XCFINFO = system.find_exe('xcfinfo')
if XCF2PNG:

    def open_xcf(filename):
        """Open a gimp file."""
        command = [XCF2PNG, filename, '-o']
        return open_image_with_command(filename, command, 'xcf2png')

else:

    open_xcf = None

if XCFINFO:

    def verify_xcf(filename):
        """Verify a gimp file."""
        command = (XCFINFO, '-u', filename)
        retcode = system.shell_returncode(command)
        if retcode == 0:
            return True
        return False

else:

    verify_xcf = None


# dcraw

DCRAW = system.find_exe('dcraw')

if DCRAW:

    def open_dcraw(filename):
        """Open a camera raw image file."""
        command = [DCRAW, '-w', filename]
        return open_image_with_command(filename, command, 'xcf2png',
            temp_ext='ppm')

    def verify_dcraw(filename):
        """Verify a camera raw image file."""
        command = (DCRAW, '-i', filename)
        retcode = system.shell_returncode(command)
        if retcode == 0:
            return True
        return False

else:

    open_dcraw = None
    verify_dcraw = None


# register methods

# IMPORTANT: the order of registering is important, the method
# which is first registered gets more priority

RAW_EXTENSIONS = ['arw', 'cr2', 'crw', 'dcr', 'dng', 'erf', 'kdc', 'nef',
    'orf', 'pef', 'raf', 'sr2', 'srf', 'x3f']

WITHOUT_PIL = system.MethodRegister()
WITHOUT_PIL.register(['xcf'], open_xcf)
WITHOUT_PIL.register(RAW_EXTENSIONS, open_dcraw)
WITHOUT_PIL.register(['svg', 'svgz'], open_inkscape)
WITHOUT_PIL.register(['ai', 'avi', 'cmyk', 'cmyka', 'dpx', 'eps', 'exr', 'mng',
    'mov', 'mpeg', 'mpg', 'otf', 'pdf', 'pict', 'ps', 'psd', 'svg', 'svgz',
    'ttf', 'wmf', 'xcf', 'xpm', 'ycbcr', 'ycbcra', 'yuv'],
    open_imagemagick)

# This is for file formats which PIL can read, but not all subformats
# For example: compressed tiff files

ENHANCE_PIL = system.MethodRegister()
ENHANCE_PIL.register(['tiff'], open_libtiff)
ENHANCE_PIL.register(['png'], open_imagemagick)

VERIFY_WITHOUT_PIL = system.MethodRegister()
VERIFY_WITHOUT_PIL.register(['xcf'], verify_xcf)
VERIFY_WITHOUT_PIL.register(RAW_EXTENSIONS, verify_dcraw)
VERIFY_WITHOUT_PIL.register(['eps', 'psd', 'pdf', 'svg', 'svgz', 'wmf', 'xcf'],
    verify_imagemagick)


def verify_image(info_file, valid, invalid,
        method_register=VERIFY_WITHOUT_PIL):
    extension = system.file_extension(info_file['path'])
    if extension in method_register.extensions:
        verify_image_without_pil(info_file, method_register, valid, invalid)
    else:
        verify_image_with_pil(info_file, valid, invalid)


def verify_image_with_pil(info_file, valid, invalid):
    try:
        im = open(info_file['path'])
        #if info has 'Convertor', the image is not opened by PIL
        #and already loaded and verified
        if not ('Convertor' in im.info):
            im.verify()
        valid.append(info_file)
        return True
    except Exception, error:
        invalid.append(info_file['path'])
        return False


def verify_image_without_pil(info_file, method_register, valid, invalid):
    """Try to verify images which PIL can't handle."""
    extension = system.file_extension(info_file['path'])
    methods = method_register.get_methods(extension)
    for verify_method in methods:
        if verify_method(info_file['path']):
            valid.append(info_file)
            return True
    invalid.append(info_file['path'])
    return False


if __name__ == '__main__':
    print TIFF_COMPRESSION_TYPES
    filename = '/home/stani/Downloads/0009.tif'
    image = open(filename)
    print(image.info)
    #save(image.rotate(10), filename + '.tif', compression='g4')
