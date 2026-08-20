"""Bounded PostgreSQL reads for the observational Energy UI payload."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .report_reader import fetch_daily_report_rows, fetch_module_report_rows
from .reports import lifecycle_report, module_health_report, winter_report
from .reader import ITEM_TABLE
from .ui_payload import build_energy_ui_payload


FORECAST_CURRENT_AGE = timedelta(hours=6)


def _current_health_status(policy, raw_value, now, stale_after_seconds):
    if policy == "status_must_equal_OK":
        return raw_value.strip().upper() == "OK"
    if policy == "numeric_must_equal_1":
        try:
            return float(raw_value) == 1.0
        except ValueError:
            return False
    if policy == "timestamp_threshold":
        if stale_after_seconds is None:
            return False
        try:
            reported_at = datetime.fromisoformat(raw_value)
        except ValueError:
            return False
        if reported_at.tzinfo is None or reported_at.utcoffset() is None:
            return False
        age = (now - reported_at).total_seconds()
        return 0 <= age <= stale_after_seconds
    return False


def fetch_live_subsystem_health(connection, config, resolved_sources, *, generated_at):
    """Read one current, bounded freshness value per required source."""
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    definitions = {source.canonical_name: source for source in config.sources}
    required = [source for source in resolved_sources if source.required]
    groups = {"bms": [], "schneider": [], "weather": []}
    reasons = []
    collector_ok = bool(required)
    cached = {}
    for source in required:
        definition = definitions.get(source.canonical_name)
        table = source.freshness_table_name
        if definition is None or source.status != "ok" or not table or not ITEM_TABLE.fullmatch(table):
            collector_ok = False
            reasons.append("collector_source_contract_incomplete")
            healthy = False
        else:
            if table not in cached:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"SELECT value FROM public.{table} "
                        "WHERE time <= %s ORDER BY time DESC LIMIT 1",
                        (generated_at,),
                    )
                    cached[table] = cursor.fetchone()
            row = cached[table]
            if row is None:
                collector_ok = False
                reasons.append("collector_freshness_value_missing")
                healthy = False
            else:
                healthy = _current_health_status(
                    definition.stale_policy, str(row[0]), generated_at,
                    definition.stale_after_seconds,
                )
        name = source.canonical_name
        group = (
            "bms" if name.startswith("battery.")
            else "schneider" if name.startswith(("pv.", "house."))
            else "weather" if name.startswith(("weather.", "solar."))
            else None
        )
        if group is not None:
            groups[group].append(healthy)

    health = {}
    for group, values in groups.items():
        if not values:
            health[group] = "unavailable"
            reasons.append(f"{group}_live_health_missing")
        elif all(values):
            health[group] = "ok"
        else:
            health[group] = "fault"
            reasons.append(f"{group}_live_health_not_ok")
    health.update({
        "collector": "ok" if collector_ok else "unavailable",
        "publisher": "ok",
        "reasons": sorted(set(reasons)),
    })
    return health


def fetch_ui_health_and_forecast(
    connection,
    *,
    through_date: date,
    generated_at: datetime,
    timezone_name: str,
    live_health: dict[str, object],
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
        "bms": live_health["bms"],
        "schneider": live_health["schneider"],
        "weather": live_health["weather"],
        "collector": live_health["collector"],
        "publisher": live_health["publisher"],
        "reasons": sorted(set(reasons + list(live_health.get("reasons", [])))),
    }
    return forecast, health


def build_energy_ui_snapshot(
    connection,
    epochs,
    *,
    generated_at: datetime,
    timezone_name: str = "America/Denver",
    live_health: dict[str, object],
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
        live_health=live_health,
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
