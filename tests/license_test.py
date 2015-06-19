#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2010  www.stani.be
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
# You need to have licensecheck installed:
#   sudo apt-get install devscripts


import os
import re
import sys
import time
sys.path.insert(0, os.path.join('..', 'phatch'))


try:
    from lib import system
except ImportError:
    print("You need to run this script from the 'tests' directory.")
    sys.exit(1)

RE_FILE = re.compile('(?P<filename>.+?):\s(?P<license>.+?)\s*'\
    '\n(\s+\[(?P<copyright>.+?)\])?')


def get_error(d):
    if 'GENERATED' in d['license']:
        return None
    if d['license'] != 'GPL (v3 or later)':
        return 'License should be "GPL (v3 or later)".'
    if d['copyright'] is None:
        return 'Copyright is missing (needs to include www.stani.be).'
    if not('www.stani.be' in d['copyright']):
        return "Copyright doesn't include 'www.stani.be'"


def check():
    time_start = time.time()
    error = 0
    total = 0
    cur_dir = os.getcwd()
    stdout, stderr = system.shell(['licensecheck',
        '--recursive',
        '--copyright',
        '--ignore', 'phatch/other|wxGlade|license',
        os.path.abspath('..'),
    ])
    for match in RE_FILE.finditer(stdout):
        d = match.groupdict()
        d['error'] = get_error(d)
        if d['error'] and not('api.py' in d['filename']):
            print('%(filename)s:\n'\
                '- %(error)s\n'\
                '- license: %(license)s\n'\
                '- copyright: %(copyright)s\n' % d)
            error += 1
        total += 1
    print('Ran %d license tests in %.3fs'
        % (total, time.time() - time_start))
    sys.exit(error)


if __name__ == '__main__':
    check()
