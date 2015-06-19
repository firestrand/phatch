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

if __name__ == '__main__':
    import gettext
    gettext.install('test')

import glob
import os
import re

import metadata
import openImage
import unicoding

try:
    import pyexiv2
except ImportError:
    pyexiv2 = None

SEPARATOR = '_'

ALL = _('All')
SELECT = _('Select')
RE_TAG_LAST = re.compile('[.](Canon|Sony|Nikon|Leica|Panasonic)')
RE_TAG_ERROR = _('''\
The tag "%s" is not valid.
It should follow the syntax: Exif_* or Iptc_*\
''')
RE_TAG_SELECT_NOT = re.compile('[%s]|exif|iptc|#' % SEPARATOR)

MARKUP = '**%s**'
NONE = ''
THUMB_SIZE = (128, 128)


class TableImage:

    def __init__(self, filename, thumb_size=THUMB_SIZE):
        """For every image one TableImage is created. It is a helper
        class to display the metadata in a grid.

        :param filename: image filename
        :type filename: string
        :param thumb_size: size of the thumbnail
        :type thumb_size: tuple of int
        """
        self.filename = filename
        self.thumb_size = thumb_size
        self.update()

    def update(self):
        """Update the table from the image source file."""
        self.label = os.path.basename(self.filename)
        self.thumb = openImage.open_thumb(self.filename, size=THUMB_SIZE)
        info = metadata.InfoExtract(self.filename)
        info.extract_all()
        self.info = info.dump(expand=True)
        self.update_time()

    def update_time(self):
        """Update time. This time is used to check if the source file
        has changed.
        """
        self.time = self.get_time()

    def update_if_modified(self):
        """Check if the source file image has changed and update if it
        has.

        :returns: True, if source image has changed
        :rtype: bool
        """
        if self.is_modified():
            self.update()
            return True
        return False

    def is_modified(self):
        return self.get_time() > self.time

    def get_time(self):
        if os.path.exists(self.filename):
            return os.path.getmtime(self.filename)
        else:
            return self.time


