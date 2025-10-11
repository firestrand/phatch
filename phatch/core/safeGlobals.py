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
    for key, value in list(dictionary.items()):
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
    """Create a restricted namespace for safe expression evaluation.

    This provides only the functions needed for Phatch expressions like:
    - <width>, <height> (variables from _locals)
    - <min(width, height)> (basic math)
    - <###(index+1)> (formatting with arithmetic)
    - <year>, <monthname> (date/time from metadata)

    Security: Combined with safe.py's assert_safe() validation of code.co_names,
    this prevents code injection attacks. All names in expressions must be in:
    - This globals dict (math functions below)
    - _locals dict (user image info)
    - SAFE['all'] list (safe builtins: min, max, int, str, etc.)

    Any attempt to use __class__, __import__, eval, exec, etc. will be blocked
    by the co_names validator in safe.py.
    """
    GLOBALS = {}

    # Basic math functions (most commonly needed for dimension calculations)
    GLOBALS['abs'] = abs
    GLOBALS['min'] = min
    GLOBALS['max'] = max
    GLOBALS['round'] = round
    GLOBALS['pow'] = pow
    GLOBALS['sum'] = sum

    # Math module functions (for advanced expressions)
    GLOBALS['sqrt'] = math.sqrt
    GLOBALS['ceil'] = math.ceil
    GLOBALS['floor'] = math.floor

    # Math constants (may be useful for calculations)
    GLOBALS['pi'] = math.pi
    GLOBALS['e'] = math.e

    # Type conversions (needed for field validation)
    GLOBALS['int'] = int
    GLOBALS['float'] = float
    GLOBALS['str'] = str

    # Boolean constants (needed for conditionals)
    GLOBALS['True'] = True
    GLOBALS['False'] = False

    # Metadata function for date/time expressions
    GLOBALS['now'] = now

    return GLOBALS
