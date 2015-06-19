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

"""The most important functions of this module are
``open`` and ``save_to_cache``.

For the freedesktop specifications, it follows:
http://jens.triq.net/thumbnail-spec/index.html
"""

import hashlib
import os
import stat
import tempfile
import urllib

from PIL import Image

import imtools
import system


def ensure_path(*paths):
    path = os.path.join(*paths)
    if not os.path.exists(path):
        os.mkdir(path)
    return path

CHECKBOARD = {}
FREEDESKTOP = True  # os.path.exists(FREEDESKTOP_PATH)
THUMB_INFO = {'software': 'Phatch'}


def get_mtime(filename, file_stat=None):
    if file_stat is None:
        file_stat = os.stat(filename)
    return file_stat[stat.ST_MTIME]


def get_filesize(filename, file_stat=None):
    if file_stat is None:
        file_stat = os.stat(filename)
    return file_stat[stat.ST_SIZE]


if FREEDESKTOP:

    import PngImagePlugin

    FREEDESKTOP_SIZE = {
        'normal': (128, 128),
        'large': (256, 256)}
    SIZE = FREEDESKTOP_SIZE['normal']

    FREEDESKTOP_PATH = {
        'normal': os.path.expanduser('~/.thumbnails/normal'),
        'large': os.path.expanduser('~/.thumbnails/large')}
    if os.path.exists(FREEDESKTOP_PATH['normal']):
        ensure_path(FREEDESKTOP_PATH['large'])
    else:
        #simulate freedesktop with a temp dir
        thumb_path = ensure_path(tempfile.gettempdir(), 'thumbnails')
        FREEDESKTOP_PATH = {
            'normal': ensure_path(thumb_path, 'normal'),
            'large': ensure_path(thumb_path, 'large')}

    def get_uri(filename):
        """Get uri of filename.

        :param filename: filename
        :type filename: string
        :returns: uri
        :rtype: string

        >>> get_uri('/home/user/test.png')
        'file:///home/user/test.png'
        """
        if filename.startswith('file://'):
            return filename
        abspath = os.path.abspath(filename)
        try:
            return 'file://%s' % urllib.pathname2url(abspath.encode('utf-8'))
        except:
            # fallback if fails on unicode
            return 'file://%s' % abspath

    def get_hash(filename):
        """Get md5 hash of uri of filename.

        :param filename: filename
        :type filename: string
        :returns: hash
        :rtype: string

        >>> get_hash('file:///home/user/test.png')
        '03223f4f10458a8b5d14327f3ae23136'
        """
        return hashlib.md5(get_uri(filename)).hexdigest()

    def get_freedesktop_size_label(size):
        """Returns the freedesktop size label.

        :param size: requested size of the thumbnail
        :type size: tuple of int
        :returns: size label
        :rtype: string

        >>> get_freedesktop_size_label((128, 128))
        'normal'
        >>> get_freedesktop_size_label((128, 129))
        'large'
        """
        thumb_width, thumb_height = size
        if thumb_width < 129 and thumb_height < 129:
            return 'normal'
        elif thumb_width < 257 and thumb_height < 257:
            return 'large'
        return ''

    def get_freedesktop_filename(filename, size_label='normal'):
        """Get filename of freedekstop thumbnail.

        :param filename: image filename
        :type filename: string
        :param size_label: ``'normal'`` or ``'large'``
        :type size_label: string
        :returns: thumbnail filename
        :rtype: string
        """
        filename = os.path.join(FREEDESKTOP_PATH[size_label],
            get_hash(filename) + ".png")
        return filename

    def get_freedesktop_pnginfo(filename, image=None, thumb_info=None):
        """Gets png metadata for the thumbnail.

        :param filename: image filename
        :type filename: string
        :returns: png info
        :rtype: PngImagePlugin.PngInfo
        """
        full_info = THUMB_INFO.copy()
        if thumb_info:
            full_info.update(thumb_info)
        file_stat = os.stat(filename)
        info = PngImagePlugin.PngInfo()
        info.add_text('Thumb::URI', get_uri(filename))
        info.add_text('Thumb::MTime', str(get_mtime(filename, file_stat)))
        info.add_text('Thumb::Size', str(get_filesize(filename, file_stat)))
        if 'software' in full_info:
            info.add_text('Thumb::Software', full_info['software'])
        if 'height' in full_info:
            info.add_text('Thumb::Image::Height', str(full_info['height']))
        elif image:
            info.add_text('Thumb::Image::Height', str(image.size[1]))
        if 'width' in full_info:
            info.add_text('Thumb::Image::Width', str(full_info['width']))
        elif image:
            info.add_text('Thumb::Image::Width', str(image.size[0]))
        return info

    def _open(filename, image=None, open_image=Image.open,
            size=SIZE, save_cache=True, **keyw):
        """Open image for thumbnail of the image specified by filename.

        .. note::

            This does not return an image yet with the size. This
            needs to be combined with the :func:`open`.

        :param filename: image filename
        :type filename: string
        :param image: optionally pass the already opened image
        :type image: Image
        :param open_image: alternative open method
        :type open_image: function
        :param size: size ``(width, height)`` of the thumbnail
        :type size: tuple
        :param save_cache: save opened thumbnail to cache cache
        :type save_cache: bool
        """
        # is the thumbnail small enough for the cache?
        size_label = get_freedesktop_size_label(size)
        if size_label:
            # retrieve the filename of the cached thumbnail if desirable
            thumb_filename = get_freedesktop_filename(filename, size_label)
            if os.path.isfile(thumb_filename) and \
                    not needs_update(filename, thumb_filename=thumb_filename):
                # png -> open with pil immediately, no need for open_image
                return Image.open(thumb_filename)
        if image is None:
            image = open_image(filename)
        if size_label and save_cache:
            return _save_to_cache(filename, image, size, size_label)
        return image

    def _save_to_cache(filename, image, size=SIZE,
            size_label=None, thumb_info=None, **options):
        """Save thumb as thumbnail for image filename. The size of the
        thumbnails should be a cache thumbnail size.

        :param filename: image filename
        :type filename: string
        :param thumb: thumb image
        :type thumb: Image
        :param thumb_filename: thumb filename
        :type thumb_filename: string
        :param size: size ``(width, height)`` of the thumbnail
        :type size: tuple
        :param size_label: ``'normal'``, ``'large'`` or ``None``
        :type size_label: string
        :returns: image or thumb
        :rtype: Image
        """
        thumb = imtools.convert_save_mode_by_format(image, 'PNG')
        if size_label is None:
            size_label = get_freedesktop_size_label(size)
        pnginfo = get_freedesktop_pnginfo(filename, thumb_info=thumb_info)
        if not size_label:
            # too large -> make thumbnail
            thumb.thumbnail(size, Image.ANTIALIAS)
        thumb_cache = thumb.copy()
        # save large thumbnail
        if size_label == 'large':
            thumb, thumb_cache = _save_to_cache_size('large', filename,
                size_label, thumb, thumb_cache, size, pnginfo,
                **options)
        # save normal thumbnail
        thumb, thumb_cache = _save_to_cache_size('normal', filename,
            size_label, thumb, thumb_cache, size, pnginfo,
            **options)
        return thumb

    def _save_to_cache_size(cache_size_label, filename, size_label,
            thumb, thumb_cache, size, pnginfo, **options):
        thumb_cache.thumbnail(FREEDESKTOP_SIZE[cache_size_label],
            Image.ANTIALIAS)
        temp = system.TempFile('.png')
        imtools.save(thumb_cache, temp.path, pnginfo=pnginfo, **options)
        thumb_filename = get_freedesktop_filename(filename, cache_size_label)
        temp.close(dest=thumb_filename)
        os.chmod(thumb_filename, 0600)
        if cache_size_label == size_label:
            # make thumbnail as it is smaller than this thumb cache size
            thumb = thumbnail(thumb_cache, size)
        return thumb, thumb_cache

    def delete(filename):
        for size_label in FREEDESKTOP_SIZE:
            try:
                os.remove(get_freedesktop_filename(filename, size_label))
            except:
                pass

    def needs_update(filename, size_label='normal', thumb_filename=None):
        if thumb_filename is None:
            thumb_filename = get_freedesktop_filename(filename, size_label)
        if not os.path.exists(thumb_filename):
            return True
        try:
            thumb = Image.open(thumb_filename)
        except:
            return True
        try:
            thumb_mtime = thumb.info['Thumb::MTime']
        except KeyError:
            return True
        file_mtime = str(get_mtime(filename))
        return file_mtime != thumb_mtime


