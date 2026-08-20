"""Reproducible report bodies with run metadata kept outside content."""

from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from statistics import median

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
    minimum_temperatures = [
        float(row["min_temperature_c"])
        for row in rows if row.get("min_temperature_c") is not None
    ]
    maximum_temperatures = [
        float(row["max_temperature_c"])
        for row in rows if row.get("max_temperature_c") is not None
    ]
    return {
        "report": "lifecycle",
        "schema_version": SCHEMA_VERSION,
        "window_start": rows[0]["local_date"].isoformat(),
        "window_end": rows[-1]["local_date"].isoformat(),
        "charge_kwh": sum(float(row["charge_kwh"]) for row in rows),
        "discharge_kwh": sum(float(row["discharge_kwh"]) for row in rows),
        "cumulative_efc": sum(float(row["daily_efc"]) for row in rows),
        "ending_cumulative_efc": (
            float(rows[-1]["cumulative_efc"])
            if rows[-1].get("cumulative_efc") is not None else None
        ),
        "high_soc_exposure_hours": {
            "above_90": sum(float(row.get("hours_above_90") or 0) for row in rows),
            "above_95": sum(float(row.get("hours_above_95") or 0) for row in rows),
        },
        "temperature_exposure_c": {
            "minimum": min(minimum_temperatures, default=None),
            "maximum": max(maximum_temperatures, default=None),
        },
        "module_health": {
            "status": "unavailable",
            "reason": "no_module_samples",
        },
    }


def _counter_delta(rows, field: str) -> float | None:
    values = [float(row[field]) for row in rows if row.get(field) is not None]
    if len(values) < 2:
        return None
    return round(max(0.0, values[-1] - values[0]), 12)


