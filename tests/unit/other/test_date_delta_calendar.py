import datetime

import pytest

from phatch.other.relativedelta import FR, MO, relativedelta, weekday

UTC = datetime.UTC


@pytest.mark.parametrize(
    ("start", "delta", "expected"),
    [
        (
            datetime.datetime(2024, 1, 31, 12, tzinfo=UTC),
            relativedelta(months=1),
            datetime.datetime(2024, 2, 29, 12, tzinfo=UTC),
        ),
        (
            datetime.datetime(2023, 1, 31, 12, tzinfo=UTC),
            relativedelta(months=1),
            datetime.datetime(2023, 2, 28, 12, tzinfo=UTC),
        ),
        (
            datetime.datetime(2024, 1, 31, 12, tzinfo=UTC),
            relativedelta(months=-1),
            datetime.datetime(2023, 12, 31, 12, tzinfo=UTC),
        ),
        (
            datetime.datetime(2024, 2, 29, 12, tzinfo=UTC),
            relativedelta(years=1),
            datetime.datetime(2025, 2, 28, 12, tzinfo=UTC),
        ),
        (
            datetime.datetime(2024, 2, 28, 23, 59, 59, tzinfo=UTC),
            relativedelta(seconds=1),
            datetime.datetime(2024, 2, 29, tzinfo=UTC),
        ),
    ],
)
def test_relative_calendar_arithmetic_has_known_utc_results(
    start: datetime.datetime,
    delta: relativedelta,
    expected: datetime.datetime,
) -> None:
    assert start + delta == expected


def test_absolute_fields_apply_before_relative_fields() -> None:
    start = datetime.datetime(2023, 5, 17, 18, 30, 45, 123456, tzinfo=UTC)

    result = start + relativedelta(
        year=2024,
        month=2,
        day=31,
        hour=0,
        minute=1,
        second=2,
        microsecond=3,
        days=1,
    )

    assert result == datetime.datetime(2024, 3, 1, 0, 1, 2, 3, tzinfo=UTC)


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        (relativedelta(weekday=MO), datetime.date(2024, 3, 4)),
        (relativedelta(weekday=MO(2)), datetime.date(2024, 3, 11)),
        (relativedelta(weekday=MO(-1)), datetime.date(2024, 3, 4)),
        (relativedelta(weekday=FR(-2)), datetime.date(2024, 2, 23)),
        (relativedelta(weekday=0), datetime.date(2024, 3, 4)),
    ],
)
def test_weekday_selection_uses_documented_nth_semantics(
    delta: relativedelta, expected: datetime.date
) -> None:
    assert datetime.date(2024, 3, 4) + delta == expected


@pytest.mark.parametrize(
    ("year", "delta", "expected"),
    [
        (2024, relativedelta(yearday=1), datetime.date(2024, 1, 1)),
        (2024, relativedelta(yearday=60), datetime.date(2024, 2, 29)),
        (2023, relativedelta(yearday=60), datetime.date(2023, 3, 1)),
        (2024, relativedelta(nlyearday=60), datetime.date(2024, 3, 1)),
    ],
)
def test_year_day_fields_map_to_known_calendar_dates(
    year: int, delta: relativedelta, expected: datetime.date
) -> None:
    assert datetime.date(year, 7, 1) + delta == expected


def test_leapdays_only_apply_after_february_in_a_leap_year() -> None:
    leap_delta = relativedelta(leapdays=1)

    assert datetime.date(2024, 3, 1) + leap_delta == datetime.date(2024, 3, 2)
    assert datetime.date(2024, 2, 28) + leap_delta == datetime.date(2024, 2, 28)
    assert datetime.date(2023, 3, 1) + leap_delta == datetime.date(2023, 3, 1)


def test_time_delta_promotes_date_to_midnight_datetime() -> None:
    result = datetime.date(2024, 1, 1) + relativedelta(hours=2)

    assert result == datetime.datetime(2024, 1, 1, 2)
    assert type(result) is datetime.datetime


def test_weekday_value_behavior_is_stable() -> None:
    first_monday = MO(1)

    assert MO(1) == weekday(0, 1)
    assert first_monday(1) is first_monday
    assert MO != "Monday"
    assert repr(MO) == "MO"
    assert repr(FR(-2)) == "FR(-2)"


def test_invalid_inputs_raise_public_errors() -> None:
    with pytest.raises(ValueError, match="invalid year day"):
        _ = relativedelta(yearday=367)
    with pytest.raises(TypeError, match="diffs datetime/date"):
        _ = relativedelta("2024-01-01", "2023-01-01")
    with pytest.raises(TypeError, match="unsupported type"):
        relativedelta(days=1).__radd__(1)
