"""Accounting over already-qualified, half-open held-power intervals.

This module does not qualify receipts or infer freshness from numeric changes.
Callers must supply intervals bounded by independent evidence expiry, invalid
events and observer boundaries. No interpolation or implicit carry is performed.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite


@dataclass(frozen=True)
class PowerInterval:
    start: datetime
    end: datetime
    watts: float


@dataclass(frozen=True)
class PowerAccounting:
    positive_kwh: float
    negative_kwh: float
    covered_seconds: float
    missing_seconds: float
    window_seconds: float
    coverage: float


def _aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("power interval timestamps must be timezone-aware")


def account_power_intervals(
    intervals: list[PowerInterval], *, window_start: datetime, window_end: datetime,
) -> PowerAccounting:
    """Sum signed throughput and coverage from exactly the same segments.

    Polarity is deliberately not labeled charge/discharge: that mapping belongs
    to the calibrated source contract. Missing time is not measured zero power.
    All input segments are validated, including segments outside the window;
    overlap and out-of-order evidence fail closed rather than being repaired.
    """
    _aware(window_start)
    _aware(window_end)
    # Normalize before arithmetic so DST fold/offset transitions measure elapsed
    # time, even when callers pass two datetimes sharing a ZoneInfo instance.
    start = window_start.astimezone(timezone.utc)
    end = window_end.astimezone(timezone.utc)
    window_seconds = (end - start).total_seconds()
    if window_seconds <= 0:
        raise ValueError("power accounting window must be positive")
    positive_wh = negative_wh = covered = 0.0
    previous_end = None
    for interval in intervals:
        _aware(interval.start)
        _aware(interval.end)
        left = interval.start.astimezone(timezone.utc)
        right = interval.end.astimezone(timezone.utc)
        if right <= left or (previous_end is not None and left < previous_end):
            raise ValueError("power intervals must be positive, ordered and nonoverlapping")
        if (isinstance(interval.watts, bool)
                or not isinstance(interval.watts, (int, float))):
            raise ValueError("power must be a finite number")
        try:
            watts = float(interval.watts)
        except OverflowError as exc:
            raise ValueError("power must be a finite number") from exc
        if not isfinite(watts):
            raise ValueError("power must be a finite number")
        previous_end = right
        seconds = max(0.0, (min(end, right) - max(start, left)).total_seconds())
        if not seconds:
            continue
        covered += seconds
        wh = watts * (seconds / 3600.0)
        positive_wh += max(0.0, wh)
        negative_wh += max(0.0, -wh)
    if not isfinite(positive_wh) or not isfinite(negative_wh):
        raise ValueError("power accounting overflow")
    return PowerAccounting(
        positive_kwh=positive_wh / 1000.0,
        negative_kwh=negative_wh / 1000.0,
        covered_seconds=covered,
        missing_seconds=max(0.0, window_seconds - covered),
        window_seconds=window_seconds,
        coverage=min(1.0, covered / window_seconds),
    )


def account_common_power(left, right, *, window_start, window_end):
    """Account two streams only over their identical qualified intersection.

    Validate both complete inputs even if their intersection is empty. The
    two-pointer walk is linear; gaps and exclusive boundaries are preserved.
    """
    for intervals in (left, right):
        account_power_intervals(intervals, window_start=window_start, window_end=window_end)
    common_left, common_right = [], []
    i = j = 0
    start, end = window_start.astimezone(timezone.utc), window_end.astimezone(timezone.utc)
    while i < len(left) and j < len(right):
        a, b = left[i], right[j]
        a_end, b_end = a.end.astimezone(timezone.utc), b.end.astimezone(timezone.utc)
        first = max(start, a.start.astimezone(timezone.utc), b.start.astimezone(timezone.utc))
        last = min(end, a_end, b_end)
        if first < last:
            common_left.append(PowerInterval(first, last, a.watts))
            common_right.append(PowerInterval(first, last, b.watts))
        if a_end <= b_end:
            i += 1
        if b_end <= a_end:
            j += 1
    return tuple(account_power_intervals(intervals, window_start=start, window_end=end)
                 for intervals in (common_left, common_right))
