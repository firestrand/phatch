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

import math
import random

from lib.metadata import now


def allow(key):
    return key[0] != '_'


def add_dictionary(namespace, dictionary):
    for key, value in dictionary.items():
        if allow(key):
            namespace[key] = value


def add_module(namespace, module):
    """Add module dictionary to the ``namespace``. This is the equivalent
    for::

        from module import *

    This used for the GLOBALS variable.

    :param namespace: namespace
    :type namespace: dict
    :param module_dict: module
    :type module_dict: module
    """
    add_dictionary(namespace, module.__dict__)


def safe_globals():
    GLOBALS = {}
    add_module(GLOBALS, math)
    add_module(GLOBALS, random)
    GLOBALS['now'] = now
    return GLOBALS
