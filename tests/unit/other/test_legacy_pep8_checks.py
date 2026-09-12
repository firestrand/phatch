from io import StringIO
from tokenize import generate_tokens

import pytest

from phatch.other import pep8


@pytest.mark.parametrize(
    ("check", "arguments", "expected"),
    [
        (pep8.tabs_or_spaces, (" \tpass\n", " "),
         (1, "E101 indentation contains mixed spaces and tabs")),
        (pep8.tabs_obsolete, ("\tpass\n",),
         (0, "W191 indentation contains tabs")),
        (pep8.trailing_whitespace, ("x  \n",),
         (1, "W291 trailing whitespace")),
        (pep8.trailing_blank_lines, ("\n", ["x\n", "\n"], 2),
         (0, "W391 blank line at end of file")),
        (pep8.missing_newline, ("x",),
         (1, "W292 no newline at end of file")),
        (pep8.maximum_line_length, ("x" * 80 + "\n",),
         (79, "E501 line too long (80 characters)")),
    ],
)
def test_physical_checks_report_exact_violation(check, arguments, expected):
    assert check(*arguments) == expected


@pytest.mark.parametrize(
    ("check", "arguments"),
    [
        (pep8.tabs_or_spaces, ("    pass\n", " ")),
        (pep8.tabs_obsolete, ("    pass\n",)),
        (pep8.trailing_whitespace, ("x\n",)),
        (pep8.trailing_blank_lines, ("\n", ["\n", "x\n"], 1)),
        (pep8.missing_newline, ("x\n",)),
        (pep8.maximum_line_length, ("x = 1\n",)),
    ],
)
def test_physical_checks_accept_valid_lines(check, arguments):
    assert check(*arguments) is None


@pytest.mark.parametrize(
    ("check", "source", "expected"),
    [
        (pep8.extraneous_whitespace, "f( x)",
         (2, "E201 whitespace after '('")),
        (pep8.extraneous_whitespace, "f(x )",
         (3, "E202 whitespace before ')'")),
        (pep8.extraneous_whitespace, "f(x , y)",
         (3, "E203 whitespace before ','")),
        (pep8.missing_whitespace, "f(a,b)",
         (3, "E231 missing whitespace after ','")),
        (pep8.whitespace_around_operator, "a = 4  + 5",
         (5, "E221 multiple spaces before operator")),
        (pep8.whitespace_around_operator, "a = 4 +  5",
         (6, "E222 multiple spaces after operator")),
        (pep8.whitespace_around_operator, "a = 4\t+ 5",
         (5, "E223 tab before operator")),
        (pep8.whitespace_around_operator, "a = 4 +\t5",
         (6, "E224 tab after operator")),
        (pep8.whitespace_around_comma, "a = (1,  2)",
         (7, "E241 multiple spaces after ','")),
        (pep8.whitespace_around_comma, "a = (1,\t2)",
         (7, "E242 tab after ','")),
        (pep8.whitespace_around_named_parameter_equals, "f(value = 1)",
         (9, "E251 no spaces around keyword / parameter equals")),
        (pep8.imports_on_separate_lines, "import os, sys",
         (9, "E401 multiple imports on one line")),
        (pep8.compound_statements, "if ready: run()",
         (8, "E701 multiple statements on one line (colon)")),
        (pep8.compound_statements, "first(); second()",
         (7, "E702 multiple statements on one line (semicolon)")),
        (pep8.python_3000_has_key, "data.has_key(key)",
         (4, "W601 .has_key() is deprecated, use 'in'")),
        (pep8.python_3000_raise_comma, "raise ValueError, 'bad'",
         (16, "W602 deprecated form of raising exception")),
        (pep8.python_3000_not_equal, "left <> right",
         (5, "W603 '<>' is deprecated, use '!='")),
        (pep8.python_3000_backticks, "`value`",
         (0, "W604 backticks are deprecated, use 'repr()'")),
    ],
)
def test_logical_checks_report_exact_violation(check, source, expected):
    assert check(source) == expected


