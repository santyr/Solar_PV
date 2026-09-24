"""Forecast snapshot contracts that prevent retrospective future leakage."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from math import isfinite
from typing import Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from psycopg2.extras import Json


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


@dataclass(frozen=True)
class ForecastSnapshot:
    source: str
    issued_at: datetime
    valid_for: datetime
    metric: str
    value: float | None
    unit: str | None
    payload: dict[str, object]

    def __post_init__(self):
        if not _aware(self.issued_at) or not _aware(self.valid_for):
            raise ValueError("forecast timestamps must be timezone-aware")
        if self.valid_for < self.issued_at:
            raise ValueError("valid_for cannot precede issued_at")
        if not self.source or not self.metric:
            raise ValueError("forecast source and metric are required")
        if not isinstance(self.payload, dict):
            raise ValueError("forecast payload must be an object")


def select_forecast_as_of(
    snapshots: Iterable[ForecastSnapshot],
    *,
    source: str,
    metric: str,
    valid_for: datetime,
    origin: datetime,
) -> ForecastSnapshot | None:
    if not _aware(valid_for) or not _aware(origin):
        raise ValueError("selection timestamps must be timezone-aware")
    candidates = [
        snapshot
        for snapshot in snapshots
        if snapshot.source == source
        and snapshot.metric == metric
        and snapshot.valid_for == valid_for
        and snapshot.issued_at <= origin
    ]
    return max(candidates, key=lambda snapshot: snapshot.issued_at, default=None)


HOURLY_METRICS = {
    "tempF": ("temperature_f", "degF"),
    "precipPct": ("precipitation_probability_pct", "pct"),
    "precipIn": ("precipitation_in", "in"),
    "radiationWm2": ("radiation_wm2", "W/m2"),
    "windMph": ("wind_mph", "mph"),
    "weatherCode": ("weather_code", None),
}
DAILY_METRICS = {
    "highF": ("daily_high_f", "degF"),
    "lowF": ("daily_low_f", "degF"),
    "precipPct": ("daily_precipitation_probability_pct", "pct"),
    "precipSumIn": ("daily_precipitation_in", "in"),
    "weatherCode": ("daily_weather_code", None),
    "pvKwh": ("daily_pv_kwh", "kWh"),
}


def _timestamp(value: object, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"forecast {name} must be ISO-8601") from exc
    if not _aware(parsed):
        raise ValueError(f"forecast {name} must include timezone information")
    return parsed


def _metric_value(value: object) -> float | None:
    if value is None:
        return None
    if type(value) not in (int, float):
        raise ValueError("forecast metric must be finite numeric or null")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("forecast metric must be finite numeric or null") from exc
    if not isfinite(result):
        raise ValueError("forecast metric must be finite numeric or null")
    return result


def _provenance(payload: object) -> dict[str, object]:
    version = payload.get("version") if isinstance(payload, dict) else None
    if type(version) is not int or version not in (1, 2):
        raise ValueError("forecast detail version must be 1 or 2")
    result: dict[str, object] = {"forecast_version": version}
    if version == 1:
        return result
    adjustment = payload.get("temperatureAdjustment")
    if not isinstance(adjustment, dict):
        raise ValueError("temperatureAdjustment is required")
    for key in ("highCorrectionF", "lowCorrectionF"):
        if _metric_value(adjustment.get(key)) is None:
            raise ValueError("temperatureAdjustment corrections are required")
    if adjustment.get("hourlyMethod") not in ("daily-fallback", "hourly-blend"):
        raise ValueError("temperatureAdjustment method is invalid")
    buckets = adjustment.get("hourBuckets")
    if not isinstance(buckets, list) or len(buckets) != 24:
        raise ValueError("temperatureAdjustment requires 24 buckets")
    for hour, bucket in enumerate(buckets):
        if (
            not isinstance(bucket, dict)
            or type(bucket.get("hour")) is not int
            or bucket["hour"] != hour
        ):
            raise ValueError("temperatureAdjustment buckets must be ordered")
        count = bucket.get("count")
        weight = _metric_value(bucket.get("weight"))
        if (
            type(count) is not int
            or count < 0
            or weight is None
            or not 0 <= weight <= 1
        ):
            raise ValueError("temperatureAdjustment bucket count/weight invalid")
    result["temperatureAdjustment"] = deepcopy(adjustment)
    return result


def snapshots_from_openhab_detail(payload: dict[str, object]) -> list[ForecastSnapshot]:
    """Normalize the additive OpenHAB forecast-detail Item without losing origin."""
    provenance = _provenance(payload)
    issued_at = _timestamp(payload.get("generatedAt"), "generatedAt")
    try:
        zone = ZoneInfo(str(payload["timezone"]))
    except (KeyError, ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("forecast timezone is invalid") from exc
    days = payload.get("days")
    if not isinstance(days, list):
        raise ValueError("forecast days must be an array")
    snapshots = []
    for day in days:
        if not isinstance(day, dict):
            raise ValueError("forecast day must be an object")
        try:
            forecast_day = date.fromisoformat(day["date"])
            # A daily summary covers the named local day; its valid-for instant
            # is the following local midnight, including across DST changes.
            valid_day = datetime.combine(forecast_day + timedelta(days=1), time(), zone)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("forecast day date is invalid") from exc
        summary = day.get("summary", {})
        hours = day.get("hours", [])
        if not isinstance(summary, dict) or not isinstance(hours, list):
            raise ValueError("forecast day summary/hours are invalid")
        daily_values = {
            field: _metric_value(summary[field])
            for field in DAILY_METRICS
            if field in summary
        }
        if valid_day >= issued_at:
            for field, value in daily_values.items():
                metric, unit = DAILY_METRICS[field]
                snapshots.append(ForecastSnapshot(
                    source="open_meteo_openhab",
                    issued_at=issued_at,
                    valid_for=valid_day,
                    metric=metric,
                    value=value,
                    unit=unit,
                    payload={**provenance, "forecast_day": forecast_day.isoformat()},
                ))
        for hour in hours:
            if not isinstance(hour, dict):
                raise ValueError("forecast hour must be an object")
            valid_for = _timestamp(hour.get("at"), "hour at")
            hourly_values = {
                field: _metric_value(hour[field])
                for field in HOURLY_METRICS
                if field in hour
            }
            if valid_for < issued_at:
                continue
            for field, value in hourly_values.items():
                metric, unit = HOURLY_METRICS[field]
                snapshots.append(ForecastSnapshot(
                    source="open_meteo_openhab",
                    issued_at=issued_at,
                    valid_for=valid_for,
                    metric=metric,
                    value=value,
                    unit=unit,
                    payload=provenance,
                ))
    return snapshots


def persist_forecast_snapshots(connection, snapshots: Iterable[ForecastSnapshot]) -> int:
    """Insert immutable forecast facts; duplicate snapshots are a successful no-op."""
    inserted = 0
    with connection.cursor() as cursor:
        for snapshot in snapshots:
            cursor.execute(
                """INSERT INTO energy_analytics.forecast_snapshots
                   (source, issued_at, valid_for, metric, value, unit, payload)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (source, issued_at, valid_for, metric) DO NOTHING""",
                (
                    snapshot.source,
                    snapshot.issued_at,
                    snapshot.valid_for,
                    snapshot.metric,
                    snapshot.value,
                    snapshot.unit,
                    Json(snapshot.payload),
                ),
            )
            inserted += max(0, cursor.rowcount)
    connection.commit()
    return inserted
