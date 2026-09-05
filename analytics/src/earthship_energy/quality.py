"""Pure source-health assessment for daily analytics evidence."""

from __future__ import annotations

from datetime import datetime, timedelta


def _coverage_quality(coverage: float) -> str:
    if coverage >= 0.9:
        return "ok"
    if coverage >= 0.5:
        return "partial"
    return "insufficient_data"


def _parse_aware_datetime(raw: str) -> datetime | None:
    try:
        value = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return None
    return value


def assess_source_quality(
    *,
    canonical_name: str,
    row_count: int,
    first_at: datetime | None,
    last_at: datetime | None,
    window_start: datetime,
    window_end: datetime,
    stale_policy: str,
    stale_after_seconds: int | None,
    freshness_item: str | None,
    freshness_points: list[tuple[datetime, str]],
) -> dict[str, object]:
    """Measure how much of a window is authorized by explicit health evidence."""

    for label, value in (("window_start", window_start), ("window_end", window_end)):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{label} must be timezone-aware")
    window_seconds = (window_end - window_start).total_seconds()
    if window_seconds <= 0:
        raise ValueError("quality window must be positive")
    if freshness_item is None:
        return {
            "canonical_name": canonical_name,
            "row_count": row_count,
            "first_at": first_at,
            "last_at": last_at,
            "coverage": 0.0,
            "stale_intervals": 0,
            "quality": "freshness_unverified",
            "detail": {
                "policy": stale_policy,
                "freshness_basis": None,
                "reason": "no explicit freshness companion",
            },
        }

    valid_seconds = 0.0
    stale_intervals = 0
    ordered = sorted(freshness_points)
    for observed_at, _ in ordered:
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("freshness observation timestamps must be timezone-aware")
    for index, (observed_at, raw_value) in enumerate(ordered):
        interval_start = max(window_start, observed_at)
        next_at = ordered[index + 1][0] if index + 1 < len(ordered) else window_end
        interval_end = min(window_end, next_at)
        seconds = max(0.0, (interval_end - interval_start).total_seconds())
        if seconds == 0:
            continue
        authorized = 0.0
        if stale_policy == "timestamp_threshold":
            if stale_after_seconds is None:
                raise ValueError("timestamp_threshold requires stale_after_seconds")
            reported_at = _parse_aware_datetime(raw_value)
            if reported_at is not None and reported_at <= observed_at:
                expiry = reported_at + timedelta(seconds=stale_after_seconds)
                authorized = max(
                    0.0,
                    (min(interval_end, expiry) - interval_start).total_seconds(),
                )
                authorized = min(seconds, authorized)
        elif stale_policy == "status_must_equal_OK":
            authorized = seconds if raw_value.strip().upper() == "OK" else 0.0
        elif stale_policy == "numeric_must_equal_1":
            try:
                authorized = seconds if float(raw_value) == 1.0 else 0.0
            except ValueError:
                authorized = 0.0
        else:
            raise ValueError(f"unsupported companion freshness policy: {stale_policy}")
        valid_seconds += authorized
        if authorized < seconds:
            stale_intervals += 1

    coverage = min(1.0, max(0.0, valid_seconds / window_seconds))
    return {
        "canonical_name": canonical_name,
        "row_count": row_count,
        "first_at": first_at,
        "last_at": last_at,
        "coverage": coverage,
        "stale_intervals": stale_intervals,
        "quality": _coverage_quality(coverage),
        "detail": {
            "policy": stale_policy,
            "freshness_basis": freshness_item,
            "stale_after_seconds": stale_after_seconds,
            "valid_seconds": valid_seconds,
            "window_seconds": window_seconds,
        },
    }
