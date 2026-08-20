from datetime import date, datetime, timedelta, timezone

import pytest

from earthship_energy.series import (
    coverage_ratio,
    duration_above,
    equivalent_full_cycles,
    fahrenheit_to_celsius,
    integrate_trapezoid,
    local_day_bounds,
    time_weighted_mean,
)


UTC = timezone.utc


def at(hour: int) -> datetime:
    return datetime(2026, 1, 1, hour, tzinfo=UTC)


def test_fahrenheit_to_celsius():
    assert fahrenheit_to_celsius(32.0) == pytest.approx(0.0)
    assert fahrenheit_to_celsius(212.0) == pytest.approx(100.0)


@pytest.mark.parametrize(
    ("day", "expected_hours"),
    [
        (date(2026, 1, 15), 24),
        (date(2026, 3, 8), 23),
        (date(2026, 11, 1), 25),
    ],
)
def test_local_day_bounds_are_dst_aware(day, expected_hours):
    start, end = local_day_bounds(day, "America/Denver")
    assert start.tzinfo is UTC
    assert end.tzinfo is UTC
    assert (end - start) == timedelta(hours=expected_hours)


def test_trapezoidal_power_integration_returns_kwh_and_coverage():
    result = integrate_trapezoid(
        [(at(0), 1000.0), (at(1), 2000.0), (at(2), 1000.0)],
        max_gap=timedelta(hours=1),
    )
    assert result.value_hours / 1000.0 == pytest.approx(3.0)
    assert result.covered_seconds == pytest.approx(7200.0)


def test_integration_does_not_bridge_large_gaps():
    result = integrate_trapezoid(
        [(at(0), 1000.0), (at(1), 1000.0), (at(4), 5000.0)],
        max_gap=timedelta(hours=1),
    )
    assert result.value_hours / 1000.0 == pytest.approx(1.0)
    assert result.covered_seconds == pytest.approx(3600.0)
    assert coverage_ratio(result.covered_seconds, 4 * 3600.0) == 0.25


def test_time_weighted_mean_uses_only_covered_intervals():
    result = integrate_trapezoid(
        [(at(0), 10.0), (at(1), 20.0), (at(2), 30.0)],
        max_gap=timedelta(hours=1),
    )
    assert time_weighted_mean(result) == pytest.approx(20.0)


def test_duration_above_interpolates_threshold_crossing():
    seconds = duration_above(
        [(at(0), 0.0), (at(1), 100.0)],
        threshold=50.0,
        max_gap=timedelta(hours=1),
    )
    assert seconds == pytest.approx(1800.0)


def test_invalid_or_empty_coverage_is_explicit():
    assert coverage_ratio(0.0, 0.0) == 0.0
    assert time_weighted_mean(integrate_trapezoid([], timedelta(minutes=5))) is None


def test_equivalent_full_cycles_preserves_bidirectional_throughput():
    assert equivalent_full_cycles(10.24, 10.24, 20.48) == pytest.approx(0.5)
    with pytest.raises(ValueError, match="positive"):
        equivalent_full_cycles(1.0, 1.0, 0.0)
