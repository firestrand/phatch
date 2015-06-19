#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2008  www.stani.be
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
import subprocess
import sys


COMMAND = [
    'nosetests',
    '--with-doctest',
    '--noexe',  # DO NOT look for tests in python modules that are executable.
    '-P',  # --no-path-adjustment
    '-q',  # --quiet
]
MODULES = ['actions', 'console', 'core', 'data', 'lib', 'pyWx']


def main(COMMAND, MODULES):
    if sys.platform.startswith('win'):
        # windows
        args = COMMAND + ['-e', 'linux'] + MODULES
    elif sys.platform.startswith('darwin'):
        # mac
        args = COMMAND + ['-e', 'linux|windows'] + MODULES
    else:
        # linux
        args = COMMAND + ['-e', 'windows'] + MODULES + ['linux']
    os.chdir('../phatch')
    # The commented lines might be necessary for windows?!
    #os.rename('__init__.py', '__init__.py.test')
    #if os.path.exists('__init__.py'):
    #    os.remove('__init__.py')
    result = subprocess.call(args)
    #os.rename('__init__.py.test', '__init__.py')
    os.chdir('../tests')
    return result


if __name__ == '__main__':
    sys.exit(main(COMMAND, MODULES))
