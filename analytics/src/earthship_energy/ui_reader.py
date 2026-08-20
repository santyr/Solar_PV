"""Bounded PostgreSQL reads for the observational Energy UI payload."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .report_reader import fetch_daily_report_rows, fetch_module_report_rows
from .reports import lifecycle_report, module_health_report, winter_report
from .ui_payload import build_energy_ui_payload


FORECAST_CURRENT_AGE = timedelta(hours=6)


def _group_status(
    rows: dict[str, str], prefixes: tuple[str, ...], missing_reason: str,
    reasons: list[str],
) -> str:
    values = [quality for name, quality in rows.items() if name.startswith(prefixes)]
    if not values:
        reasons.append(missing_reason)
        return "unavailable"
    return "ok" if all(value == "ok" for value in values) else "degraded"


def fetch_ui_health_and_forecast(
    connection,
    *,
    through_date: date,
    generated_at: datetime,
    timezone_name: str,
) -> tuple[dict[str, object], dict[str, object]]:
    """Read one completed quality day and one as-of forecast snapshot."""
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    timezone = ZoneInfo(timezone_name)
    forecast_floor = datetime.combine(
        generated_at.astimezone(timezone).date(), time.min, tzinfo=timezone
    )
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT canonical_name, quality
               FROM energy_analytics.daily_source_quality
               WHERE local_date = %s
               ORDER BY canonical_name""",
            (through_date,),
        )
        quality_rows = {str(name): str(quality) for name, quality in cursor.fetchall()}
        cursor.execute(
            """SELECT issued_at, valid_for, value
               FROM energy_analytics.forecast_snapshots
               WHERE metric = 'daily_pv_kwh'
                 AND issued_at <= %s AND valid_for >= %s
               ORDER BY issued_at DESC, valid_for ASC
               LIMIT 1""",
            (generated_at, forecast_floor),
        )
        forecast_row = cursor.fetchone()

    reasons: list[str] = []
    analytics = (
        "unavailable" if not quality_rows
        else "ok" if all(value == "ok" for value in quality_rows.values())
        else "degraded"
    )
    if analytics == "unavailable":
        reasons.append("missing_daily_source_quality")
    elif analytics == "degraded":
        reasons.append("daily_source_quality_not_ok")
    bms = _group_status(
        quality_rows, ("battery.",), "missing_bms_quality_evidence", reasons
    )
    schneider = _group_status(
        quality_rows, ("pv.", "house."),
        "missing_schneider_quality_evidence", reasons,
    )
    weather = _group_status(
        quality_rows, ("weather.", "solar."),
        "missing_weather_quality_evidence", reasons,
    )
    collector = "ok" if analytics == "ok" else (
        "unavailable" if analytics == "unavailable" else "degraded"
    )

    if forecast_row is None:
        forecast = {
            "status": "unavailable",
            "issuedAt": None,
            "validFor": None,
            "pv24hKwh": None,
            "reason": "no_forecast_snapshot",
        }
        forecast_health = "unavailable"
        reasons.append("no_forecast_snapshot")
    else:
        issued_at, valid_for, value = forecast_row
        if (
            issued_at.tzinfo is None or issued_at.utcoffset() is None
            or valid_for.tzinfo is None or valid_for.utcoffset() is None
        ):
            raise ValueError("forecast database timestamps must be timezone-aware")
        age = generated_at - issued_at
        current = timedelta(0) <= age <= FORECAST_CURRENT_AGE
        forecast = {
            "status": "current" if current else "stale",
            "issuedAt": issued_at.isoformat(),
            "validFor": valid_for.isoformat(),
            "pv24hKwh": float(value) if value is not None else None,
            "reason": None if current else "forecast_issue_older_than_6h",
        }
        forecast_health = "ok" if current else "stale"
        if not current:
            reasons.append("forecast_issue_older_than_6h")
    health = {
        "analytics": analytics,
        "forecast": forecast_health,
        "bms": bms,
        "schneider": schneider,
        "weather": weather,
        "collector": collector,
        "reasons": sorted(set(reasons)),
    }
    return forecast, health


def build_energy_ui_snapshot(
    connection,
    epochs,
    *,
    generated_at: datetime,
    timezone_name: str = "America/Denver",
) -> dict[str, object]:
    """Assemble reports only through the last completed site-local day."""
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    current = [epoch for epoch in epochs if epoch.current_analytics]
    if len(current) != 1:
        raise ValueError("exactly one current analytics epoch is required")
    epoch = current[0]
    if epoch.start_local_date is None:
        raise ValueError("current analytics epoch requires a start date")
    timezone = ZoneInfo(timezone_name)
    completed_end = generated_at.astimezone(timezone).date()
    rows = (
        fetch_daily_report_rows(
            connection, epoch.epoch_id, epoch.start_local_date, completed_end
        )
        if completed_end > epoch.start_local_date else []
    )
    approved = [row for row in rows if row.get("quality") == "ok"]
    through_date = approved[-1]["local_date"] if approved else completed_end - timedelta(days=1)
    module_start_date = max(
        epoch.start_local_date, completed_end - timedelta(days=365)
    )
    module_rows = fetch_module_report_rows(
        connection,
        datetime.combine(module_start_date, time.min, tzinfo=timezone),
        generated_at,
    )
    forecast, health = fetch_ui_health_and_forecast(
        connection,
        through_date=through_date,
        generated_at=generated_at,
        timezone_name=timezone_name,
    )
    winter = lifecycle = None
    if approved:
        winter = winter_report(
            approved,
            nominal_usable_kwh=epoch.nominal_usable_kwh,
            reserve_soc_pct=20.0,
        )
        lifecycle = lifecycle_report(approved)
    return build_energy_ui_payload(
        generated_at=generated_at,
        timezone_name=timezone_name,
        epoch_id=epoch.epoch_id,
        daily_rows=approved,
        winter=winter,
        lifecycle=lifecycle,
        module_health=module_health_report(module_rows),
        forecast=forecast,
        health=health,
    )
