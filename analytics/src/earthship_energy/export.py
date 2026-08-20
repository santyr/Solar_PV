"""Portable, versioned future-model feature exports."""

from __future__ import annotations

import csv
from datetime import datetime
import io
from math import isfinite


class FeatureExportError(ValueError):
    pass


FIELDS = (
    "schema_version",
    "at",
    "epoch_id",
    "battery_soc_pct",
    "battery_soc_pct_lag_1h",
    "pv_power_w",
    "pv_power_w_lag_1h",
    "load_power_w",
    "load_power_w_lag_1h",
    "outdoor_temperature_c",
    "outdoor_irradiance_w_m2",
    "daylight_observed",
    "dishwasher_active",
    "shurflo_pump_active",
    "forecast_temperature_f",
    "forecast_radiation_w_m2",
    "forecast_daily_pv_kwh",
    "forecast_issued_at",
    "forecast_valid_for",
    "daily_pv_forecast_issued_at",
    "daily_pv_forecast_valid_for",
    "forecast_status",
    "shade_confidence",
    "kiva_confidence",
)


def _aware(value: datetime) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _csv_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float):
        if not isfinite(value):
            raise FeatureExportError("feature numbers must be finite")
        return round(value, 6)
    return value


def export_feature_csv(rows, *, cadence_minutes: int = 15) -> bytes:
    if cadence_minutes not in {5, 15}:
        raise FeatureExportError("cadence must be 5 or 15 minutes")
    normalized = []
    for row in sorted(rows, key=lambda item: item["at"]):
        missing = set(FIELDS[2:]) - set(row)
        if missing:
            raise FeatureExportError(f"missing feature fields: {sorted(missing)}")
        at = row["at"]
        issued = row["forecast_issued_at"]
        valid = row["forecast_valid_for"]
        daily_issued = row["daily_pv_forecast_issued_at"]
        daily_valid = row["daily_pv_forecast_valid_for"]
        if not _aware(at):
            raise FeatureExportError("feature timestamps must be timezone-aware")
        if at.minute % cadence_minutes or at.second or at.microsecond:
            raise FeatureExportError("row does not align to requested cadence")
        status = row["forecast_status"]
        if status not in {"current", "stale", "unavailable"}:
            raise FeatureExportError("invalid forecast status")
        if status == "unavailable":
            if issued is not None or valid is not None:
                raise FeatureExportError("unavailable forecast must omit timestamps")
        elif not _aware(issued) or not _aware(valid):
            raise FeatureExportError("available forecast timestamps must be timezone-aware")
        if issued is not None and issued > at:
            raise FeatureExportError("future forecast leakage")
        if row["forecast_daily_pv_kwh"] is None:
            if daily_issued is not None or daily_valid is not None:
                raise FeatureExportError("missing daily PV forecast must omit timestamps")
        elif not _aware(daily_issued) or not _aware(daily_valid):
            raise FeatureExportError("daily PV forecast timestamps must be timezone-aware")
        if daily_issued is not None and daily_issued > at:
            raise FeatureExportError("future forecast leakage")
        normalized.append(
            {
                "schema_version": 2,
                **{
                    field: _csv_value(row[field])
                    for field in FIELDS[1:]
                },
            }
        )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(normalized)
    return stream.getvalue().encode("utf-8")