class Table(object):

    def __init__(self, thumb_size=THUMB_SIZE):
        self.images = []
        self.thumb_size = thumb_size
        self.keys = []
        self.key_amount = 0
        self.row = 'key'
        self.col = 'image'

    def transpose(self):
        row = self.row
        self.row = self.col
        self.col = row

    #---open
    def open_image(self, filename, update=True, encoding=None):
        filename = unicoding.fix_filename(filename, encoding)
        if filename:
            self.images.append(TableImage(filename, self.thumb_size))
            if update:
                self.update()
        else:
            raise IOError()

    def open_images(self, paths, encoding=None):
        invalid = []
        update = False
        for path in paths:
            if os.path.isfile(path):
                #disable this if a file doesn't open to debug
                try:
                    self.open_image(path, update=False,
                        encoding=encoding)
                    update = True
                    continue
                except:
                    pass
            elif os.path.isdir(path):
                for filename in glob.glob(os.path.join(path, '*.*')):
                    try:
                        self.open_image(filename, update=False,
                            encoding=encoding)
                        update = True
                    except:
                        pass
                continue
            invalid.append(path)
        if update:
            self.update()
        return invalid

    def open_folder(self, folder):
        return self.open_images(glob.glob(os.path.join(folder, '*')))

    #---update
    def update(self):
        self._update_keys()

    def _update_keys(self, tag=None, filter=None):
        #todo category, filter
        keys = set()
        for image in self.images:
            keys = keys.union(image.info.keys())
        self.keys = self._sort_keys(keys)
        self.key_amount = len(self.keys)
        self.set_tag(tag)
        self.set_filter(filter)

    def _sort_keys(self, keys):
        keys = sorted(keys)
        first = []
        last = []
        for key in sorted(keys):
            if RE_TAG_LAST.search(key):
                last.append(key)
            else:
                first.append(key)
        return first + last

    #---image
    def delete_images(self, pos, num=1):
        self.images = self.images[:pos] + self.images[pos + 1:]

    def get_image_amount(self):
        return len(self.images)

    def get_image_label(self, index):
        return self.images[index].label

    def get_image_filename(self, index):
        return self.images[index].filename

    def set_image_label(self, index, value):
        raise Exception(_('Unable to change label.'))

    #---key
    def _add_key(self, key):
        if not(key in self.keys):
            self.keys = self.keys[:self.key_amount] + [key]\
                                + self.keys[self.key_amount:]
            self.key_amount += 1

    def add_key(self, key, value=''):
        """Add key to all images"""
        self._add_key(key)
        return self.set_key_value(key, value)

    def add_image_key(self, image, key, value=''):
        self._add_key(key)
        return self.set_image_key_value(image, key, value)

    def delete_keys(self, pos, num=1):
        keys = self.keys[pos:pos + num]
        changes = []
        for image in self.images:
            image_changes = {}
            for key in keys:
                if key in image.info:
                    image_changes[key] = None
            if image_changes:
                changes.append((image, image_changes))
        return self._write(
            changes=changes,
            error_message=_('Unable to delete tag <%s>'))

    def _delete_key(self, key):
        to_keep = []
        to_delete = []
        key_ = key + '.'  # derivate keys eg hour, day
        for index, k in enumerate(self.keys[:]):
            if (k == key or k.startswith(key_)):
                if index < self.key_amount:
                    self.key_amount -= 1
            else:
                to_keep.append(k)
        self.keys = to_keep

    def get_key_amount(self):
        return self.key_amount

    def get_key_label(self, index):
        return self.keys[index]

    def is_key_editable(self, index=0, key=None):
        if not pyexiv2:
            return False
        if key is None:
            key = self.keys[index]
        for image in self.images:
            if metadata.is_editable_tag(key):
                return True
        return False

    def is_key_empty(self, key):
        for image in self.images:
            if key in image.info:
                return False
        return True

    def set_key_label(self, index, value):
        # new tag -> replace new & delete current
        if not metadata.RE_PYEXIV2_TAG.match(value):
            # return error
            return RE_TAG_ERROR % value
        key = self.keys[index]
        log = self._write(
            changes=[(image, {value:image.info[key], key:None})
                for image in self.images if key in image.info],
            error_message=_('Unable to rename tag <%s>'))
        if not log:
            self.keys[index] = value
        return log

    #---cell
    def delete_cell(self, row, col):
        return self.set_cell_value(row, col, None)

    def get_cell_value(self, row, col):
        key, image = self._get_key_image(row, col)
        return image.info.get(key, NONE)

    def is_cell_empty(self, row, col):
        key, image = self._get_key_image(row, col)
        return not(key in image.info)

    def is_cell_editable(self, row, col):
        key, image = self._get_key_image(row, col)
        return pyexiv2 and self.is_key_editable(key=key)

    def is_cell_deletable(self, row, col):
        return self.is_cell_editable(row, col) \
            and not self.is_cell_empty(row, col)

    def is_image_editable(self, image):
        return False

    def set_cell_value(self, row, col, value):
        key, image = self._get_key_image(row, col)
        if value == self.get_cell_value(row, col):
            return
        return self.set_image_key_value(image, key, value)

    def set_image_key_value(self, image, key, value):
        if not(value is None):
            value = unicode(value)
        return self._write(
            changes=((image, {key: value}), ),
            error_message=_('Unable to save tag <%s>'))

    def set_key_value(self, key, value):
        changes = []
        for image in self.images:
            if not(value == image.info.get(key, None)):
                changes.append((image, {key: value}))
        return self._write(
            changes=changes,
            error_message=_('Unable to save tag <%s>'))

    #row, col specific
    def _get_key_image(self, row, col):
        if self.row == 'key':
            return self.keys[row], self.images[col]
        else:
            return self.keys[col], self.images[row]

    def __getattr__(self, attr):
        new_attr = attr.replace('row', self.row).replace('col', self.col)
        if new_attr in Table.__dict__:

            def method(*args, **keyw):
                return Table.__dict__[new_attr](self, *args, **keyw)

            return method
        raise AttributeError(attr)

    def _write(self, changes, error_message):
        """Write changes to the image files with pyexiv2.

        :param changes: ((image, {key: value}), )
        :type changes: tuple
        :param error_message: with %s interpolation
        :type error_message: string
        :returns: error log
        :rtype: string
        """
        log = []
        keys_to_delete = set()
        for image, image_changes in changes:
            # try to save to image file
            try:
                exiv2_image = pyexiv2.Image(image.filename)
                exiv2_image.readMetadata()
                for key, value in image_changes.items():
                    exiv2_key = str(key.replace(SEPARATOR, '.'))
                    if value:
                        exiv2_image[exiv2_key] = value
                    else:
                        del exiv2_image[exiv2_key]
                exiv2_image.writeMetadata()
            except Exception, error:
                log.append('%s:\n%s'\
                    % (error_message % key, unicode(error)))
                continue
            # successfully saved to image file (wait until now)
            image.update_time()
            if value:
                image.info[key] = value
                metadata.InfoExtract.expand_var(image.info, key,
                    metadata.convert_from_string(value))
            else:
                del image.info[key]
                keys_to_delete.add(key)
        for key in keys_to_delete:
            if self.is_key_empty(key):
                self._delete_key(key)
        return '\n'.join(log)

    #---selecting
    def set_tag(self, tag):
        if not(tag is None):
            self._tag = tag
        if self._tag == ALL:
            self.keys.sort()
            self.key_amount = self.key_amount_tag = len(self.keys)
            return
        elif self._tag == SELECT:

            def condition(key):
                return not RE_TAG_SELECT_NOT.search(key)

        else:
            prefix = '%s%s' % (self._tag, SEPARATOR)

            def condition(key):
                return key.startswith(prefix)

        self._select(condition)
        self.key_amount_tag = self.key_amount

    def set_filter(self, filter=''):
        if not(filter is None):
            self._filter = filter
        filter = self._filter.lower()

        def condition(key):
            return filter in key.lower()

        self._select(condition, as_filter=True)

    def _select(self, condition, as_filter=False):
        # we need to iterate over a copy
        if as_filter:
            keys = self.keys[: self.key_amount_tag]
        else:
            keys = self.keys[:]
        # enumerate
        selected = []
        to_delete = []
        for index, key in enumerate(keys):
            if condition(key):
                selected.append(key)
                to_delete.insert(0, index)
        # delete
        for index in to_delete:
            del self.keys[index]
        # place selection in front
        self.keys = self._sort_keys(selected) + self.keys
        self.key_amount = len(selected)
