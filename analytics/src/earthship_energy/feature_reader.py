"""Read a bounded, leakage-safe feature grid from raw and compact PostgreSQL data."""

from __future__ import annotations

from bisect import bisect_right
from datetime import datetime, timedelta, timezone

from .bms_evidence import EvidenceSequenceError
from .reader import ITEM_TABLE, fetch_bms_soc_intervals
from .series import local_day_bounds
from .power_reader import read_power_history
from .power_intervals import account_power_intervals


def _power_lookup(intervals, start, end):
    # Validate the entire stream, including segments outside the lookup window.
    account_power_intervals(intervals, window_start=start, window_end=end)
    if any(segment.watts < 0 for segment in intervals):
        raise ValueError('PV power cannot be negative')
    starts = [segment.start.astimezone(timezone.utc) for segment in intervals]

    def value_at(at):
        index = bisect_right(starts, at)
        if index and at < intervals[index - 1].end.astimezone(timezone.utc):
            return intervals[index - 1].watts
        return None

    return value_at


def _soc_lookup(connection, table, start, end, epochs, timezone_name):
    """Index original qualified segments, never interpolating across gaps."""
    intervals = []
    for epoch in epochs:
        # Undated historical banks cannot authorize atomic evidence.
        if epoch.start_local_date is None:
            continue
        bank_start = local_day_bounds(epoch.start_local_date, timezone_name)[0]
        bank_end = (local_day_bounds(epoch.end_local_date_exclusive, timezone_name)[0]
                    if epoch.end_local_date_exclusive is not None else None)
        left, right = max(start, bank_start), min(end, bank_end or end)
        if right <= left or table is None:
            continue
        try:
            intervals.extend(fetch_bms_soc_intervals(
                connection, table, left, right, epoch_start=bank_start, epoch_end=bank_end,
            ))
        except EvidenceSequenceError:
            # Ambiguous evidence never falls back to legacy numeric history.
            continue
    intervals.sort(key=lambda interval: interval.start)
    if any(left.end > right.start for left, right in zip(intervals, intervals[1:])):
        raise ValueError("physical bank evidence intervals overlap")
    starts = [interval.start for interval in intervals]

    def value_at(at):
        index = bisect_right(starts, at) - 1
        if index >= 0 and at < intervals[index].end:
            return intervals[index].soc
        return None

    return value_at


REQUIRED_TABLES = {
    "battery.soc_pct",
    "pv.input_power_w",
    "house.ac_power_w",
    "weather.outdoor_temperature_c",
    "weather.irradiance_w_m2",
}

FEATURE_FIELDS = (
    "at", "epoch_id", "battery_soc_pct", "battery_soc_pct_lag_1h",
    "pv_power_w", "pv_power_w_lag_1h", "load_power_w",
    "load_power_w_lag_1h", "outdoor_temperature_c",
    "outdoor_irradiance_w_m2", "daylight_observed", "dishwasher_active",
    "shurflo_pump_active", "forecast_temperature_f",
    "forecast_radiation_w_m2", "forecast_daily_pv_kwh",
    "forecast_issued_at", "forecast_valid_for",
    "daily_pv_forecast_issued_at", "daily_pv_forecast_valid_for",
    "forecast_status", "shade_confidence", "kiva_confidence",
)


def _value(table: str, at_expression: str) -> str:
    return (
        f"(SELECT value::double precision FROM public.{table} "
        f"WHERE time <= {at_expression} ORDER BY time DESC LIMIT 1)"
    )


def _switch(table: str | None) -> str:
    if table is None:
        return "NULL::boolean"
    return (
        f"(SELECT CASE upper(value::text) WHEN 'ON' THEN true "
        f"WHEN 'OFF' THEN false ELSE NULL END FROM public.{table} "
        "WHERE time <= g.at ORDER BY time DESC LIMIT 1)"
    )


def _converted(expression: str, conversion: str | None) -> str:
    if conversion is None:
        return expression
    if conversion == "fahrenheit_to_celsius":
        return f"(({expression}) - 32.0) * 5.0 / 9.0"
    raise ValueError(f"unsupported numeric conversion: {conversion}")


