# Copyright (C) 2009 www.stani.be
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

#import rpdb2;rpdb2.start_embedded_debugger('x')

import operator
import re

SAFE = {
    'int': ['abs', 'int', 'min', 'max', 'pow', 'sum'],
    'str': ['chr', 'lower', 'str', 'title', 'upper'],
    'bool': ['True', 'False'],
    'datetime': ['day', 'hour', 'microsecond', 'minute', 'month',
        'monthname', 'second', 'weekday', 'weekdayname', 'year'],
    'rational': ['denominator', 'numerator'],
}
SAFE['all'] = reduce(operator.add, SAFE.values())


"""Todo: alleen format ### moet vervangen worden, daarna gewoon
eval met locals (incl indices) en globals.

<x>_<y> wordt '%s_%s'(eval(x),eval(y)) '"""

RE_EXPR = re.compile('<([^<>]+?)>', re.UNICODE)
RE_FORMAT = re.compile('#+')
RE_VAR = re.compile('(?P<var>[A-Za-z]\w*)(?P<attr>([.]\w(\w|[.])+)?)',
    re.UNICODE)


class UnsafeError(Exception):
    pass


def _format_int(match):
    """Converts a ``####`` string into a formating string.

    Helper function for :func:`format_expr`.

    :param match: match for a ``##``-string
    :type match: regular expression match
    :returns: interpolation format
    :rtype: string

    >>> f = _format_int(RE_FORMAT.search('####'))
    >>> f
    '"%04d"%'
    >>> eval(f + '5')
    '0005'
    """
    return '"%%0%dd"%%' % len(match.group(0))


def format_expr(s):
    """Returns an expression with ``####`` in a pure python expression
    which can be evaluated.

    :param s: expression
    :type s: expression

    >>> f = format_expr('###(5+1)')
    >>> f
    '"%03d"%(5+1)'
    >>> eval(f)
    '006'
    """
    return RE_FORMAT.sub(_format_int, s)


def compile_expr(meta_expr, _globals=None, _locals=None, validate=None,
        preprocess=lambda x: x, safe=True):
    """If safe is a list, a restricted evaluation will be executed.
    Otherwise if safe is None, a unrestriced eval will be executed.

    :param meta_expr: meta-expression with <subexpressions>
    :type meta_expr: string
    :param _globals: globals
    :type _globals: dict
    :param _locals: locals
    :type _locals: dict
    :param safe: safe names which will be accepted by the compiler
    :type safe: list or None
    :param preprocess: preprocess expression (e.g. for ## formatting)
    :type preprocess: callable

    >>> compile_expr('<1+1>_<abs(2-3)>', safe=False)
    u'2_1'
    >>> compile_expr('<###(index+1)>', _locals={'index':1},
    ...     preprocess=format_expr, safe=False)
    u'002'
    """
    if _locals is None:
        _locals = {}
    if _globals is None:
        _globals = {}

    if safe:

        def compile_sub_expr(expr):
            return unicode(eval_safe(preprocess(expr.group(1)),
                _globals, _locals, validate))

    else:

        def compile_sub_expr(expr):
            return unicode(eval(preprocess(expr.group(1)),
                _globals, _locals))

    return RE_EXPR.sub(compile_sub_expr, meta_expr)


def assert_safe_expr(meta_expr, _globals=None, _locals=None, validate=None,
        preprocess=lambda x: x):
    for expr in RE_EXPR.finditer(meta_expr):
        assert_safe(preprocess(expr.group(1)), _globals, _locals, validate)


def assert_safe(expr, _globals=None, _locals=None, validate=None):
    if _locals is None:
        _locals = {}
    if _globals is None:
        _globals = {}
    code = compile(expr, '<%s>' % expr, 'eval')
    if code.co_names:
        if validate:
            not_allowed = validate(code.co_names, _globals, _locals)
        else:
            not_allowed = code.co_names
        if not_allowed:
            raise UnsafeError(
                _('The following name(s) are invalid: ') + \
                ', '.join([_(x) for x in not_allowed]))
    return code, _globals, _locals


def eval_safe(expr, _globals=None, _locals=None, validate=None):
    """Safely evaluate an expression. It will raise a ``ValueError`` if
    non validated names are used.

    :param expr: expression
    :type expr: string
    :returns: result

    >>> eval_safe('1+1')
    2
    >>> try:
    ...     eval_safe('"lowercase".upper()')
    ... except UnsafeError, error:
    ...     print(error)
    The following name(s) are invalid: upper
    """
    if _locals is None:
        _locals = {}
    if _globals is None:
        _globals = {}
    return eval(*assert_safe(expr, _globals, _locals, validate))


def eval_restricted(s, _globals=None, _locals=None, allowed=SAFE['all'][:]):
    """Evaluate an expression while allowing a restricted set of names.

    :param allowed: allowed names
    :type allowed: list of string
    :returns: result

    >>> eval_restricted('max(a, a+b)', _globals={'a':0, 'b':2},
    ... _locals={'a':1}, allowed=['max'])
    3
    >>> try:
    ...     eval_restricted('a+b+c', _globals={'a':0, 'b':2}, _locals={'a':1})
    ... except UnsafeError, error:
    ...     print(error)
    The following name(s) are invalid: c
    """
    if _locals is None:
        _locals = {}
    if _globals is None:
        _globals = {}
    allowed += reduce(operator.add, [v.keys() for v in (_locals, _globals)])

    def validate(names, _globals, _locals):
        return set(names).difference(allowed)

    return eval_safe(s, _globals, _locals, validate)


def extend_vars(vars, s):
    """Extend ``vars`` with new unique variables from ``s``.

    :param vars: collection of previous variables
    :type vars: list of string
    :param s: multiple expressions
    :type s: string

    >>> vars = ['a1']
    >>> extend_vars(vars, '<a1>_<foo>_<world>_<###index>')
    >>> vars
    ['a1', 'foo', 'world', 'index']
    """
    for expr in RE_EXPR.findall(s):
        #locate <expr>
        for match in RE_VAR.finditer(expr):
            var = match.group('var')
            if not var in vars:
                vars.append(var)
