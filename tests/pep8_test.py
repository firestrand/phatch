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
# Follows PEP8


import os
import pickle
import time
import shelve
import sys
sys.path.insert(0, os.path.join('..', 'phatch'))


try:
    from other import pep8
except ImportError:
    print("You need to run this script from the 'tests' directory.")
    sys.exit(1)


ERROR_HEADER = "Shame on you! These file(s) don't follow PEP8:\n%s\n"
PEP8_APP = os.path.join('..', 'phatch', 'other', 'pep8.py')
PEP8_ARGS = ['python', PEP8_APP, '--show-source', '--repeat', '--count']
WXGLADE = 'wxGlade'
OTHER = os.path.join('phatch', 'other')
OUTPUT = os.path.join('tests', 'output')

ERROR_MESSAGE = ''


def message(x):
    global ERROR_MESSAGE
    print(x)
    ERROR_MESSAGE += '%s\n' % x

pep8.process_options(PEP8_ARGS)
pep8.message = message

BLACK_LIST = [
    os.path.join('phatch', 'lib', 'metadataTest.py'),
    os.path.join('phatch', 'lib', 'pyWx', 'about.py'),
    os.path.join('phatch', 'lib', 'pyWx', 'dialogsInspector.py'),
    os.path.join('phatch', 'lib', 'pyWx', 'folderFileBrowser.py'),
]


def test(dirname='..'):
    global ERROR_MESSAGE

    def needs_pep8(filename):
        key = os.path.abspath(filename)[n:]
        return filename.endswith('.py') and not (
            OTHER in filename
            or OUTPUT in filename
            or WXGLADE in filename
            or key in BLACK_LIST
        )

    time_start = time.time()
    total = 0
    dirname = os.path.abspath(dirname)
    n = len(dirname) + 1
    summary = []
    if not os.path.exists('cache'):
        os.mkdir('cache')
    cache = shelve.open(os.path.join('cache', 'pep8'),
        protocol=pickle.HIGHEST_PROTOCOL)
    for root, dirs, files in os.walk(dirname):
        for name in files:
            filename = os.path.join(root, name)
            if not needs_pep8(filename):
                continue
            ERROR_MESSAGE = ''
            count = None
            mtime = os.path.getmtime(filename)
            if filename in cache:
                error_message, count, cmtime = cache[filename]
                if mtime != cmtime:
                    count = None
                elif error_message:
                    message(error_message)
            if count is None:
                checker = pep8.Checker(filename)  # updates ERROR_MESSAGE
                count = checker.check_all()
                cache[filename] = ERROR_MESSAGE, count, mtime
            if count or ERROR_MESSAGE:
                summary.append((filename, count))
            total += 1
    cache.close()
    if summary:
        print(ERROR_HEADER % '\n'.join(
            ['%s (%d)' % (filename, count) for filename, count in summary]
        ))
    print('Ran %d PEP8 tests in %.3fs'
        % (total, time.time() - time_start))
    return summary


def test_with_exit(dirname=''):
    summary = test(dirname)
    if summary:
        sys.exit(1)


if __name__ == '__main__':
    test_with_exit('..')
