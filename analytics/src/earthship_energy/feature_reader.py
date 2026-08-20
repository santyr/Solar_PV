"""Read a bounded, leakage-safe feature grid from raw and compact PostgreSQL data."""

from __future__ import annotations

from datetime import datetime

from .reader import ITEM_TABLE


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
) -> list[dict[str, object]]:
    if end_exclusive <= start:
        raise ValueError("feature export end must be after start")
    if cadence_minutes not in {5, 15}:
        raise ValueError("feature cadence must be 5 or 15 minutes")
    for table in tables.values():
        if not ITEM_TABLE.fullmatch(table):
            raise ValueError("invalid OpenHAB Item table name")
    missing = REQUIRED_TABLES - set(tables)
    if missing:
        raise ValueError(f"feature sources unresolved: {sorted(missing)}")
    soc = tables["battery.soc_pct"]
    pv = tables["pv.input_power_w"]
    load = tables["house.ac_power_w"]
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
                 {_value(soc, "g.at")} AS battery_soc_pct,
                 {_value(soc, "g.at - interval '1 hour'")} AS battery_soc_pct_lag_1h,
                 {_value(pv, "g.at")} AS pv_power_w,
                 {_value(pv, "g.at - interval '1 hour'")} AS pv_power_w_lag_1h,
                 {_value(load, "g.at")} AS load_power_w,
                 {_value(load, "g.at - interval '1 hour'")} AS load_power_w_lag_1h,
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
                 WHEN ftemp.issued_at IS NULL THEN 'unavailable'
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
            AND valid_for >= r.at
          ORDER BY valid_for, issued_at DESC
          LIMIT 1
        ) ftemp ON true
        LEFT JOIN energy_analytics.forecast_snapshots frad
          ON frad.source = ftemp.source
         AND frad.issued_at = ftemp.issued_at
         AND frad.valid_for = ftemp.valid_for
         AND frad.metric = 'radiation_wm2'
        LEFT JOIN LATERAL (
          SELECT issued_at, valid_for, value
          FROM energy_analytics.forecast_snapshots
          WHERE metric = 'daily_pv_kwh'
            AND issued_at <= r.at
            AND (valid_for AT TIME ZONE %s)::date =
                (r.at AT TIME ZONE %s)::date
          ORDER BY issued_at DESC
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
            ),
        )
        return [dict(zip(FEATURE_FIELDS, row)) for row in cursor.fetchall()]