def fetch_feature_rows(
    connection,
    tables: dict[str, str],
    start: datetime,
    end_exclusive: datetime,
    *,
    cadence_minutes: int,
    timezone_name: str,
    conversions: dict[str, str | None] | None = None,
    atomic_soc: bool = False,
    soc_evidence_table: str | None = None,
    bank_epochs=None,
    power_settings=None,
    power_table=None,
    power_cutover=None,
) -> list[dict[str, object]]:
    if any(at.tzinfo is None or at.utcoffset() is None for at in (start, end_exclusive)):
        raise ValueError("feature window must be timezone-aware")
    start, end_exclusive = start.astimezone(timezone.utc), end_exclusive.astimezone(timezone.utc)
    if end_exclusive <= start:
        raise ValueError("feature export end must be after start")
    if cadence_minutes not in {5, 15}:
        raise ValueError("feature cadence must be 5 or 15 minutes")
    power_args = (power_settings, power_table, power_cutover)
    qualified_power = any(value is not None for value in power_args)
    if qualified_power and not all(value is not None for value in power_args):
        raise ValueError('qualified power requires settings, table and cutover')
    if qualified_power and end_exclusive - start > timedelta(hours=24):
        raise ValueError('qualified feature window must be at most 24 hours plus one-hour lag')
    if atomic_soc and bank_epochs is None:
        raise ValueError("atomic SoC requires configured physical bank epochs")
    if soc_evidence_table is not None and not ITEM_TABLE.fullmatch(soc_evidence_table):
        raise ValueError("invalid OpenHAB evidence table name")
    for table in tables.values():
        if not ITEM_TABLE.fullmatch(table):
            raise ValueError("invalid OpenHAB Item table name")
    required = REQUIRED_TABLES - ({'pv.input_power_w', 'house.ac_power_w'} if qualified_power else set())
    missing = required - set(tables)
    if missing:
        raise ValueError(f"feature sources unresolved: {sorted(missing)}")
    soc = tables["battery.soc_pct"]
    soc_value = "NULL::double precision" if atomic_soc else _value(soc, "g.at")
    soc_lag = ("NULL::double precision" if atomic_soc
               else _value(soc, "g.at - interval '1 hour'"))
    pv = tables.get("pv.input_power_w")
    load = tables.get("house.ac_power_w")
    pv_value = 'NULL::double precision' if qualified_power else _value(pv, 'g.at')
    pv_lag = 'NULL::double precision' if qualified_power else _value(pv, "g.at - interval '1 hour'")
    load_value = 'NULL::double precision' if qualified_power else _value(load, 'g.at')
    load_lag = 'NULL::double precision' if qualified_power else _value(load, "g.at - interval '1 hour'")
    power_lookup = None
    if qualified_power:
        history = read_power_history(power_settings, power_table,
            start - timedelta(hours=1), end_exclusive, cutover=power_cutover)
        power_lookup = _power_lookup(history['pv.input_power_w'],
                                    start - timedelta(hours=1), end_exclusive)
    temperature = tables["weather.outdoor_temperature_c"]
    irradiance = tables["weather.irradiance_w_m2"]
    dishwasher = _switch(tables.get("load.dishwasher_state"))
    pump = _switch(tables.get("load.shurflo_pump_state"))
    conversions = conversions or {}
    temperature_value = _converted(
        _value(temperature, "g.at"),
        conversions.get("weather.outdoor_temperature_c"),
    )
    sql = f"""
        WITH grid AS (
          SELECT generate_series(
            %s::timestamptz,
            %s::timestamptz - interval '1 second',
            make_interval(mins => %s)
          ) AS at
        ),
        raw AS (
          SELECT g.at,
                 {soc_value} AS battery_soc_pct,
                 {soc_lag} AS battery_soc_pct_lag_1h,
                 {pv_value} AS pv_power_w,
                 {pv_lag} AS pv_power_w_lag_1h,
                 {load_value} AS load_power_w,
                 {load_lag} AS load_power_w_lag_1h,
                 {temperature_value} AS outdoor_temperature_c,
                 {_value(irradiance, "g.at")} AS outdoor_irradiance_w_m2,
                 {dishwasher} AS dishwasher_active,
                 {pump} AS shurflo_pump_active
          FROM grid g
        )
        SELECT r.at,
               epoch.epoch_id,
               r.battery_soc_pct,
               r.battery_soc_pct_lag_1h,
               r.pv_power_w,
               r.pv_power_w_lag_1h,
               r.load_power_w,
               r.load_power_w_lag_1h,
               r.outdoor_temperature_c,
               r.outdoor_irradiance_w_m2,
               COALESCE(r.outdoor_irradiance_w_m2 > 5, false),
               r.dishwasher_active,
               r.shurflo_pump_active,
               ftemp.value,
               frad.value,
               fpv.value,
               ftemp.issued_at,
               ftemp.valid_for,
               fpv.issued_at,
               fpv.valid_for,
               CASE
                 WHEN ftemp.issued_at IS NULL OR frad.issued_at IS NULL THEN 'unavailable'
                 WHEN r.at - ftemp.issued_at > interval '3 hours' THEN 'stale'
                 ELSE 'current'
               END,
               COALESCE(shade.confidence, 0.0),
               COALESCE(kiva.confidence, 0.0)
        FROM raw r
        LEFT JOIN LATERAL (
          SELECT epoch_id
          FROM energy_analytics.system_epochs
          WHERE (start_local_date IS NULL OR
                 (r.at AT TIME ZONE %s)::date >= start_local_date)
            AND (end_local_date_exclusive IS NULL OR
                 (r.at AT TIME ZONE %s)::date < end_local_date_exclusive)
          ORDER BY current_analytics DESC, start_local_date DESC NULLS LAST
          LIMIT 1
        ) epoch ON true
        LEFT JOIN LATERAL (
          SELECT source, issued_at, valid_for, value
          FROM energy_analytics.forecast_snapshots
          WHERE metric = 'temperature_f'
            AND issued_at <= r.at
            AND captured_at <= r.at
            AND valid_for >= r.at
          ORDER BY valid_for, issued_at DESC
          LIMIT 1
        ) ftemp ON true
        LEFT JOIN energy_analytics.forecast_snapshots frad
          ON frad.source = ftemp.source
         AND frad.issued_at = ftemp.issued_at
         AND frad.valid_for = ftemp.valid_for
         AND frad.metric = 'radiation_wm2'
         AND frad.captured_at <= r.at
        LEFT JOIN LATERAL (
          SELECT issued_at, valid_for, value
          FROM energy_analytics.forecast_snapshots
          WHERE metric = 'daily_pv_kwh'
            AND payload->>'forecast_day' = (r.at AT TIME ZONE %s)::date::text
            AND issued_at <= r.at
            AND captured_at <= r.at
            AND valid_for =
                (((r.at AT TIME ZONE %s)::date + 1)::timestamp AT TIME ZONE %s)
          ORDER BY issued_at DESC, captured_at DESC
          LIMIT 1
        ) fpv ON true
        LEFT JOIN LATERAL (
          SELECT confidence
          FROM energy_analytics.system_events
          WHERE event_kind = 'indoor_shade'
            AND started_at <= r.at
            AND (ended_at IS NULL OR ended_at >= r.at)
          ORDER BY confidence DESC, started_at DESC
          LIMIT 1
        ) shade ON true
        LEFT JOIN LATERAL (
          SELECT confidence
          FROM energy_analytics.system_events
          WHERE event_kind = 'kiva_use'
            AND started_at <= r.at
            AND (ended_at IS NULL OR ended_at >= r.at)
          ORDER BY confidence DESC, started_at DESC
          LIMIT 1
        ) kiva ON true
        ORDER BY r.at
    """
    with connection.cursor() as cursor:
        cursor.execute(
            sql,
            (
                start, end_exclusive, cadence_minutes,
                timezone_name, timezone_name, timezone_name, timezone_name,
                timezone_name,
            ),
        )
        rows = [dict(zip(FEATURE_FIELDS, row)) for row in cursor.fetchall()]
    if atomic_soc:
        lookup = _soc_lookup(connection, soc_evidence_table, start - timedelta(hours=1),
                             end_exclusive, bank_epochs, timezone_name)
        for row in rows:
            at = row["at"].astimezone(timezone.utc)
            row["battery_soc_pct"] = lookup(at)
            row["battery_soc_pct_lag_1h"] = lookup(at - timedelta(hours=1))
    if qualified_power:
        for row in rows:
            at = row['at'].astimezone(timezone.utc)
            row['pv_power_w'] = power_lookup(at)
            row['pv_power_w_lag_1h'] = power_lookup(at - timedelta(hours=1))
            # No independently qualified AC-load source exists yet.
            row['load_power_w'] = row['load_power_w_lag_1h'] = None
    return rows