@pytest.mark.parametrize(
    ("check", "source"),
    [
        (pep8.extraneous_whitespace, "f(x, y)"),
        (pep8.missing_whitespace, "values[1:4]"),
        (pep8.whitespace_around_operator, "total = left + right"),
        (pep8.whitespace_around_comma, "items = (1, 2)"),
        (pep8.whitespace_around_named_parameter_equals, "f(value=1)"),
        (pep8.imports_on_separate_lines, "from os import path, sep"),
        (pep8.compound_statements, "result = lambda value: value"),
        (pep8.python_3000_has_key, "key in data"),
        (pep8.python_3000_raise_comma, "raise ValueError('bad')"),
        (pep8.python_3000_not_equal, "left != right"),
        (pep8.python_3000_backticks, "repr(value)"),
    ],
)
def test_logical_checks_accept_valid_source(check, source):
    assert check(source) is None


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("call (value)", ((1, 4), "E211 whitespace before '('")),
        ("items [0]", ((1, 5), "E211 whitespace before '['")),
    ],
)
def test_parameter_whitespace_uses_real_tokens(source, expected):
    tokens = list(generate_tokens(StringIO(source).readline))

    assert pep8.whitespace_before_parameters(source, tokens) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("total=left + right", ((1, 5), "E225 missing whitespace around operator")),
        ("total = left+right", ((1, 12), "E225 missing whitespace around operator")),
    ],
)
def test_operator_whitespace_uses_real_tokens(source, expected):
    tokens = list(generate_tokens(StringIO(source).readline))

    assert pep8.missing_whitespace_around_operator(source, tokens) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("value = 1 # comment", ((1, 9),
         "E261 at least two spaces before inline comment")),
        ("value = 1  #comment", ((1, 11),
         "E262 inline comment should start with '# '")),
    ],
)
def test_inline_comment_whitespace_uses_real_tokens(source, expected):
    tokens = list(generate_tokens(StringIO(source).readline))

    assert pep8.whitespace_before_inline_comment(source, tokens) == expected


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (("  value = 1", "", " ", 2, 0),
         (0, "E111 indentation is not a multiple of four")),
        (("pass", "if ready:", " ", 0, 0),
         (0, "E112 expected an indented block")),
        (("value = 1", "other = 2", " ", 4, 0),
         (0, "E113 unexpected indentation")),
    ],
)
def test_indentation_reports_exact_violation(arguments, expected):
    assert pep8.indentation(*arguments) == expected


def test_helpers_preserve_token_width_and_expand_tabs():
    assert pep8.expand_indent("    \tvalue") == 8
    assert pep8.mute_string("r'''secret'''") == "r'''xxxxxx'''"


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (("def method():", 0, 4, 3, "value = 1", 0),
         (0, "E301 expected 1 blank line, found 0")),
        (("def second():", 1, 0, 4, "pass", 0),
         (0, "E302 expected 2 blank lines, found 1")),
        (("value = 1", 3, 0, 4, "pass", 0),
         (0, "E303 too many blank lines (3)")),
        (("def wrapped():", 1, 0, 3, "@decorator", 0),
         (0, "E304 blank lines found after function decorator")),
    ],
)
def test_blank_line_checks_report_exact_violation(arguments, expected):
    assert pep8.blank_lines(*arguments) == expected


def test_valid_token_edge_cases_skip_false_positives():
    tuple_tokens = list(generate_tokens(StringIO("item = (3,)\n").readline))
    keyword_tokens = list(generate_tokens(StringIO("f(value=1)\n").readline))

    assert pep8.missing_whitespace("item = (3,)") is None
    assert pep8.whitespace_before_parameters("f(value=1)", keyword_tokens) is None
    assert pep8.missing_whitespace_around_operator(
        "item = (3,)", tuple_tokens) is None
    assert pep8.whitespace_before_inline_comment(
        "# standalone", list(generate_tokens(StringIO("# standalone\n").readline))
    ) is None
