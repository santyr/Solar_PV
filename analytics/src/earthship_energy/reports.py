"""Reproducible report bodies with run metadata kept outside content."""

from __future__ import annotations

from dataclasses import asdict

from .simulation import Scenario, replay_energy_balance


SCHEMA_VERSION = 1


def _ordered(daily_rows):
    rows = sorted(daily_rows, key=lambda row: row["local_date"])
    if not rows:
        raise ValueError("report requires at least one daily row")
    return rows


def monthly_report(daily_rows, *, epoch_id: str) -> dict[str, object]:
    rows = _ordered(daily_rows)
    return {
        "report": "monthly",
        "schema_version": SCHEMA_VERSION,
        "epoch_id": epoch_id,
        "window": {
            "start": rows[0]["local_date"].isoformat(),
            "end": rows[-1]["local_date"].isoformat(),
            "days": len(rows),
        },
        "metrics": {
            "pv_kwh": sum(float(row["pv_kwh"]) for row in rows),
            "load_kwh": sum(float(row["load_kwh"]) for row in rows),
            "minimum_soc_pct": min(float(row["min_soc_pct"]) for row in rows),
            "days_reaching_99": sum(bool(row["reached_99"]) for row in rows),
            "quality_days": sum(row.get("quality") == "ok" for row in rows),
        },
    }


def lifecycle_report(daily_rows) -> dict[str, object]:
    rows = _ordered(daily_rows)
    return {
        "report": "lifecycle",
        "schema_version": SCHEMA_VERSION,
        "window_start": rows[0]["local_date"].isoformat(),
        "window_end": rows[-1]["local_date"].isoformat(),
        "charge_kwh": sum(float(row["charge_kwh"]) for row in rows),
        "discharge_kwh": sum(float(row["discharge_kwh"]) for row in rows),
        "cumulative_efc": sum(float(row["daily_efc"]) for row in rows),
    }


def winter_report(
    daily_rows,
    *,
    nominal_usable_kwh: float,
    reserve_soc_pct: float,
    inverter_efficiency: float = 0.92,
) -> dict[str, object]:
    rows = _ordered(daily_rows)
    winter_months = {11, 12, 1, 2, 3}
    winter_days = sum(row["local_date"].month in winter_months for row in rows)
    scenarios = {}
    for capacity_pct in (100, 90, 80, 70, 60):
        result = replay_energy_balance(
            rows,
            Scenario(
                usable_battery_kwh=nominal_usable_kwh * capacity_pct / 100.0,
                reserve_soc_pct=reserve_soc_pct,
                pv_multiplier=1.0,
                load_multiplier=1.0,
                inverter_efficiency=inverter_efficiency,
            ),
        )
        scenarios[str(capacity_pct)] = asdict(result)
    return {
        "report": "winter_sufficiency",
        "schema_version": SCHEMA_VERSION,
        "question": "Are four Discover modules still sufficient?",
        "winter_observation_days": winter_days,
        "conclusion": (
            "scenario_results_available"
            if winter_days
            else "insufficient_winter_observations"
        ),
        "window_start": rows[0]["local_date"].isoformat(),
        "window_end": rows[-1]["local_date"].isoformat(),
        "reserve_soc_pct": reserve_soc_pct,
        "capacity_scenarios_pct": scenarios,
    }
