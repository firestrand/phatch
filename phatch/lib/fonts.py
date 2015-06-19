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

import glob
import os
import re
import subprocess
import sys
import system

from lib import safe

USER_FONTS_CACHE_PATH = None
ROOT_FONTS_CACHE_PATH = None
WRITABLE_FONTS_CACHE_PATH = None

_FONT_DICTIONARY = None
_FONT_NAMES = None

re_WORD = re.compile('([A-Z0-9]+[^A-Z0-9]*)', re.UNICODE)
re_SPACE = re.compile('_|\W+', re.UNICODE)
LOCATE = [
    ['locate', '-i', '.ttf', '.otf'],
    ['find', '/', '-iname', '*.ttf', '-o', '-name', '*.otf'],
]

#collect_fonts (system dependent)
if sys.platform.startswith('win'):
    #3thrd party module in other
    from other.findsystem import findFonts

    def collect_fonts():
        """Collect a list of all font filenames."""
        return findFonts()
else:
    #better unix alternative for collect_fonts/findFonts
    #presume findutils are present
    if not system.find_exe('locate'):
        sys.exit(_('Please install "%s" first.') % 'locate')

    def locate_files(command):
        return subprocess.Popen(command,
            stdout=subprocess.PIPE).stdout.read().splitlines()

    def collect_fonts():
        """Collect a list of all font filenames."""
        #try first with locate otherwise with find
        for command in LOCATE:
            try:
                if system.find_exe(command[0]):
                    output = locate_files(command)
                    files = [line for line in output
                        if line[-4:].lower() in ['.ttf', '.otf']]
                    if files:
                        return files
            except:
                pass
        from other.findsystem import findFonts
        return findFonts()


def basename(font_file):
    return os.path.splitext(os.path.basename(font_file))[0]


def name(x):
    """\
    Split camelcase filenames and ensure title case.

    >>> name('ArialBlack italic')
    'Arial Black Italic'
    """
    words = ' '.join(re_SPACE.split(' '.join(re_WORD.split(x))))
    return words.replace('  ', ' ').title().strip()


def _font_name(font_name, base='xxx'):
    """\
    Expand an abbreviated font name.
    """
    if font_name == 'Ariblk':
        return 'Arial', 'Arial Black'
    elif font_name == 'Cour':
        return 'Cour', 'Courier New'
    elif font_name == 'Micross':
        return 'Microsoft Sans Serif', 'Microsoft Sans Serif Regular'
    elif font_name == 'Lucon':
        return 'Lucida', 'Lucida Console'
    elif font_name == 'L 10646':
        return 'Lucida', 'Lucida Sans Unicode'
    elif font_name == 'Pala':
        return 'Pala', 'Palatino Linotype'
    elif font_name == 'Trebuc':
        return 'Trebuc', 'Trebuchet'
    elif font_name[:5] == 'Gen A':
        font_name = 'Gentium Alt ' + font_name[5:].title()
    elif font_name[:4] == 'Gen ':
        font_name = 'Gentium ' + font_name[4:]

    if font_name[:len(base)] == base:
        #base is still valid
        rest = font_name[len(base):].strip().split(' ')
        p = ' '.join(rest[:-1]).replace('Mo', 'Mono').replace('Se', 'Serif')
        prefix = ' '.join([base, p]).strip()
        suffix = rest[-1].lower()
        if suffix in ['it', 'i']:
            font_name = base + ' Italic'
        elif suffix in ['bd', 'b']:
            font_name = prefix + ' Bold'
        elif suffix in ['bi', 'bdit', 'z']:
            font_name = prefix + ' Bold Italic'
        elif suffix == 'mr':
            font_name = prefix + ' Mono Regular'
        elif suffix == 'mri':
            font_name = prefix + ' Mono Italic'
        elif suffix == 'mb':
            font_name = prefix + ' Mono Bold'
        elif suffix == 'mbi':
            font_name = prefix + ' Mono Bold Italic'
        elif suffix in ['rr', 'se']:
            font_name = prefix + ' Serif'
        elif suffix == 'rri':
            font_name = prefix + ' Serif Italic'
        elif suffix in ['rb', 'sebd']:
            font_name = prefix + ' Serif Bold'
        elif suffix == 'rbi':
            font_name = prefix + ' Serif Bold Italic'
        elif suffix in ['sb', 'sansbold']:
            font_name = prefix + ' Sans Bold'
        elif suffix == 'sbi':
            font_name = prefix + ' Sans Bold Italic'
        elif suffix == 'sr':
            font_name = prefix + ' Sans'
        elif suffix == 'sri':
            font_name = prefix + ' Sans Italic'
    else:
        #new base
        base = font_name.split(' ')[0]
        if len(base) < 4:
            base = font_name
    if font_name[-3:] == ' It':
        font_name += 'alic'
    elif font_name[-3:] == ' Bd':
        font_name = font_name[-1:] + 'old'
    font_name = font_name.replace(' Ms', ' Microsoft ')\
                    .replace(' Std', ' Standard ')\
                    .replace('Mg ', 'Magenta ')\
                    .replace('Tlwg ', 'Thai ')\
                    .replace('I102', 'Italic')\
                    .replace('R102', 'Regular')\
                    .replace('Cour ', 'Courier New ')\
                    .replace('Trebuc ', 'Trebuchet ')\
                    .replace('Pala ', 'Palatino Linotype ')
    if sys.platform.startswith('win'):
        font_name = font_name.replace('Times', 'Times New Roman')
    return font_name, base


