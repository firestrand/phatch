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
# Phatch recommends SPE (http://pythonide.stani.be) for editing python files.

# Follows PEP8

from lib.safe import RE_EXPR, RE_VAR
from lib.reverse_translation import _t, _r
from lib.unicoding import ensure_unicode

REVERSE = {}


def to_english(x):
    _x = _r(ensure_unicode(x))
    if x != _x:
        return _x
    return RE_EXPR.sub(_expr_to_english, x)


def _expr_to_english(match):
    """Translates variables within an expression to english."""
    return '<%s>' % (RE_VAR.sub(_var_to_english, match.group(1)))


def _var_to_english(match):
    return _r(match.group('var')) + match.group('attr')


def to_local(x):
    _x = _(x)
    if x != _x:
        return _x
    return RE_EXPR.sub(_expr_to_local, x)


def _expr_to_local(match):
    return '<%s>' % (RE_VAR.sub(_var_to_local, match.group(1)))


def _var_to_local(match):
    return _(match.group('var')) + match.group('attr')
