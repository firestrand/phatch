# Phatch - Photo Batch Processor
# Copyright (C) 2009 Nadia Alramli, Stani (www.stani.be)
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

import filecmp
import os
import shutil


def system_path(path):
    """Convert a path string into the correct form"""
    return os.path.abspath(os.path.normpath(path))


def create_path(path):
    """Create a path if it doesn't already exist"""
    if not os.path.exists(path):
        os.makedirs(path)


def remove_path(path):
    """Delete a file or a direcotry"""
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)


def replace_all(input, replace_map):
    """Replace multiple words in a string"""
    for key, value in replace_map:
        input = input.replace(key, value)
    return input


def write_file(path, data):
    """Write to a file"""
    f = open(path, 'w')
    f.write(data)
    f.close()


def file_name(path):
    """Get the file name from path without its extension"""
    if os.path.isdir(path):
        return ''
    return os.path.basename(path).partition('.')[0]


def file_extension(path):
    """Get the file extension for path"""
    if os.path.isdir(path):
        return ''
    return os.path.basename(path).partition('.')[-1]


def indexed_name(name, index):
    """Return an indexed name"""
    if index:
        return '%s_%s' % (name, index)
    return name


def compare(file1, file2):
    """Compare two files"""
    return filecmp.cmp(file1, file2)


def analyze(original, other):
    """Analyze the difference between the two images"""
    result = {}
    from lib import openImage
    original_image = openImage.open(original)
    other_image = openImage.open(other)
    if other_image.mode != original_image.mode:
        result['reason'] = 'Mismatching modes %s != %s' % (
            other_image.mode,
            original_image.mode)
    elif other_image.size != original_image.size:
        result['reason'] = 'Mismatching sizes %s != %s' % (
            other_image.size,
            original_image.size)
    elif original_image.info != other_image.info:
        diff = info_diff(original_image.info, other_image.info)
        result['reason'] = 'Mismatching info\n\t%s' % diff
    elif not match_metadata(original, other):
        result['reason'] = 'Mismatching metadata'
    else:
        diff_image = image_diff(original_image, other_image)
        if diff_image:
            result['reason'] = 'Mismatching pixels'
            result['diff'] = diff_image
        else:
            result['reason'] = 'Unidentifiable difference'
    return result


def info_diff(original_info, other_info):
    """Comparing image info"""
    if original_info == other_info:
        return
    result = {'extra': [], 'missing': [], 'diff': []}
    keys = sorted(list(set(original_info.keys() + other_info.keys())))
    for key in keys:
        original_value = original_info.get(key)
        other_value = other_info.get(key)
        if not original_value:
            result['extra'].append(key)
        elif not other_value:
            result['missing'].append(key)
        elif original_value != other_value:
            result['diff'].append(
                '%s should be %s not %s' % (key, original_value, other_value))
    diff = []
    if result['missing']:
        diff.append('Missing key: %s' % ', '.join(result['missing']))
    if result['extra']:
        diff.append('Extra key: %s' % ', '.join(result['extra']))
    if result['diff']:
        diff.append('Difference: %s' % ', '.join(result['diff']))
    return '\n\t'.join(diff)


def image_diff(im1, im2):
    """Return the diff of two images"""
    from PIL import Image, ImageMath
    r1, g1, b1, a1 = im1.convert('RGBA').split()
    r2, g2, b2, a2 = im2.convert('RGBA').split()
    diff_image = ImageMath.eval(
        """convert(
            max(
                max(
                    max(abs(r1 - r2), abs(g1 - g2)),
                    abs(b1 - b2)
                ),
                abs(a1 - a2)
            ), 'L')""",
        r1=r1,
        r2=r2,
        g1=g1,
        g2=g2,
        b1=b1,
        b2=b2,
        a1=a1,
        a2=a2)
    if ImageMath.eval('not(image)', image=diff_image):
        return
    return diff_image


def match_metadata(image1_path, image2_path):
    """Compare images metadata"""
    try:
        import pyexiv2
        image1 = pyexiv2.Image(image1_path)
        image1.readMetadata()
        image2 = pyexiv2.Image(image2_path)
        image2.readMetadata()
        metadata1 = sorted([(key, image1[key]) for key in image1.exifKeys()])
        metadata2 = sorted([(key, image2[key]) for key in image2.exifKeys()])
        return metadata1 == metadata2
    except IOError:
        return True


def banner(title, width=50):
    """Textual banner"""
    return '%s\n*%s*\n%s\n' % ('*' * 50, title.center(48, ' ') + '*' * 50)


def product(*args, **kwds):
    """Cartesian product of input iterables."""
    # Copyed from python 2.6 docs
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
    pools = map(tuple, args) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x + [y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)


def product_map(*args, **kwds):
    generator = kwds.get('generator', list)
    return product(*[generator(arg) for arg in args])


def inline_if(condition, when_true, when_false):
    if condition:
        return when_true
    else:
        return when_false
