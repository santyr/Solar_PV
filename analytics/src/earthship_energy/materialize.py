"""Idempotent writes for compact analytics derived from immutable raw data."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

from psycopg2.extras import Json

from .config import SourceConfig


class EpochConfigError(ValueError):
    pass


@dataclass(frozen=True)
class SystemEpoch:
    epoch_id: str
    start_local_date: date | None
    end_local_date_exclusive: date | None
    current_analytics: bool
    nominal_capacity_ah: float | None
    nominal_usable_kwh: float | None
    metadata: dict[str, Any]


def default_epoch_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "system-epochs.json"


def _optional_date(value: object, field: str) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EpochConfigError(f"{field} must be YYYY-MM-DD or null")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise EpochConfigError(f"{field} must be YYYY-MM-DD or null") from exc


def load_epoch_config(path: str | Path | None = None) -> tuple[SystemEpoch, ...]:
    target = Path(path) if path is not None else default_epoch_config_path()
    try:
        payload = json.loads(target.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise EpochConfigError(f"cannot load epoch config: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise EpochConfigError("epoch config version must be 1")
    rows = payload.get("epochs")
    if not isinstance(rows, list) or not rows:
        raise EpochConfigError("epochs must be a non-empty list")
    epochs = []
    standard = {
        "id", "start_local_date", "end_local_date_exclusive",
        "current_analytics", "nominal_capacity_ah", "nominal_usable_kwh",
    }
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise EpochConfigError("each epoch requires a string id")
        start = _optional_date(row.get("start_local_date"), "start_local_date")
        end = _optional_date(
            row.get("end_local_date_exclusive"), "end_local_date_exclusive"
        )
        if start is not None and end is not None and end <= start:
            raise EpochConfigError("epoch end must be after start")
        current = row.get("current_analytics")
        if not isinstance(current, bool):
            raise EpochConfigError("current_analytics must be boolean")
        epochs.append(SystemEpoch(
            epoch_id=row["id"], start_local_date=start,
            end_local_date_exclusive=end, current_analytics=current,
            nominal_capacity_ah=row.get("nominal_capacity_ah"),
            nominal_usable_kwh=row.get("nominal_usable_kwh"),
            metadata={key: value for key, value in row.items() if key not in standard},
        ))
    if len({epoch.epoch_id for epoch in epochs}) != len(epochs):
        raise EpochConfigError("duplicate epoch id")
    if sum(epoch.current_analytics for epoch in epochs) != 1:
        raise EpochConfigError("exactly one epoch must be current")
    ordered = sorted(epochs, key=lambda epoch: epoch.start_local_date or date.min)
    for left, right in zip(ordered, ordered[1:]):
        if left.end_local_date_exclusive is None or (
            right.start_local_date is None
            or right.start_local_date < left.end_local_date_exclusive
        ):
            raise EpochConfigError("epoch intervals overlap")
    return tuple(ordered)


def select_epoch(epochs: tuple[SystemEpoch, ...], local_date: date) -> SystemEpoch:
    matches = [
        epoch for epoch in epochs
        if (epoch.start_local_date is None or local_date >= epoch.start_local_date)
        and (epoch.end_local_date_exclusive is None
             or local_date < epoch.end_local_date_exclusive)
    ]
    if len(matches) != 1:
        raise EpochConfigError(f"date {local_date} resolves to {len(matches)} epochs")
    return matches[0]


def seed_reference_data(
    connection, source_config: SourceConfig, epochs: tuple[SystemEpoch, ...]
) -> dict[str, int]:
    try:
        with connection.cursor() as cursor:
            for source in source_config.sources:
                cursor.execute(
                    """INSERT INTO energy_analytics.metric_sources
                       (canonical_name, item_name, source_config, enabled)
                       VALUES (%s, %s, %s, true)
                       ON CONFLICT (canonical_name) DO UPDATE SET
                         item_name = EXCLUDED.item_name,
                         source_config = EXCLUDED.source_config,
                         enabled = true,
                         updated_at = now()""",
                    (source.canonical_name, source.item_name, Json(asdict(source))),
                )
            for epoch in epochs:
                cursor.execute(
                    """INSERT INTO energy_analytics.system_epochs
                       (epoch_id, start_local_date, end_local_date_exclusive,
                        current_analytics, nominal_capacity_ah,
                        nominal_usable_kwh, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (epoch_id) DO UPDATE SET
                         start_local_date = EXCLUDED.start_local_date,
                         end_local_date_exclusive = EXCLUDED.end_local_date_exclusive,
                         current_analytics = EXCLUDED.current_analytics,
                         nominal_capacity_ah = EXCLUDED.nominal_capacity_ah,
                         nominal_usable_kwh = EXCLUDED.nominal_usable_kwh,
                         metadata = EXCLUDED.metadata""",
                    (epoch.epoch_id, epoch.start_local_date,
                     epoch.end_local_date_exclusive, epoch.current_analytics,
                     epoch.nominal_capacity_ah, epoch.nominal_usable_kwh,
                     Json(epoch.metadata)),
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {"metric_sources": len(source_config.sources), "system_epochs": len(epochs)}


def _upsert(cursor, table: str, columns: tuple[str, ...], values: tuple[object, ...]):
    assignments = ", ".join(
        f"{column} = EXCLUDED.{column}" for column in columns if column not in {"local_date", "epoch_id"}
    )
    cursor.execute(
        f"INSERT INTO energy_analytics.{table} ({', '.join(columns)}) "
        f"VALUES ({', '.join(['%s'] * len(columns))}) "
        f"ON CONFLICT (local_date, epoch_id) DO UPDATE SET {assignments}, computed_at = now()",
        values,
    )


def _recompute_battery_rollups(cursor, epoch_id: str) -> dict[date, float]:
    cursor.execute(
        "SELECT local_date, daily_efc, reached_99 "
        "FROM energy_analytics.daily_battery "
        "WHERE epoch_id = %s ORDER BY local_date",
        (epoch_id,),
    )
    rows = cursor.fetchall()
    cumulative = 0.0
    last_full = None
    previous_date = None
    previous_reached_full = False
    consecutive = 0
    by_date = {}
    for local_date, daily_efc, reached_99 in rows:
        cumulative = round(cumulative + float(daily_efc), 12)
        if reached_99:
            last_full = local_date
            days_since_99 = 0
            consecutive = 0
        else:
            days_since_99 = (
                (local_date - last_full).days if last_full is not None else None
            )
            if (
                previous_date is not None
                and local_date == previous_date + timedelta(days=1)
                and not previous_reached_full
            ):
                consecutive += 1
            else:
                consecutive = 1
        cursor.execute(
            """UPDATE energy_analytics.daily_battery
               SET cumulative_efc = %s, days_since_99 = %s,
                   consecutive_days_without_99 = %s
               WHERE epoch_id = %s AND local_date = %s""",
            (
                cumulative, days_since_99, consecutive, epoch_id, local_date,
            ),
        )
        by_date[local_date] = cumulative
        previous_date = local_date
        previous_reached_full = bool(reached_99)
    return by_date


def materialize_daily_snapshot(connection, snapshot: dict[str, object], epoch_id: str) -> dict[str, object]:
    if snapshot.get("status") != "ok" or snapshot.get("mode") != "read_only_dry_run":
        raise ValueError("only a successful read-only snapshot may be materialized")
    local_date = date.fromisoformat(str(snapshot["local_date"]))
    battery = snapshot["battery"]
    pv = snapshot["pv"]
    load = snapshot["load"]
    weather = snapshot["weather"]
    balance = snapshot["balance"]
    try:
        with connection.cursor() as cursor:
            battery_columns = (
                "local_date", "epoch_id", "min_soc_pct", "max_soc_pct",
                "mean_soc_pct", "sunrise_soc_pct", "sunset_soc_pct",
                "overnight_soc_drop_pct", "depth_of_discharge_pct",
                "hours_above_90", "hours_above_95", "hours_below_50",
                "hours_below_25", "charge_kwh", "discharge_kwh", "net_kwh",
                "daily_efc", "cumulative_efc", "min_temperature_c",
                "max_temperature_c", "mean_temperature_c", "reached_95",
                "reached_99", "reached_100", "first_reached_99_at",
                "days_since_99", "consecutive_days_without_99", "coverage", "quality",
            )
            _upsert(cursor, "daily_battery", battery_columns, (
                local_date, epoch_id,
                *(battery[key] for key in battery_columns[2:17]), 0.0,
                *(battery[key] for key in battery_columns[18:25]),
                None, 0, battery["coverage"], battery["quality"],
            ))
            cumulative_efc = _recompute_battery_rollups(cursor, epoch_id)[local_date]
            _upsert(cursor, "daily_pv", (
                "local_date", "epoch_id", "pv_kwh", "peak_w",
                "productive_hours", "first_productive_at", "last_productive_at",
                "before_solar_noon_kwh", "after_solar_noon_kwh",
                "mppt_output_kwh", "mppt_efficiency", "coverage", "quality"
            ), (
                local_date, epoch_id, pv["energy_kwh"], pv["peak_w"],
                pv["productive_hours"], pv["first_productive_at"],
                pv["last_productive_at"], pv["before_solar_noon_kwh"],
                pv["after_solar_noon_kwh"], pv["output_energy_kwh"],
                pv["mppt_efficiency"], pv["coverage"], pv["quality"],
            ))
            _upsert(cursor, "daily_load", (
                "local_date", "epoch_id", "load_kwh", "peak_w", "pv_load_ratio",
                "surplus_deficit_kwh", "active_loads", "coverage", "quality"
            ), (local_date, epoch_id, load["energy_kwh"], load["peak_w"],
                balance["pv_load_ratio"], balance["surplus_deficit_kwh"],
                Json(load["active_loads"]), load["coverage"], load["quality"]))
            _upsert(cursor, "daily_weather", (
                "local_date", "epoch_id", "min_temperature_c", "max_temperature_c",
                "mean_temperature_c", "irradiance_wh_m2", "peak_irradiance_w_m2",
                "precipitation_mm", "snow_state", "coverage", "quality"
            ), (local_date, epoch_id, weather["min_temperature_c"],
                weather["max_temperature_c"], weather["mean_temperature_c"],
                weather["irradiance_wh_m2"], weather["peak_irradiance_w_m2"],
                weather["precipitation_mm"], weather["snow_state"],
                weather["coverage"], weather["quality"]))
            for source in snapshot.get("source_quality", []):
                cursor.execute(
                    """INSERT INTO energy_analytics.daily_source_quality
                       (local_date, canonical_name, row_count, first_at, last_at,
                        coverage, stale_intervals, quality, detail)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (local_date, canonical_name) DO UPDATE SET
                         row_count = EXCLUDED.row_count,
                         first_at = EXCLUDED.first_at,
                         last_at = EXCLUDED.last_at,
                         coverage = EXCLUDED.coverage,
                         stale_intervals = EXCLUDED.stale_intervals,
                         quality = EXCLUDED.quality,
                         detail = EXCLUDED.detail""",
                    (
                        local_date, source["canonical_name"], source["row_count"],
                        source["first_at"], source["last_at"], source["coverage"],
                        source["stale_intervals"], source["quality"],
                        Json(source["detail"]),
                    ),
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {"local_date": local_date.isoformat(), "epoch_id": epoch_id,
            "tables_written": 5, "source_quality_rows": len(snapshot.get("source_quality", [])),
            "cumulative_efc": cumulative_efc}
