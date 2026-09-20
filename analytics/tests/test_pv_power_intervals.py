from datetime import datetime, timedelta, timezone

import pytest

from earthship_energy.aggregation import aggregate_power
from earthship_energy.power_intervals import PowerInterval

START = datetime(2026, 9, 20, tzinfo=timezone.utc)
END = START + timedelta(days=1)


def aggregate(intervals):
    return aggregate_power([(START, 4200), (END, 4200)], START, END,
                           max_gap=END-START, power_intervals=intervals)


def test_receipt_energy_peak_and_productivity_ignore_held_numeric_history():
    result = aggregate([PowerInterval(START, START+timedelta(seconds=120), 1000)])
    assert result.energy_kwh == pytest.approx(1/30)
    assert result.coverage == pytest.approx(120/86400)
    assert result.peak_w == 1000
    assert result.productive_hours == pytest.approx(120/3600)
    assert result.first_productive_at == result.last_productive_at == START
    assert result.quality == 'insufficient_data'


def test_empty_is_missing_not_numeric_fallback():
    result = aggregate([])
    assert result.energy_kwh == result.coverage == result.productive_hours == 0
    assert result.peak_w is None
    assert result.first_productive_at is result.last_productive_at is None
    assert result.quality == 'insufficient_data'


def test_observed_zero_retains_coverage():
    result = aggregate([PowerInterval(START, END, 0)])
    assert result.energy_kwh == result.peak_w == result.productive_hours == 0
    assert result.coverage == 1
    assert result.quality == 'ok'


def test_gaps_and_outside_window_values_do_not_contribute():
    result = aggregate([
        PowerInterval(START-timedelta(hours=2), START-timedelta(hours=1), 9999),
        PowerInterval(START-timedelta(hours=1), START+timedelta(hours=1), 1000),
        PowerInterval(START+timedelta(hours=3), START+timedelta(hours=4), 2000),
        PowerInterval(END, END+timedelta(hours=1), 9999),
    ])
    assert result.energy_kwh == 3
    assert result.peak_w == 2000
    assert result.coverage == pytest.approx(2/24)
    assert result.productive_hours == 2
    assert result.first_productive_at == START
    assert result.last_productive_at == START+timedelta(hours=3)


@pytest.mark.parametrize('watts', [-100, 0, 10])
def test_productivity_threshold_is_strict_and_negative_energy_is_not_pv(watts):
    result = aggregate([PowerInterval(START, END, watts)])
    assert result.energy_kwh == max(0, watts)*24/1000
    assert result.productive_hours == 0
    assert result.first_productive_at is None


def test_invalid_intervals_are_not_sorted_or_dropped():
    interval = PowerInterval(START, END, 1000)
    with pytest.raises(ValueError, match='nonoverlapping'):
        aggregate([interval, interval])


def test_legacy_path_is_explicit_and_unchanged():
    result = aggregate(None)
    assert result.energy_kwh == pytest.approx(100.8)
    assert result.coverage == 1
