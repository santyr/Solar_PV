"""Portable, versioned future-model feature exports."""

from __future__ import annotations

import csv
from datetime import datetime
import io


class FeatureExportError(ValueError):
    pass


FIELDS = (
    "schema_version",
    "at",
    "epoch_id",
    "battery_soc_pct",
    "pv_power_w",
    "load_power_w",
    "forecast_issued_at",
    "forecast_valid_for",
    "shade_confidence",
    "kiva_confidence",
)


def _aware(value: datetime) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


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
        if not all(_aware(value) for value in (at, issued, valid)):
            raise FeatureExportError("feature timestamps must be timezone-aware")
        if at.minute % cadence_minutes or at.second or at.microsecond:
            raise FeatureExportError("row does not align to requested cadence")
        if issued > at:
            raise FeatureExportError("future forecast leakage")
        normalized.append(
            {
                "schema_version": 1,
                **{
                    field: row[field].isoformat()
                    if isinstance(row[field], datetime)
                    else row[field]
                    for field in FIELDS[1:]
                },
            }
        )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(normalized)
    return stream.getvalue().encode("utf-8")
