"""Read compact daily products for deterministic reports."""

from __future__ import annotations

from datetime import date
from datetime import datetime


MAX_MODULE_REPORT_ROWS = 4096


FIELDS = (
    "local_date", "min_soc_pct", "reached_99", "charge_kwh",
    "discharge_kwh", "daily_efc", "cumulative_efc",
    "hours_above_90", "hours_above_95", "min_temperature_c",
    "max_temperature_c", "quality", "pv_kwh", "load_kwh",
)


def fetch_daily_report_rows(
    connection, epoch_id: str, start: date, end_exclusive: date
) -> list[dict[str, object]]:
    if end_exclusive <= start:
        raise ValueError("report end must be after start")
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT b.local_date, b.min_soc_pct, b.reached_99,
                      b.charge_kwh, b.discharge_kwh, b.daily_efc,
                      b.cumulative_efc, b.hours_above_90, b.hours_above_95,
                      b.min_temperature_c, b.max_temperature_c,
                      CASE WHEN b.quality = 'ok' AND p.quality = 'ok'
                                AND l.quality = 'ok' AND w.quality = 'ok'
                           THEN 'ok' ELSE 'partial' END,
                      p.pv_kwh, l.load_kwh
               FROM energy_analytics.daily_battery b
               JOIN energy_analytics.daily_pv p
                 ON p.local_date = b.local_date AND p.epoch_id = b.epoch_id
               JOIN energy_analytics.daily_load l
                 ON l.local_date = b.local_date AND l.epoch_id = b.epoch_id
               JOIN energy_analytics.daily_weather w
                 ON w.local_date = b.local_date AND w.epoch_id = b.epoch_id
               WHERE b.epoch_id = %s AND b.local_date >= %s
                 AND b.local_date < %s
               ORDER BY b.local_date""",
            (epoch_id, start, end_exclusive),
        )
        return [dict(zip(FIELDS, row)) for row in cursor.fetchall()]


MODULE_FIELDS = (
    "batch_id", "source_name", "sha256", "module_id", "sampled_at",
    "soc_pct", "voltage_v", "current_a", "temperature_c", "cell_spread_mv",
    "charge_kwh", "discharge_kwh", "faults",
)


def fetch_module_report_rows(
    connection, start: datetime, end_exclusive: datetime
) -> list[dict[str, object]]:
    if end_exclusive <= start:
        raise ValueError("module report end must be after start")
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT * FROM (
                   SELECT b.batch_id, b.source_name, b.sha256, s.module_id,
                          s.sampled_at, s.soc_pct, s.voltage_v, s.current_a,
                          s.temperature_c, s.cell_spread_mv, s.charge_kwh,
                          s.discharge_kwh, s.faults
                   FROM energy_analytics.battery_module_samples s
                   JOIN energy_analytics.lynk_import_batches b
                     ON b.batch_id = s.batch_id
                   WHERE s.sampled_at >= %s AND s.sampled_at < %s
                   ORDER BY s.sampled_at DESC, s.module_id, b.batch_id DESC
                   LIMIT %s
               ) recent
               ORDER BY sampled_at, module_id, batch_id""",
            (start, end_exclusive, MAX_MODULE_REPORT_ROWS),
        )
        return [dict(zip(MODULE_FIELDS, row)) for row in cursor.fetchall()]
