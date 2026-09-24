"""Optional daily north-wall quality from the shared atomic temperature receipts.

This path is deliberately opt-in. The numeric OpenHAB Item is retained only
for its row statistics; it cannot authorize freshness or fill receipt gaps.
"""

from __future__ import annotations

from datetime import datetime

from .quality import _coverage_quality


NORTH_WALL_SOURCE = "thermal.north_wall_temperature_c"
NORTH_WALL_ITEM = "AmbientWeatherWS2902A_WH31E_193_Temperature"


def read_north_wall_quality(
    db_config_path, policy_path, *, start: datetime, end: datetime, assessed_at: datetime,
    row_count: int, first_at: datetime | None, last_at: datetime | None,
) -> dict[str, object]:
    """Fail closed on missing access, identity drift, or incomplete receipts."""
    import psycopg2
    from hourly_temperature_runtime import read_db_config
    from weather_temperature_config import load_temperature_policies
    from weather_temperature_history import fetch_temperature_window

    policies = load_temperature_policies(str(policy_path))
    policy = policies.get("north_wall")
    if policy is None or policy.model != "AmbientWeather-WH31E" or policy.sensor_id != 193:
        raise ValueError("north-wall receipt policy identity mismatch")
    config = read_db_config(str(db_config_path))
    result = fetch_temperature_window(
        lambda: psycopg2.connect(**config, connect_timeout=3),
        start=start, end=end, assessed_at=assessed_at,
        stream="north_wall", policy=policy, include_provenance=True,
    )
    duration = (end - start).total_seconds()
    if (result["total_seconds"] != duration
            or not 0 <= result["covered_seconds"] <= duration
            or type(result["gap_count"]) is not int or result["gap_count"] < 0):
        raise ValueError("invalid north-wall receipt coverage")
    coverage = result["covered_seconds"] / duration
    return {
        "canonical_name": NORTH_WALL_SOURCE,
        "row_count": row_count,
        "first_at": first_at,
        "last_at": last_at,
        "coverage": coverage,
        "stale_intervals": result["gap_count"],
        "quality": _coverage_quality(coverage),
        "detail": {
            "policy": "atomic_temperature_evidence_v1",
            "freshness_basis": "Weather_Temperature_Evidence_JSON",
            "stream": "north_wall",
            "model": policy.model,
            "sensor_id": policy.sensor_id,
            "valid_seconds": result["covered_seconds"],
            "window_seconds": duration,
            "maximum_gap_seconds": result["maximum_gap_seconds"],
            "history_sha256": result["history_sha256"],
            "row_count_basis": "numeric_item_only",
        },
    }
