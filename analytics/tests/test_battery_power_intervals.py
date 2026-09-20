"""Battery energy and EFC must use the exact qualified power segments."""
from datetime import datetime, timedelta, timezone

import pytest

from earthship_energy.aggregation import aggregate_battery
from earthship_energy.power_intervals import PowerInterval

START = datetime(2026, 9, 20, tzinfo=timezone.utc)
END = START + timedelta(days=1)


def aggregate(intervals, sign='positive_charging'):
    return aggregate_battery(
        soc_points=[(START, 75), (END, 75)],
        # Contradictory held history must be ignored in qualified mode.
        power_points=[(START, 1000), (END, 1000)],
        temperature_c_points=[(START, 20), (END, 20)],
        window_start=START, window_end=END, max_gap=END-START,
        nominal_usable_kwh=20.48, power_sign=sign, power_intervals=intervals,
    )


def test_short_receipt_does_not_become_full_day_energy_or_efc():
    result = aggregate([PowerInterval(START, START+timedelta(seconds=120), 1000)])
    assert result.charge_kwh == pytest.approx(1/30)
    assert result.discharge_kwh == 0
    assert result.daily_efc == pytest.approx((1/30)/(2*20.48))
    assert result.coverage == pytest.approx(120/86400)
    assert result.quality == 'insufficient_data'


@pytest.mark.parametrize('sign', ['positive_charging', 'negative_charging'])
def test_signed_throughput_preserves_gap_and_calibration(sign):
    result = aggregate([
        PowerInterval(START, START+timedelta(hours=1), 1000),
        PowerInterval(START+timedelta(hours=3), START+timedelta(hours=4), -2000),
    ], sign)
    charge, discharge = (1, 2) if sign == 'positive_charging' else (2, 1)
    assert result.charge_kwh == charge
    assert result.discharge_kwh == discharge
    assert result.net_kwh == charge-discharge
    assert result.daily_efc == pytest.approx(3/(2*20.48))
    assert result.coverage == pytest.approx(2/24)


def test_empty_qualified_history_is_not_a_numeric_fallback():
    result = aggregate([])
    assert result.charge_kwh == result.discharge_kwh == result.daily_efc == 0
    assert result.coverage == 0
    assert result.quality == 'insufficient_data'


def test_observed_zero_is_distinct_from_missing():
    result = aggregate([PowerInterval(START, END, 0)])
    assert result.charge_kwh == result.discharge_kwh == result.daily_efc == 0
    assert result.coverage == 1
    assert result.quality == 'ok'


def test_overlapping_qualified_intervals_fail_closed():
    interval = PowerInterval(START, END, 1000)
    with pytest.raises(ValueError, match='nonoverlapping'):
        aggregate([interval, interval])


def test_omitted_qualified_input_retains_explicit_legacy_path():
    result = aggregate(None)
    assert result.charge_kwh == 24
    assert result.coverage == 1
