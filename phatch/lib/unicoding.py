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

import codecs
import locale
import system

ENCODING = locale.getdefaultlocale()[1]

try:
    codecs.lookup(ENCODING)
except:
    ENCODING = locale.getpreferredencoding()
    try:
        codecs.lookup(ENCODING)
    except:
        ENCODING = 'utf-8'


def ensure_unicode(x, encoding=ENCODING, errors='replace'):
    if type(x) is unicode:
        return x
    try:
        return unicode(x)
    except UnicodeDecodeError:
        return unicode(x, encoding, errors)


def exception_to_unicode(x, encoding=ENCODING, errors='replace'):
##    #python2.5
##    if hasattr(x, 'message'):
##        return ensure_unicode(x.message, encoding, errors)
    #python2.4
    try:
        return ensure_unicode(x, encoding, errors)
    except:
        try:
            return ensure_unicode(str(x), encoding, errors)
        except:
            return u'?'


def fix_filename(f, encoding=None):
    if system.is_file(f):
        return f
    if type(f) is unicode:
        encodings = ['latin1', 'utf-8', ENCODING]
        if encoding:
            encodings = [encoding] + encodings
        for encoding in encodings:
            try:
                f = f.encode(encoding)
                if system.is_file(f):
                    return f
            except UnicodeEncodeError:
                pass
    return None
