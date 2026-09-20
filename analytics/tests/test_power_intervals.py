from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from earthship_energy.power_intervals import PowerInterval, account_power_intervals


START = datetime(2026, 9, 19, tzinfo=timezone.utc)
END = START + timedelta(days=1)


def account(intervals):
    return account_power_intervals(intervals, window_start=START, window_end=END)


def test_only_qualified_120_seconds_contribute_not_held_24_hours():
    result = account([PowerInterval(START, START + timedelta(seconds=120), 1000)])
    assert result.positive_kwh == pytest.approx(1 / 30)
    assert result.negative_kwh == 0
    assert result.covered_seconds == 120
    assert result.missing_seconds == 86280
    assert result.coverage == pytest.approx(1 / 720)


def test_missing_is_distinct_from_observed_zero():
    missing = account([])
    zero = account([PowerInterval(START, END, 0)])
    assert missing.positive_kwh == zero.positive_kwh == 0
    assert missing.coverage == 0
    assert zero.coverage == 1


def test_clip_half_open_boundaries_and_preserve_gaps_and_sign():
    result = account([
        PowerInterval(START - timedelta(hours=2), START, 9999),
        PowerInterval(START, START + timedelta(hours=1), 1000),
        PowerInterval(START + timedelta(hours=2), START + timedelta(hours=3), -2000),
        PowerInterval(END - timedelta(hours=1), END + timedelta(hours=1), 3000),
        PowerInterval(END + timedelta(hours=1), END + timedelta(hours=2), 9999),
    ])
    assert result.positive_kwh == 4
    assert result.negative_kwh == 2
    assert result.covered_seconds == 10800
    assert result.missing_seconds == 75600


@pytest.mark.parametrize('watts', [float('nan'), float('inf'), -float('inf'), True, '1000', None, 10**400])
def test_invalid_power_rejected_even_outside_window(watts):
    with pytest.raises(ValueError):
        account([PowerInterval(END, END + timedelta(hours=1), watts)])


@pytest.mark.parametrize('intervals', [
    [PowerInterval(START, START, 0)],
    [PowerInterval(END, START, 0)],
    [PowerInterval(START, END, 0), PowerInterval(START, END, 0)],
    [PowerInterval(END, END + timedelta(hours=1), 0), PowerInterval(START, END, 0)],
    [PowerInterval(START.replace(tzinfo=None), END, 0)],
])
def test_ambiguous_or_invalid_intervals_fail_closed(intervals):
    with pytest.raises(ValueError):
        account(intervals)


@pytest.mark.parametrize('month,day,hours', [(3, 8, 23), (11, 1, 25)])
def test_denver_dst_uses_elapsed_time(month, day, hours):
    start = datetime(2026, month, day, tzinfo=ZoneInfo('America/Denver'))
    end = start + timedelta(days=1)
    result = account_power_intervals([PowerInterval(start, end, 1000)],
                                     window_start=start, window_end=end)
    assert result.positive_kwh == hours
    assert result.covered_seconds == hours * 3600
    assert result.coverage == 1


def test_adjacent_equal_segments_do_not_create_a_gap():
    midpoint = START + timedelta(hours=12)
    split = account([PowerInterval(START, midpoint, 1000), PowerInterval(midpoint, END, 1000)])
    assert split == account([PowerInterval(START, END, 1000)])


def test_nonpositive_window_rejected():
    with pytest.raises(ValueError):
        account_power_intervals([], window_start=END, window_end=START)


def test_finite_inputs_cannot_overflow_to_infinite_accounting():
    with pytest.raises(ValueError, match='overflow'):
        account([PowerInterval(START, END, 1e308)])
