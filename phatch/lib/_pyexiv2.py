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

import re
import pyexiv2

BROKEN = 'Exif[.]Canon'
RE_BROKEN = re.compile(BROKEN)
ISSUES = 'Saving metadata to %s caused following issues:\n'
FAILED = '''
Failed to save metadata to %s:\npyexiv2: %s
Trying again by ignoring tags with following pattern:\n%s\n'''

#info taken from http://dev.exiv2.org/wiki/exiv2/Supported_image_formats
READ_EXIF = ['JPEG', 'EXV', 'CR2', 'CRW', 'MRW', 'TIFF', 'DNG', 'NEF', 'PEF',
    'ARW', 'SR2', 'ORF', 'RW2', 'RAF', 'PSD', 'JP2']

WRITE_EXIF = ['JPEG', 'EXV', 'CRW', 'DNG', 'NEF', 'PEF', 'PSD', 'JP2']
#others needs more testing
#for sure exclude TIFF for now:
#-  eg try to convert Marino_Detail02 from jpeg to tiff
#-> tiff gets corrupted
#['JPEG', 'EXV', 'CRW', 'TIFF', 'DNG', 'NEF', 'PEF', 'PSD', 'JP2']

READ_IPTC = ['JPEG', 'EXV', 'CR2', 'MRW', 'TIFF', 'DNG', 'NEF', 'PEF',
    'ARW', 'SR2', 'ORF', 'RW2', 'RAF', 'PSD', 'JP2']

WRITE_IPTC = ['JPEG', 'EXV', 'CR2', 'MRW', 'DNG', 'NEF', 'PEF',
    'ARW', 'SR2', 'ORF', 'RW2', 'RAF', 'PSD', 'JP2']
#exclude for now: 'TIFF',

READ_COMMENT = ['JPEG', 'EXV', 'CRW']

WRITE_COMMENT = ['JPEG', 'EXV', 'CRW']


def is_readable_format(format):
    """Returns True if pyexiv2 can read Exif or Iptc metadata from
    the image file ``format``."""
    return not format or format in READ_EXIF + READ_IPTC + READ_COMMENT


def is_writable_format(format):
    """Returns True if pyexiv2 can write Exif or Iptc metadata to
    the image file ``format``."""
    return not format or format in WRITE_EXIF + WRITE_IPTC + WRITE_COMMENT


def is_writable_format_exif(format):
    """Returns True if pyexiv2 can write Exif metadata to
    the image file ``format``."""
    return not format or format in WRITE_EXIF


def is_writable_format_iptc(format):
    """Returns True if pyexiv2 can write Iptc metadata to
    the image file ``format``."""
    return not format or format in WRITE_IPTC


def write_metadata(source_pyexiv2_image, target, source_format=None,
        target_format=None, thumbdata=None):
    """
    :param source_pyexiv2_image: file opened by pyexiv2
    :type source_pyexiv2_image: pyexiv2.Image
    :param target: target filename
    :type target: string
    :param source_format: source format e.g. obtained by PIL
    :type source_format: string
    :param target_format: target format e.g. obtained by PIL
    :type target_format: string
    :param thumbdata: new thumbnail (e.g. with StringIO, see :mod:`imtools`)
    :type thumbdata: string
    """
    #if there is nothing to read or write, return immediately
    if not is_writable_format(target_format):
        return ''
    #correct tags
    if not source_pyexiv2_image:
        return ''

    #make two attempts to copy metadata:
    #1. normal
    #2. exclude tags which (might) break exiv2 (eg Canon tuples)

    # This will probably be obsolete for python-pyexiv2 0.2
    # -> If that is True add a version check

    #verify if there are tags which might break exiv2
    broken_tag = None

    for tag in list(source_pyexiv2_image.exifKeys()) + \
        list(source_pyexiv2_image.iptcKeys()):
        if RE_BROKEN.match(tag):
            broken_tag = RE_BROKEN
            break

    #copy the tags
    log = ''

    #attempt to copy metadata
    try:
        warnings = _copy_metadata(source_pyexiv2_image, target,
            source_format, target_format, broken_tag, thumbdata)
        copied = True
    except Exception, message:
        copied = False

    #if metadata copied succesfully, check for warnings
    if copied:
        if warnings:
            log += ISSUES % target + warnings
    else:
        log = FAILED % (target, message, BROKEN)

    return log


