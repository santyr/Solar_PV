"""Closed, deterministic payload for the observational Energy console."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SCHEMA = "earthship-energy-ui/v1"
MAX_PAYLOAD_BYTES = 16 * 1024
TOP_LEVEL_FIELDS = {
    "schema", "generatedAt", "timezone", "epochId", "throughDate", "status",
    "battery", "energy", "winter", "lifecycle", "forecast", "health",
}
BATTERY_FIELDS = {
    "status", "latestMinSocPct", "latestReached99", "endingCumulativeEfc",
    "currentNoFullDays", "daysSinceFull",
}
ENERGY_FIELDS = {
    "status", "latest", "activeLoads", "observedCurtailmentKwh",
    "observedCurtailmentStatus",
}
LATEST_ENERGY_FIELDS = {"date", "pvKwh", "loadKwh", "chargeKwh", "dischargeKwh"}
ACTIVE_LOAD_FIELDS = {"status", "measurement", "reason"}
WINTER_FIELDS = {
    "status", "observationDays", "lowestSocPct", "medianMinSocPct",
    "longestNoFullDays", "worstDeficitPeriod",
}
DEFICIT_FIELDS = {
    "start", "end", "days", "deficitKwh", "pvKwh", "loadKwh",
    "timeToReach99Days",
}
LIFECYCLE_FIELDS = {
    "status", "chargeKwh", "dischargeKwh", "periodEfc",
    "endingCumulativeEfc", "highSocHoursAbove90", "highSocHoursAbove95",
    "stateOfHealthPct", "moduleHealth",
}
MODULE_FIELDS = {
    "status", "reason", "moduleCount", "latestCurrentSharingRangeA",
    "maximumCellSpreadMv",
}
FORECAST_FIELDS = {
    "status", "issuedAt", "validFor", "pv24hKwh", "nextMorningSocPct",
    "fullToday", "fullTomorrow", "reason",
}
HEALTH_FIELDS = {
    "status", "analytics", "forecast", "bms", "schneider", "weather",
    "collector", "publisher", "reasons",
}
STATUSES = {"ok", "degraded", "unavailable", "stale", "fault"}
FORECAST_STATUSES = {"current", "stale", "unavailable", "degraded"}


def _aware(value: str, path: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must be an aware ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{path} must be an aware ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{path} must be an aware ISO-8601 timestamp")
    return parsed


def _date(value: object, path: str) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{path} must use YYYY-MM-DD or null")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{path} must use YYYY-MM-DD or null") from exc


def _exact(value: object, fields: set[str], path: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{path} has missing or unknown fields")
    return value


def _number(value: object, path: str, *, optional: bool = True) -> float | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{path} must be a finite number")
    return result


def _integer(value: object, path: str, *, optional: bool = True) -> int | None:
    if value is None and optional:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"{path} must be a nonnegative integer")
    return value


def _boolean(value: object, path: str, *, optional: bool = True) -> bool | None:
    if value is None and optional:
        return None
    if type(value) is not bool:
        raise ValueError(f"{path} must be a boolean or null")
    return value


def _status(value: object, path: str) -> str:
    if value not in STATUSES:
        raise ValueError(f"{path} status is outside the closed vocabulary")
    return str(value)


def _ordered_rows(rows) -> list[dict[str, object]]:
    approved = [row for row in rows if row.get("quality") == "ok"]
    ordered = sorted(approved, key=lambda row: row["local_date"])
    if any(type(row.get("local_date")) is not date for row in ordered):
        raise ValueError("daily local_date must be a date")
    if len({row["local_date"] for row in ordered}) != len(ordered):
        raise ValueError("daily dates must be unique")
    return ordered


def _no_full_evidence(rows: list[dict[str, object]]) -> tuple[int, int | None]:
    if not rows:
        return 0, None
    current = 0
    expected = rows[-1]["local_date"]
    for row in reversed(rows):
        if row["local_date"] != expected or bool(row["reached_99"]):
            break
        current += 1
        expected -= timedelta(days=1)
    last_full = next(
        (row["local_date"] for row in reversed(rows) if bool(row["reached_99"])),
        None,
    )
    days_since = (rows[-1]["local_date"] - last_full).days if last_full else None
    return current, days_since


def _winter_section(report: dict[str, object] | None) -> dict[str, object]:
    observed = report.get("observed") if report else None
    if not report or not observed:
        return {
            "status": "unavailable",
            "observationDays": int(report.get("winter_observation_days", 0)) if report else 0,
            "lowestSocPct": None,
            "medianMinSocPct": None,
            "longestNoFullDays": None,
            "worstDeficitPeriod": None,
        }
    deficit = observed.get("worst_deficit_period")
    normalized_deficit = None if deficit is None else {
        "start": deficit.get("start"),
        "end": deficit.get("end"),
        "days": deficit.get("days"),
        "deficitKwh": deficit.get("deficit_kwh"),
        "pvKwh": deficit.get("pv_kwh"),
        "loadKwh": deficit.get("load_kwh"),
        "timeToReach99Days": deficit.get("time_to_reach_99_days"),
    }
    return {
        "status": "ok",
        "observationDays": int(report["winter_observation_days"]),
        "lowestSocPct": observed.get("lowest_soc_pct"),
        "medianMinSocPct": observed.get("median_min_soc_pct"),
        "longestNoFullDays": observed.get("longest_no_full_sequence_days"),
        "worstDeficitPeriod": normalized_deficit,
    }


def _module_section(report: dict[str, object] | None) -> dict[str, object]:
    if not report or report.get("status") != "ok":
        return {
            "status": "unavailable",
            "reason": (report or {}).get("reason", "no_module_samples"),
            "moduleCount": None,
            "latestCurrentSharingRangeA": None,
            "maximumCellSpreadMv": None,
        }
    summary = report.get("summary", {})
    return {
        "status": "ok",
        "reason": None,
        "moduleCount": summary.get("module_count"),
        "latestCurrentSharingRangeA": summary.get("latest_current_sharing_range_a"),
        "maximumCellSpreadMv": summary.get("maximum_cell_spread_mv"),
    }


def build_energy_ui_payload(
    *,
    generated_at: datetime,
    timezone_name: str,
    epoch_id: str,
    daily_rows,
    winter: dict[str, object] | None,
    lifecycle: dict[str, object] | None,
    module_health: dict[str, object] | None,
    forecast: dict[str, object] | None,
    health: dict[str, object] | None,
) -> dict[str, object]:
    """Build a compact state payload without inventing missing evidence."""
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("timezone is invalid") from exc
    if not isinstance(epoch_id, str) or not epoch_id:
        raise ValueError("epoch_id is required")
    rows = _ordered_rows(daily_rows)
    latest = rows[-1] if rows else None
    current_no_full, days_since_full = _no_full_evidence(rows)

    battery = {
        "status": "ok" if latest else "unavailable",
        "latestMinSocPct": latest.get("min_soc_pct") if latest else None,
        "latestReached99": bool(latest["reached_99"]) if latest else None,
        "endingCumulativeEfc": latest.get("cumulative_efc") if latest else None,
        "currentNoFullDays": current_no_full if latest else None,
        "daysSinceFull": days_since_full,
    }
    energy_latest = None if latest is None else {
        "date": latest["local_date"].isoformat(),
        "pvKwh": latest.get("pv_kwh"),
        "loadKwh": latest.get("load_kwh"),
        "chargeKwh": latest.get("charge_kwh"),
        "dischargeKwh": latest.get("discharge_kwh"),
    }
    energy = {
        "status": "ok" if latest else "unavailable",
        "latest": energy_latest,
        "activeLoads": {
            "status": "unavailable",
            "measurement": "state_only",
            "reason": "no_power_meter_contract",
        },
        "observedCurtailmentKwh": None,
        "observedCurtailmentStatus": "unavailable",
    }
    lifecycle_section = {
        "status": "ok" if lifecycle else "unavailable",
        "chargeKwh": lifecycle.get("charge_kwh") if lifecycle else None,
        "dischargeKwh": lifecycle.get("discharge_kwh") if lifecycle else None,
        "periodEfc": lifecycle.get("cumulative_efc") if lifecycle else None,
        "endingCumulativeEfc": lifecycle.get("ending_cumulative_efc") if lifecycle else None,
        "highSocHoursAbove90": (
            lifecycle.get("high_soc_exposure_hours", {}).get("above_90")
            if lifecycle else None
        ),
        "highSocHoursAbove95": (
            lifecycle.get("high_soc_exposure_hours", {}).get("above_95")
            if lifecycle else None
        ),
        "stateOfHealthPct": None,
        "moduleHealth": _module_section(module_health),
    }
    forecast_section = {
        "status": (forecast or {}).get("status", "unavailable"),
        "issuedAt": (forecast or {}).get("issuedAt"),
        "validFor": (forecast or {}).get("validFor"),
        "pv24hKwh": (forecast or {}).get("pv24hKwh"),
        "nextMorningSocPct": None,
        "fullToday": None,
        "fullTomorrow": None,
        "reason": (forecast or {}).get("reason", "forecast_evidence_unavailable"),
    }
    supplied_health = health or {}
    health_values = {
        name: supplied_health.get(name, "unavailable")
        for name in ("analytics", "forecast", "bms", "schneider", "weather", "collector", "publisher")
    }
    health_status = "ok" if all(value == "ok" for value in health_values.values()) else "degraded"
    health_section = {
        "status": health_status,
        **health_values,
        "reasons": list(supplied_health.get("reasons", [])),
    }
    sections = [battery, energy, _winter_section(winter), lifecycle_section, forecast_section]
    overall = (
        "unavailable" if latest is None
        else "ok" if all(section["status"] == "ok" for section in sections)
        and health_status == "ok"
        else "degraded"
    )
    result = {
        "schema": SCHEMA,
        "generatedAt": generated_at.isoformat(),
        "timezone": timezone_name,
        "epochId": epoch_id,
        "throughDate": latest["local_date"].isoformat() if latest else None,
        "status": overall,
        "battery": battery,
        "energy": energy,
        "winter": sections[2],
        "lifecycle": lifecycle_section,
        "forecast": forecast_section,
        "health": health_section,
    }
    return validate_energy_ui_payload(result, now=generated_at)


def validate_energy_ui_payload(
    payload: object, *, now: datetime | None = None
) -> dict[str, object]:
    result = _exact(payload, TOP_LEVEL_FIELDS, "payload")
    if result["schema"] != SCHEMA:
        raise ValueError("energy UI schema must be earthship-energy-ui/v1")
    generated = _aware(result["generatedAt"], "generatedAt")
    if now is not None:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("validation time must be timezone-aware")
        if generated > now:
            raise ValueError("generatedAt cannot be in the future")
    try:
        ZoneInfo(result["timezone"])
    except (TypeError, ZoneInfoNotFoundError) as exc:
        raise ValueError("timezone is invalid") from exc
    if not isinstance(result["epochId"], str) or not result["epochId"]:
        raise ValueError("epochId is required")
    through = _date(result["throughDate"], "throughDate")
    if through and through > generated.astimezone(ZoneInfo(result["timezone"])).date():
        raise ValueError("throughDate cannot follow generatedAt")
    _status(result["status"], "payload")

    battery = _exact(result["battery"], BATTERY_FIELDS, "battery")
    _status(battery["status"], "battery")
    for field in ("latestMinSocPct", "endingCumulativeEfc"):
        _number(battery[field], f"battery.{field}")
    _boolean(battery["latestReached99"], "battery.latestReached99")
    _integer(battery["currentNoFullDays"], "battery.currentNoFullDays")
    _integer(battery["daysSinceFull"], "battery.daysSinceFull")

    energy = _exact(result["energy"], ENERGY_FIELDS, "energy")
    _status(energy["status"], "energy")
    if energy["latest"] is not None:
        latest = _exact(energy["latest"], LATEST_ENERGY_FIELDS, "energy.latest")
        latest_date = _date(latest["date"], "energy.latest.date")
        if through and latest_date != through:
            raise ValueError("energy latest date must equal throughDate")
        for field in ("pvKwh", "loadKwh", "chargeKwh", "dischargeKwh"):
            _number(latest[field], f"energy.latest.{field}", optional=False)
    active = _exact(energy["activeLoads"], ACTIVE_LOAD_FIELDS, "energy.activeLoads")
    _status(active["status"], "energy.activeLoads")
    if active["measurement"] != "state_only" or not isinstance(active["reason"], str):
        raise ValueError("active loads must retain the state_only contract")
    _number(energy["observedCurtailmentKwh"], "energy.observedCurtailmentKwh")
    _status(energy["observedCurtailmentStatus"], "energy.observedCurtailment")

    winter = _exact(result["winter"], WINTER_FIELDS, "winter")
    _status(winter["status"], "winter")
    _integer(winter["observationDays"], "winter.observationDays", optional=False)
    for field in ("lowestSocPct", "medianMinSocPct"):
        _number(winter[field], f"winter.{field}")
    _integer(winter["longestNoFullDays"], "winter.longestNoFullDays")
    if winter["worstDeficitPeriod"] is not None:
        deficit = _exact(winter["worstDeficitPeriod"], DEFICIT_FIELDS, "winter.worstDeficitPeriod")
        _date(deficit["start"], "winter.worstDeficitPeriod.start")
        _date(deficit["end"], "winter.worstDeficitPeriod.end")
        _integer(deficit["days"], "winter.worstDeficitPeriod.days", optional=False)
        for field in ("deficitKwh", "pvKwh", "loadKwh"):
            _number(deficit[field], f"winter.worstDeficitPeriod.{field}", optional=False)
        _integer(deficit["timeToReach99Days"], "winter.worstDeficitPeriod.timeToReach99Days")

    lifecycle = _exact(result["lifecycle"], LIFECYCLE_FIELDS, "lifecycle")
    _status(lifecycle["status"], "lifecycle")
    for field in LIFECYCLE_FIELDS - {"status", "moduleHealth"}:
        _number(lifecycle[field], f"lifecycle.{field}")
    module = _exact(lifecycle["moduleHealth"], MODULE_FIELDS, "lifecycle.moduleHealth")
    _status(module["status"], "lifecycle.moduleHealth")
    if module["reason"] is not None and not isinstance(module["reason"], str):
        raise ValueError("module health reason must be a string or null")
    _integer(module["moduleCount"], "lifecycle.moduleHealth.moduleCount")
    _number(module["latestCurrentSharingRangeA"], "lifecycle.moduleHealth.latestCurrentSharingRangeA")
    _number(module["maximumCellSpreadMv"], "lifecycle.moduleHealth.maximumCellSpreadMv")

    forecast = _exact(result["forecast"], FORECAST_FIELDS, "forecast")
    if forecast["status"] not in FORECAST_STATUSES:
        raise ValueError("forecast status is outside the closed vocabulary")
    issued = _aware(forecast["issuedAt"], "forecast.issuedAt") if forecast["issuedAt"] is not None else None
    valid_for = _aware(forecast["validFor"], "forecast.validFor") if forecast["validFor"] is not None else None
    if issued is not None and issued > generated:
        raise ValueError("forecast.issuedAt cannot follow generatedAt")
    if issued is not None and valid_for is not None and valid_for < issued:
        raise ValueError("forecast.validFor cannot precede issuedAt")
    for field in ("pv24hKwh", "nextMorningSocPct"):
        _number(forecast[field], f"forecast.{field}")
    for field in ("fullToday", "fullTomorrow"):
        _boolean(forecast[field], f"forecast.{field}")
    if forecast["reason"] is not None and not isinstance(forecast["reason"], str):
        raise ValueError("forecast.reason must be a string or null")

    health = _exact(result["health"], HEALTH_FIELDS, "health")
    for field in HEALTH_FIELDS - {"reasons"}:
        _status(health[field], f"health.{field}")
    if (
        not isinstance(health["reasons"], list)
        or len(health["reasons"]) > 16
        or any(not isinstance(reason, str) or len(reason.encode()) > 256 for reason in health["reasons"])
    ):
        raise ValueError("health.reasons must be at most 16 bounded strings")
    return result


def encode_energy_ui_payload(payload: object) -> bytes:
    validated = validate_energy_ui_payload(payload)
    encoded = json.dumps(
        validated, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if len(encoded) >= MAX_PAYLOAD_BYTES:
        raise ValueError("energy UI payload must be below 16 KiB")
    return encoded
