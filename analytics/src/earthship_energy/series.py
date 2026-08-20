"""Pure, unit-tested time-series math for energy analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from math import isfinite
from typing import Iterable
from zoneinfo import ZoneInfo


Point = tuple[datetime, float]


@dataclass(frozen=True)
class IntegrationResult:
    """Integral in value-hours and the duration that contributed to it."""

    value_hours: float
    covered_seconds: float


def fahrenheit_to_celsius(value: float) -> float:
    return (float(value) - 32.0) * 5.0 / 9.0


def local_day_bounds(day: date, timezone_name: str) -> tuple[datetime, datetime]:
    """Return the UTC half-open bounds for one local calendar day."""

    zone = ZoneInfo(timezone_name)
    start_local = datetime.combine(day, time.min, tzinfo=zone)
    end_local = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _validated_points(points: Iterable[Point]) -> list[Point]:
    ordered = sorted((at, float(value)) for at, value in points)
    previous = None
    for at, value in ordered:
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        if not isfinite(value):
            raise ValueError("values must be finite")
        if previous is not None and at == previous:
            raise ValueError("duplicate timestamps are ambiguous")
        previous = at
    return ordered


def _valid_intervals(points: Iterable[Point], max_gap: timedelta):
    if max_gap.total_seconds() <= 0:
        raise ValueError("max_gap must be positive")
    ordered = _validated_points(points)
    for left, right in zip(ordered, ordered[1:]):
        seconds = (right[0] - left[0]).total_seconds()
        if 0 < seconds <= max_gap.total_seconds():
            yield left, right, seconds


def integrate_trapezoid(
    points: Iterable[Point], max_gap: timedelta
) -> IntegrationResult:
    """Integrate a value series without bridging intervals beyond ``max_gap``."""

    value_hours = 0.0
    covered_seconds = 0.0
    for left, right, seconds in _valid_intervals(points, max_gap):
        value_hours += ((left[1] + right[1]) / 2.0) * seconds / 3600.0
        covered_seconds += seconds
    return IntegrationResult(value_hours, covered_seconds)


def coverage_ratio(covered_seconds: float, window_seconds: float) -> float:
    if window_seconds <= 0:
        return 0.0
    return min(1.0, max(0.0, float(covered_seconds) / float(window_seconds)))


def time_weighted_mean(result: IntegrationResult) -> float | None:
    if result.covered_seconds <= 0:
        return None
    return result.value_hours / (result.covered_seconds / 3600.0)


def duration_above(
    points: Iterable[Point], threshold: float, max_gap: timedelta
) -> float:
    """Linearly interpolate seconds strictly above a threshold."""

    duration = 0.0
    for left, right, seconds in _valid_intervals(points, max_gap):
        left_value, right_value = left[1], right[1]
        if left_value > threshold and right_value > threshold:
            duration += seconds
        elif left_value <= threshold < right_value:
            duration += seconds * (right_value - threshold) / (
                right_value - left_value
            )
        elif right_value <= threshold < left_value:
            duration += seconds * (left_value - threshold) / (
                left_value - right_value
            )
    return duration


def equivalent_full_cycles(
    charge_kwh: float, discharge_kwh: float, nominal_usable_kwh: float
) -> float:
    if nominal_usable_kwh <= 0:
        raise ValueError("nominal usable capacity must be positive")
    if charge_kwh < 0 or discharge_kwh < 0:
        raise ValueError("throughput values must be non-negative")
    return (charge_kwh + discharge_kwh) / (2.0 * nominal_usable_kwh)
