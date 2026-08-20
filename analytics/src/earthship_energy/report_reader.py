"""Read compact daily products for deterministic reports."""

from __future__ import annotations

from datetime import date


FIELDS = (
    "local_date", "min_soc_pct", "reached_99", "charge_kwh",
    "discharge_kwh", "daily_efc", "quality", "pv_kwh", "load_kwh",
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
                      CASE WHEN b.quality = 'ok' AND p.quality = 'ok'
                                AND l.quality = 'ok' THEN 'ok' ELSE 'partial' END,
                      p.pv_kwh, l.load_kwh
               FROM energy_analytics.daily_battery b
               JOIN energy_analytics.daily_pv p
                 ON p.local_date = b.local_date AND p.epoch_id = b.epoch_id
               JOIN energy_analytics.daily_load l
                 ON l.local_date = b.local_date AND l.epoch_id = b.epoch_id
               WHERE b.epoch_id = %s AND b.local_date >= %s
                 AND b.local_date < %s
               ORDER BY b.local_date""",
            (epoch_id, start, end_exclusive),
        )
        return [dict(zip(FIELDS, row)) for row in cursor.fetchall()]
