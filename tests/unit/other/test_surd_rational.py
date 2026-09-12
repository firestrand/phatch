import pytest

from phatch.other import surd as surd_module
from phatch.other.surd import gcd, surd


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [
        (145, 15, (29, 3)),
        (-14, 6, (-7, 3)),
        (14, -6, (-7, 3)),
        (-14, -6, (7, 3)),
        (0, 19, (0, 1)),
        (3.2, 1, (16, 5)),
        (1045.2, 2.5, (10452, 25)),
        (12000, 0.05, (240000, 1)),
    ],
)
def test_construction_canonicalizes_known_rational_values(
    numerator: int | float,
    denominator: int | float,
    expected: tuple[int, int],
) -> None:
    value = surd(numerator, denominator)

    assert (value.num, value.denom) == expected
    assert type(value.num) is int
    assert type(value.denom) is int


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (54, 24, 6),
        (24, 54, 6),
        (0, 19, 19),
    ],
)
def test_gcd_returns_known_euclidean_results(
    left: int, right: int, expected: int
) -> None:
    assert gcd(left, right) == expected


def test_arithmetic_identities_evaluate_to_independent_known_values() -> None:
    one_half = surd(1, 2)
    one_third = surd(1, 3)

    assert one_half + one_third == surd(5, 6)
    assert one_half - one_third == surd(1, 6)
    assert one_half * one_third == surd(1, 6)
    assert one_half / one_third == surd(3, 2)
    assert 2 + one_half == surd(5, 2)
    assert 2 - one_half == surd(3, 2)
    assert 2 * one_half == surd(1)
    assert 2 / one_half == surd(4)


def test_sign_absolute_and_conversion_protocols_return_known_values() -> None:
    value = surd(-7, 3)

    assert -value == surd(7, 3)
    assert abs(value) == surd(7, 3)
    assert float(value) == -7 / 3
    assert int(value) == -2
    assert value() == 0


def test_ordering_equality_hash_and_strings_use_canonical_value() -> None:
    reduced = surd(2, 4)

    assert reduced == surd(1, 2)
    assert reduced != surd(2, 3)
    assert surd(1, 3) < reduced < surd(3, 4)
    assert surd(3, 4) > reduced
    assert reduced <= surd(1, 2)
    assert reduced >= surd(1, 2)
    assert hash(reduced) == hash(surd(1, 2))
    assert repr(reduced) == "1/2"
    assert str(reduced) == "1/2"
    assert str(surd(4)) == "4"


def test_zero_denominators_raise_for_construction_and_division() -> None:
    with pytest.raises(ZeroDivisionError):
        _ = surd(4, 0)
    with pytest.raises(ZeroDivisionError):
        _ = surd(4) / surd(0)


def test_historical_known_value_driver_completes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    surd_module.test_driver()

    output = capsys.readouterr().out
    assert "all surd tests passed." in output
    assert "1000 divisions" in output
