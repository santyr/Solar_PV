"""Forecast snapshot contracts that prevent retrospective future leakage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
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


def snapshots_from_openhab_detail(payload: dict[str, object]) -> list[ForecastSnapshot]:
    """Normalize the additive OpenHAB forecast-detail Item without losing origin."""
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("forecast detail version must be 1")
    issued_at = _timestamp(payload.get("generatedAt"), "generatedAt")
    try:
        zone = ZoneInfo(str(payload["timezone"]))
    except (KeyError, ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("forecast timezone is invalid") from exc
    days = payload.get("days")
    if not isinstance(days, list):
        raise ValueError("forecast days must be an array")
    snapshots = []
    provenance = {"forecast_version": 1}
    for day in days:
        if not isinstance(day, dict):
            raise ValueError("forecast day must be an object")
        try:
            valid_day = datetime.combine(date.fromisoformat(day["date"]), time(), zone)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("forecast day date is invalid") from exc
        summary = day.get("summary", {})
        hours = day.get("hours", [])
        if not isinstance(summary, dict) or not isinstance(hours, list):
            raise ValueError("forecast day summary/hours are invalid")
        for field, (metric, unit) in DAILY_METRICS.items():
            if valid_day >= issued_at and field in summary:
                value = summary[field]
                snapshots.append(ForecastSnapshot(
                    source="open_meteo_openhab",
                    issued_at=issued_at,
                    valid_for=valid_day,
                    metric=metric,
                    value=float(value) if value is not None else None,
                    unit=unit,
                    payload=provenance,
                ))
        for hour in hours:
            if not isinstance(hour, dict):
                raise ValueError("forecast hour must be an object")
            valid_for = _timestamp(hour.get("at"), "hour at")
            if valid_for < issued_at:
                continue
            for field, (metric, unit) in HOURLY_METRICS.items():
                if field in hour:
                    value = hour[field]
                    snapshots.append(ForecastSnapshot(
                        source="open_meteo_openhab",
                        issued_at=issued_at,
                        valid_for=valid_for,
                        metric=metric,
                        value=float(value) if value is not None else None,
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