def _copy_metadata(source_pyexiv2_image, target, source_format=None,
        target_format=None, broken_tag=None, thumbdata=None):
    """
    :param source_pyexiv2_image: file opened by pyexiv2
    :type source_pyexiv2_image: pyexiv2.Image
    :param target: target filename
    :type target: string
    :param source_format: source format e.g. obtained by PIL
    :type source_format: string
    :param target_format: target format e.g. obtained by PIL
    :type target_format: string
    :param broken_tag: tag which might possibly break the metadata writing
    :type broken_tag: compiled regular expression
    :param thumbdata: new thumbnail (e.g. with StringIO, see :mod:`imtools`)
    :type thumbdata: string
    """
    #read target
    target = pyexiv2.Image(target)
    target.readMetadata()
    warnings = []
    written = False
    #copy exif metadata
    if (not source_format or source_format in READ_EXIF) and \
        (not target_format or target_format in WRITE_EXIF):
        for tag in source_pyexiv2_image.exifKeys():
            if not(broken_tag and broken_tag.match(tag)):
                try:
                    #the following is more or less the same as
                    #target[tag] = source_pyexiv2_image[tag]
                    #but prevents conversions
                    target._Image__setExifTag(tag,
                        source_pyexiv2_image._Image__getExifTag(tag)[1])
                    written = True
                except Exception, message:
                    message = '%s: %s' % (tag, message)
                    warnings.append(message)
    #copy iptc metadata
    if (not source_format or source_format in READ_IPTC) and \
        (not target_format or target_format in WRITE_IPTC):
        for tag in source_pyexiv2_image.iptcKeys():
            try:
                target[tag] = source_pyexiv2_image[tag]
                written = True
            except Exception, message:
                message = '%s: %s' % (tag, message)
                warnings.append(message)
    #copy comment
    if (not source_format or source_format in READ_COMMENT) and \
        (not target_format or target_format in WRITE_COMMENT):
        try:
            target.setComment(source_pyexiv2_image.getComment())
            written = True
        except Exception, message:
            warnings.append(message)
    warnings.append(write_thumbdata(target, thumbdata))
    #save metadata (this might rise an exception)
    if written:
        target.writeMetadata()
    return '\n'.join(warnings)


def extension_to_image_format(ext):
    format = ext[1:].upper()
    if format in ['JPG', 'JPE']:
        format = 'JPEG'
    elif format == 'TIF':
        format = 'TIFF'
    return format


def read_thumbdata(image):
    try:
        return image.getThumbnailData()
    except Exception, message:
        return None


def write_thumbdata(image, thumbdata=None):
    if (thumbdata is None):
        return ''
    try:
        image.setThumbnailData(thumbdata)
        return ''
    except Exception, message:
        return unicode(message)


#def write_comment(source, comment=None, source_format=None,
#        target_format=None):
#    #TODO: phatch for now ignores jpg comments
#    #this function is not ready
#    if comment is None:
#        source.getComment()
#    if (not source_format or source_format in READ_COMMENT) and \
#        (not target_format or target_format in WRITE_COMMENT):
#        try:
#            target.setComment(comment)
#        except Exception, message:
#            return unicode(message)
#    return ''

def flush(image, thumbdata):
    warnings = [write_thumbdata(image, thumbdata)]
    try:
        image.writeMetadata()
    except Exception, message:
        warnings.append(unicode(message))
    return '\n'.join(warnings)
