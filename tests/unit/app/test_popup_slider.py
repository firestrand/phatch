import builtins
import pytest

pytest.importorskip("wx")

if "_" not in builtins.__dict__:
    builtins.__dict__["_"] = lambda value: value

from phatch.lib.pyWx.popup import SliderCtrl


def test_resolve_bounds_defaults_to_safe_range_when_missing():
    minimum, maximum = SliderCtrl._resolve_bounds(None, None, 42)

    assert (minimum, maximum) == (SliderCtrl.DEFAULT_MIN, SliderCtrl.DEFAULT_MAX)


def test_resolve_bounds_guards_against_inverted_range():
    minimum, maximum = SliderCtrl._resolve_bounds(10, 5, 7)

    assert minimum == 10
    assert maximum == 11