else:

    _save_to_cache = None

    def _open(filename, image=None, open_image=Image.open, **keyw):
        """Open image for thumbnail of the image specified by filename.

        .. note::

            This does not return an image yet with the size. This
            needs to be combined with the :func:`after_open` as in the
            :func:`open`.

        :param filename: image filename
        :type filename: string
        :param image: optionally pass the already opened image
        :type image: Image
        :param open_image: alternative open method
        :type open_image: function
        :returns: image
        :rtype: Image
        """
        if image is None:
            return open_image(filename)
        return image

    def delete(filename):
        pass


def is_needed(image, format='JPEG'):
    """Small images don't need thumbnails

    :param image: image
    :type image: pil.Image
    :param format: image format
    :type format: string
    :returns: ``True`` if large enough, ``False`` otherwise
    :rtype: bool

    >>> im = Image.new('L', (128, 128))
    >>> is_needed(im)
    False
    >>> im = Image.new('L', (1024, 1024))
    >>> is_needed(im)
    True
    """
    if format == 'JPEG':
        #be more strict for jpeg (because of lossless compression)
        return image.size[0] > 512 or image.size[1] > 512
    else:
        return image.size[0] > SIZE[0] or image.size[1] > SIZE[1]


def thumbnail(image, size=SIZE, checkboard=False, copy=True):
    """Makes a not in place thumbnail

    :param image: image
    :type image: pil.Image
    :param size: thumbnail size
    :type size: tuple of int
    :returns: thumbnail
    :rtype: Image

    >>> im = Image.new('L', (1024, 1024))
    >>> thumbnail(im, (128, 128)).size
    (128, 128)
    """
    if copy:
        thumb = image.copy()
    #skip if thumb is smaller than requested size
    if thumb.size[0] > size[0] or thumb.size[1] > size[1]:
        thumb.thumbnail(size, Image.ANTIALIAS)
    if checkboard:
        return imtools.add_checkboard(thumb)
    return thumb


