"""Idempotent parsing for operator-exported LYNK ACCESS module CSV data."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io


class ImportError(ValueError):
    pass


REQUIRED_COLUMNS = {
    "module_id",
    "sampled_at",
    "soc_pct",
    "voltage_v",
    "current_a",
    "temperature_c",
    "cell_spread_mv",
    "charge_kwh",
    "discharge_kwh",
    "faults",
}


@dataclass(frozen=True)
class ModuleSample:
    module_id: str
    sampled_at: datetime
    soc_pct: float | None
    voltage_v: float | None
    current_a: float | None
    temperature_c: float | None
    cell_spread_mv: float | None
    charge_kwh: float | None
    discharge_kwh: float | None
    faults: tuple[str, ...]


@dataclass(frozen=True)
class LynkImportBatch:
    sha256: str
    source_name: str
    status: str
    rows: tuple[ModuleSample, ...]


def _number(value: str, field_name: str) -> float | None:
    if value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ImportError(f"invalid {field_name}") from exc


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ImportError("invalid sampled_at") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ImportError("sampled_at must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def prepare_lynk_import(
    content: bytes, source_name: str, existing_hashes: set[str]
) -> LynkImportBatch:
    sha256 = hashlib.sha256(content).hexdigest()
    if sha256 in existing_hashes:
        return LynkImportBatch(sha256, source_name, "duplicate", ())
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportError("LYNK CSV must be UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text))
    columns = set(reader.fieldnames or ())
    if REQUIRED_COLUMNS - columns:
        raise ImportError(f"missing required columns: {sorted(REQUIRED_COLUMNS - columns)}")
    rows = []
    keys = set()
    for line_number, raw in enumerate(reader, start=2):
        module_id = (raw.get("module_id") or "").strip()
        if not module_id:
            raise ImportError(f"line {line_number}: module_id is required")
        sampled_at = _timestamp(raw["sampled_at"])
        key = (module_id, sampled_at)
        if key in keys:
            raise ImportError(f"duplicate sample at line {line_number}")
        keys.add(key)
        faults = tuple(
            part.strip() for part in raw["faults"].split(";") if part.strip()
        )
        rows.append(
            ModuleSample(
                module_id=module_id,
                sampled_at=sampled_at,
                soc_pct=_number(raw["soc_pct"], "soc_pct"),
                voltage_v=_number(raw["voltage_v"], "voltage_v"),
                current_a=_number(raw["current_a"], "current_a"),
                temperature_c=_number(raw["temperature_c"], "temperature_c"),
                cell_spread_mv=_number(raw["cell_spread_mv"], "cell_spread_mv"),
                charge_kwh=_number(raw["charge_kwh"], "charge_kwh"),
                discharge_kwh=_number(raw["discharge_kwh"], "discharge_kwh"),
                faults=faults,
            )
        )
    if not rows:
        raise ImportError("LYNK CSV contains no samples")
    return LynkImportBatch(sha256, source_name, "ready", tuple(rows))
