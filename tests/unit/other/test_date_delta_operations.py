import datetime

import pytest

from phatch.other.relativedelta import MO, TU, relativedelta

UTC = datetime.UTC


@pytest.mark.parametrize(
    ("later", "earlier"),
    [
        (
            datetime.datetime(2024, 3, 31, 10, 20, 30, 400, tzinfo=UTC),
            datetime.datetime(2023, 12, 30, 8, 15, 20, 100, tzinfo=UTC),
        ),
        (datetime.date(2023, 2, 28), datetime.date(2024, 2, 29)),
        (datetime.datetime(2024, 1, 2, 1), datetime.date(2024, 1, 1)),
    ],
)
def test_difference_constructor_round_trips_dates(
    later: datetime.date, earlier: datetime.date
) -> None:
    assert earlier + relativedelta(later, earlier) == later


def test_normalization_carries_positive_and_negative_units() -> None:
    positive = relativedelta(
        months=14, hours=25, minutes=61, seconds=61, microseconds=1_000_001
    )
    negative = relativedelta(
        months=-14, hours=-25, minutes=-61, seconds=-61, microseconds=-1_000_001
    )

    assert (positive.years, positive.months, positive.days) == (1, 2, 1)
    assert (positive.hours, positive.minutes, positive.seconds) == (2, 2, 2)
    assert positive.microseconds == 1
    assert (negative.years, negative.months, negative.days) == (-1, -2, -1)
    assert (negative.hours, negative.minutes, negative.seconds) == (-2, -2, -2)
    assert negative.microseconds == -1


def test_delta_algebra_preserves_absolute_and_relative_fields() -> None:
    first = relativedelta(years=1, days=2, seconds=3, year=2024, hour=0, microsecond=7)
    second = relativedelta(months=2, days=3, minute=4, second=5, microsecond=11)

    combined = first + second
    difference = first - second

    assert (combined.years, combined.months, combined.days, combined.seconds) == (
        1,
        2,
        5,
        3,
    )
    assert (combined.year, combined.hour, combined.minute) == (2024, 0, 4)
    assert (combined.second, combined.microsecond) == (5, 11)
    assert (difference.years, difference.months, difference.days) == (1, -2, -1)
    assert (difference.seconds, difference.microseconds) == (3, 0)


def test_negation_multiplication_and_division_have_known_values() -> None:
    delta = relativedelta(days=4, hours=6)

    assert -delta == relativedelta(days=-4, hours=-6)
    assert delta * 2 == relativedelta(days=8, hours=12)
    assert delta / 2 == relativedelta(days=2, hours=3)


def test_subtracting_delta_from_date_applies_negation() -> None:
    start = datetime.date(2024, 3, 31)

    assert start - relativedelta(months=1) == datetime.date(2024, 2, 29)


def test_truth_equality_and_representation_cover_value_semantics() -> None:
    assert not relativedelta()
    assert relativedelta(days=1)
    assert relativedelta(weekday=MO) == relativedelta(weekday=MO(1))
    assert relativedelta(weekday=MO) != relativedelta(weekday=TU)
    assert relativedelta(weekday=MO) != relativedelta()
    assert relativedelta(days=1) != datetime.timedelta(days=1)
    assert repr(relativedelta(years=1, day=2, weekday=MO)) == (
        "relativedelta(years=+1, day=2, weekday=MO)"
    )


def test_delta_operators_reject_unrelated_types() -> None:
    delta = relativedelta(days=1)

    with pytest.raises(TypeError, match="unsupported type"):
        _ = delta + datetime.timedelta(days=1)
    with pytest.raises(TypeError, match="unsupported type"):
        _ = delta - datetime.timedelta(days=1)