def module_health_report(sample_rows) -> dict[str, object]:
    rows = sorted(sample_rows, key=lambda row: (row["sampled_at"], row["module_id"]))
    if not rows:
        return {
            "report": "module_health",
            "schema_version": SCHEMA_VERSION,
            "status": "unavailable",
            "reason": "no_module_samples",
            "modules": {},
            "provenance": [],
        }
    by_module = {}
    for row in rows:
        by_module.setdefault(str(row["module_id"]), []).append(row)
    latest_rows = {module: values[-1] for module, values in by_module.items()}
    latest_currents = [
        float(row["current_a"]) for row in latest_rows.values()
        if row.get("current_a") is not None
    ]
    mean_current = (
        sum(latest_currents) / len(latest_currents) if latest_currents else None
    )
    modules = {}
    for module, values in sorted(by_module.items()):
        latest = values[-1]
        spreads = [
            float(row["cell_spread_mv"]) for row in values
            if row.get("cell_spread_mv") is not None
        ]
        temperatures = [
            float(row["temperature_c"]) for row in values
            if row.get("temperature_c") is not None
        ]
        faults = sorted({
            str(fault)
            for row in values
            for fault in (row.get("faults") or [])
        })
        latest_current = (
            float(latest["current_a"]) if latest.get("current_a") is not None else None
        )
        modules[module] = {
            "sample_count": len(values),
            "latest_at": latest["sampled_at"].isoformat(),
            "latest_soc_pct": latest.get("soc_pct"),
            "latest_voltage_v": latest.get("voltage_v"),
            "latest_current_a": latest_current,
            "latest_current_deviation_a": (
                latest_current - mean_current
                if latest_current is not None and mean_current is not None else None
            ),
            "latest_temperature_c": latest.get("temperature_c"),
            "latest_cell_spread_mv": latest.get("cell_spread_mv"),
            "maximum_cell_spread_mv": max(spreads, default=None),
            "temperature_range_c": {
                "minimum": min(temperatures, default=None),
                "maximum": max(temperatures, default=None),
            },
            "charge_throughput_delta_kwh": _counter_delta(values, "charge_kwh"),
            "discharge_throughput_delta_kwh": _counter_delta(values, "discharge_kwh"),
            "faults_observed": faults,
        }
    provenance = sorted(
        {
            (int(row["batch_id"]), str(row["source_name"]), str(row["sha256"]))
            for row in rows
        }
    )
    all_spreads = [
        float(row["cell_spread_mv"]) for row in rows
        if row.get("cell_spread_mv") is not None
    ]
    return {
        "report": "module_health",
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "window": {
            "start": rows[0]["sampled_at"].isoformat(),
            "end": rows[-1]["sampled_at"].isoformat(),
            "samples": len(rows),
        },
        "summary": {
            "module_count": len(modules),
            "latest_current_sharing_range_a": (
                max(latest_currents) - min(latest_currents)
                if latest_currents else None
            ),
            "maximum_cell_spread_mv": max(all_spreads, default=None),
        },
        "modules": modules,
        "provenance": [
            {"batch_id": batch_id, "source_name": source, "sha256": sha256}
            for batch_id, source, sha256 in provenance
        ],
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires data")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _longest_no_full_sequence(rows) -> int:
    longest = current = 0
    previous_date = None
    for row in rows:
        local_date = row["local_date"]
        if previous_date is not None and local_date != previous_date + timedelta(days=1):
            current = 0
        current = 0 if row["reached_99"] else current + 1
        longest = max(longest, current)
        previous_date = local_date
    return longest


def _worst_deficit_period(rows) -> dict[str, object] | None:
    runs = []
    current = []
    previous_date = None
    for row in rows:
        deficit = max(0.0, float(row["load_kwh"]) - float(row["pv_kwh"]))
        contiguous = (
            previous_date is None or row["local_date"] == previous_date + timedelta(days=1)
        )
        if deficit > 0:
            if not contiguous:
                if current:
                    runs.append(current)
                current = []
            current.append(row)
        elif current:
            runs.append(current)
            current = []
        previous_date = row["local_date"]
    if current:
        runs.append(current)
    if not runs:
        return None
    worst = max(
        runs,
        key=lambda run: (
            sum(float(row["load_kwh"]) - float(row["pv_kwh"]) for row in run),
            len(run),
        ),
    )
    end_index = rows.index(worst[-1])
    recovery = next(
        (
            (row["local_date"] - worst[-1]["local_date"]).days
            for row in rows[end_index + 1:]
            if row["reached_99"]
        ),
        None,
    )
    return {
        "start": worst[0]["local_date"].isoformat(),
        "end": worst[-1]["local_date"].isoformat(),
        "days": len(worst),
        "deficit_kwh": sum(
            float(row["load_kwh"]) - float(row["pv_kwh"]) for row in worst
        ),
        "pv_kwh": sum(float(row["pv_kwh"]) for row in worst),
        "load_kwh": sum(float(row["load_kwh"]) for row in worst),
        "time_to_reach_99_days": recovery,
    }


def _scenario_payload(rows, scenario: Scenario) -> dict[str, object]:
    return asdict(replay_energy_balance(rows, scenario))


def winter_report(
    daily_rows,
    *,
    nominal_usable_kwh: float,
    reserve_soc_pct: float,
    inverter_efficiency: float = 0.92,
) -> dict[str, object]:
    rows = _ordered(daily_rows)
    winter_months = {11, 12, 1, 2, 3}
    winter_rows = [row for row in rows if row["local_date"].month in winter_months]
    winter_days = len(winter_rows)
    scenarios = {}
    tradeoffs = {}
    if winter_rows:
        for capacity_pct in (100, 90, 80, 70, 60):
            scenario = Scenario(
                usable_battery_kwh=nominal_usable_kwh * capacity_pct / 100.0,
                reserve_soc_pct=reserve_soc_pct,
                pv_multiplier=1.0,
                load_multiplier=1.0,
                inverter_efficiency=inverter_efficiency,
            )
            scenarios[str(capacity_pct)] = _scenario_payload(winter_rows, scenario)
        for pv_pct in (100, 125, 150):
            for storage_pct in (100, 80, 60):
                key = f"pv_{pv_pct}pct_storage_{storage_pct}pct"
                tradeoffs[key] = _scenario_payload(
                    winter_rows,
                    Scenario(
                        usable_battery_kwh=nominal_usable_kwh * storage_pct / 100.0,
                        reserve_soc_pct=reserve_soc_pct,
                        pv_multiplier=pv_pct / 100.0,
                        load_multiplier=1.0,
                        inverter_efficiency=inverter_efficiency,
                    ),
                )
    observed = None
    if winter_rows:
        minima = [float(row["min_soc_pct"]) for row in winter_rows]
        observed = {
            "lowest_soc_pct": min(minima),
            "median_min_soc_pct": median(minima),
            "p05_min_soc_pct": _percentile(minima, 0.05),
            "days_below_soc_pct": {
                str(threshold): sum(value < threshold for value in minima)
                for threshold in (75, 60, 50, 40, 25)
            },
            "longest_no_full_sequence_days": _longest_no_full_sequence(winter_rows),
            "worst_deficit_period": _worst_deficit_period(winter_rows),
        }
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
        "observed": observed,
        "capacity_scenarios_pct": scenarios,
        "pv_storage_tradeoff": tradeoffs,
    }