def _font_dictionary(font_files=None):
    if font_files is None:
        font_files = collect_fonts()
    #step 1: temporary font names derived from file names
    t = {}
    for font_file in font_files:
        t[name(basename(font_file))] = font_file
    #step 2: fix font names derived from context
    #normally a base come first, than italic, bold
    font_names = t.keys()
    font_names.sort()
    d = {}
    base = 'xxx'  # non existing font name as base
    for font_name in font_names:
        new_font_name, base = _font_name(font_name, base)
        if new_font_name[0].upper() == new_font_name[0]:
            d[new_font_name] = t[font_name]
    return d


def font_dictionary(filename=None, force=False):
    """\
    Path specification for the font dictionary, cached
    """
    global _FONT_DICTIONARY
    if _FONT_DICTIONARY is None:
        if filename is None:
            if os.path.exists(USER_FONTS_CACHE_PATH):
                filename = USER_FONTS_CACHE_PATH
            else:
                filename = ROOT_FONTS_CACHE_PATH
        if filename and os.path.exists(filename) and not force:
            _FONT_DICTIONARY = safe.eval_safe(file(filename, 'rb').read())
        else:
            _FONT_DICTIONARY = {}
        if not _FONT_DICTIONARY:
            _FONT_DICTIONARY = _font_dictionary()
            if not (WRITABLE_FONTS_CACHE_PATH is None):
                f = file(WRITABLE_FONTS_CACHE_PATH, 'wb')
                f.write(unicode(_FONT_DICTIONARY))
                f.close()
    if not _FONT_DICTIONARY:
        # 'empty' dict for ui
        _FONT_DICTIONARY = {'': ''}
    _FONT_DICTIONARY.update(SHIPPED_FONTS)
    return _FONT_DICTIONARY


def font_names(filename=None):
    global _FONT_NAMES
    if _FONT_NAMES is None:
        _FONT_NAMES = font_dictionary(filename).keys()
        _FONT_NAMES.sort()
    return _FONT_NAMES


def merge(*paths):
    font_files = []
    for path in paths:
        font_files += glob.glob(os.path.join(path, "*.ttf"))
    return _font_dictionary(font_files)


def set_font_cache(user_fonts_path, root_fonts_path,
        user_fonts_cache_path, root_fonts_cache_path):
    """Expose global variables"""
    # maybe this should generate the cache immediately
    global SHIPPED_FONTS
    global USER_FONTS_CACHE_PATH
    global ROOT_FONTS_CACHE_PATH
    global WRITABLE_FONTS_CACHE_PATH
    SHIPPED_FONTS = merge(root_fonts_path, user_fonts_path)
    USER_FONTS_PATH = user_fonts_path
    ROOT_FONTS_PATH = root_fonts_path
    USER_FONTS_CACHE_PATH = user_fonts_cache_path
    ROOT_FONTS_CACHE_PATH = root_fonts_cache_path
    if not hasattr(os, 'getuid') or os.getuid():
        WRITABLE_FONTS_CACHE_PATH = USER_FONTS_CACHE_PATH
    else:
        WRITABLE_FONTS_CACHE_PATH = ROOT_FONTS_CACHE_PATH


def example():
    names = font_dictionary().keys()
    names.sort()
    sys.stdout.write(unicode(names) + '\n')


if __name__ == '__main__':
    example()
