from pathlib import Path

import pytest

from phatch.lib import safe


def allow_known_names(
    names: tuple[str, ...], globals_: dict[str, int], locals_: dict[str, int]
) -> set[str]:
    return set(names).difference(globals_, locals_, safe.SAFE["all"])


def test_eval_safe_computes_name_free_expression() -> None:
    assert safe.eval_safe("1 + 1") == 2


def test_eval_restricted_prefers_locals_and_accepts_namespace_names() -> None:
    allowed = ["max"]

    result = safe.eval_restricted("max(a, a+b)", {"a": 0, "b": 2}, {"a": 1}, allowed)

    assert result == 3
    assert allowed == ["max", "a", "a", "b"]


def test_eval_restricted_reports_only_unknown_names() -> None:
    with pytest.raises(safe.UnsafeError, match=r"invalid: c$"):
        safe.eval_restricted("a+b+c", {"b": 2}, {"a": 1}, [])


def test_eval_restricted_supplies_empty_namespaces() -> None:
    assert safe.eval_restricted("1 + 1") == 2


def test_assert_safe_returns_caller_namespaces_without_copying() -> None:
    globals_ = {"width": 4}
    locals_ = {"height": 3}

    code, returned_globals, returned_locals = safe.assert_safe(
        "width + height", globals_, locals_, allow_known_names
    )

    assert eval(code, returned_globals, returned_locals) == 7
    assert returned_globals is globals_
    assert returned_locals is locals_


def test_assert_safe_rejects_names_before_expression_can_execute(
    tmp_path: Path,
) -> None:
    sentinel = tmp_path / "must-not-exist"
    expression = f'__import__("pathlib").Path({str(sentinel)!r}).touch()'

    with pytest.raises(safe.UnsafeError, match="__import__"):
        safe.eval_safe(expression)

    assert not sentinel.exists()


@pytest.mark.parametrize(
    ("expression", "error"),
    [("1 +", SyntaxError), ("1 / 0", ZeroDivisionError)],
)
def test_eval_safe_preserves_callable_errors(
    expression: str, error: type[Exception]
) -> None:
    with pytest.raises(error):
        safe.eval_safe(expression)


def test_compile_expr_handles_safe_and_unrestricted_subexpressions() -> None:
    assert safe.compile_expr("<1+1>_<abs(2-3)>", safe=False) == "2_1"
    assert (
        safe.compile_expr(
            "<min(width,height)>",
            {"min": min},
            {"width": 1920, "height": 1080},
            allow_known_names,
        )
        == "1080"
    )


def test_compile_expr_formats_integer_and_preserves_plain_text() -> None:
    assert safe.format_expr("###(index+1)") == '"%03d"%(index+1)'
    assert (
        safe.compile_expr(
            "image-<###(index+1)>",
            _locals={"index": 1},
            preprocess=safe.format_expr,
            safe=False,
        )
        == "image-002"
    )
    assert safe.compile_expr("plain", safe=False) == "plain"


def test_compile_expr_rejects_invalid_and_unsafe_rendered_formulas(
    tmp_path: Path,
) -> None:
    with pytest.raises(SyntaxError):
        safe.compile_expr("prefix-<1+>-suffix", safe=False)

    sentinel = tmp_path / "must-not-exist"
    expression = f'<__import__("pathlib").Path({str(sentinel)!r}).touch()>'
    with pytest.raises(safe.UnsafeError, match="__import__"):
        safe.compile_expr(expression)
    assert not sentinel.exists()


def test_assert_safe_expr_checks_every_rendered_formula() -> None:
    assert safe.assert_safe_expr("plain text") is None
    with pytest.raises(safe.UnsafeError, match="blocked"):
        safe.assert_safe_expr("<1+1>-<blocked>")


def test_extend_vars_adds_unique_identifiers_and_attributes() -> None:
    variables = ["a1"]

    safe.extend_vars(variables, "<a1>_<foo>_<image.width>_<###index>_<foo>")

    assert variables == ["a1", "foo", "image", "index"]