def get_format_data(image, format, size=SIZE, checkboard=False):
    """Convert the image in the file bytes of the image at a certain
    size. By consequence this byte data is different for the chosen
    format (``JPEG``, ``TIFF``, ...).

    .. see also:: :func:`get_format_data`

    :param image: source image
    :type impage: pil.Image
    :param format: image file type format
    :type format: string
    :param size: target thumbnail size
    :type size: tuple of int
    :returns: byte data of the thumbnail
    """
    thumb = thumbnail(image, size, checkboard)
    return imtools.get_format_data(thumb, format)


def save_to_cache(filename, image=None, open_image=imtools.open_image_exif,
        thumb_info=None, **options):
    """Save the thumb of image as a thumbnail for specified file.

    This is called by the _open function, which requires that it
    returns the thumb.

    :param filename: filename of the image
    :type filename: string
    :param image: generate thumb from pil image directly (optional)
    :type image: pil.Image
    :param open_image: alternative for Image.open
    :type open_image: function
    """
    #is save_to_cache implemented for the current platform?
    if _save_to_cache:
        #is image opened already?
        if image is None:
            image = open_image(filename)
        _save_to_cache(filename, image, thumb_info=thumb_info, **options)


def open(filename, image=None, open_image=imtools.open_image_exif,
    size=SIZE, save_cache=True):
    """Retrieves a thumbnail from a file. It will only use the cache
    if ``size`` is smaller than the cache thumbnail sizes.

    On Linux it will try to load it from the freedesktop thumbnail
    cache, which makes it much faster. Otherwise it will generate the
    thumbnail.

    :param filename: filename of the image
    :type filename: string
    :param image: generate thumb from pil image directly (optional)
    :type image: pil.Image
    :param open_image: alternative for Image.open
    :type open_image: function
    :param size: size of the thumbnail
    :type size: tuple of int
    :param save_cache: save thumbnail in cache (linux only)
    :type save_cache: bool
    :returns: thumbnail
    :rtype: pil.Image
    """
    thumb = _open(filename=filename, image=image, open_image=open_image,
        size=size, save_cache=save_cache)
    if thumb.size[0] > size[0] or thumb.size[1] > size[1]:
        #we need a smaller thumb
        return thumbnail(thumb, size, checkboard=True)
    #add checkerboard for transparant images
    return imtools.add_checkboard(thumb)
