"""Compose a read-only daily analytics snapshot from resolved raw sources."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date

from .aggregation import aggregate_battery, aggregate_power, aggregate_weather
from .config import SourceConfig
from .reader import fetch_numeric_series
from .series import Point, fahrenheit_to_celsius, local_day_bounds


REQUIRED_DAILY = {
    "battery.soc_pct",
    "battery.dc_power_w",
    "battery.temperature_c",
    "pv.input_power_w",
    "house.ac_power_w",
    "weather.irradiance_w_m2",
    "weather.outdoor_temperature_c",
}


def _convert(points: list[Point], conversion: str | None) -> list[Point]:
    if conversion is None:
        return points
    if conversion == "fahrenheit_to_celsius":
        return [(at, fahrenheit_to_celsius(value)) for at, value in points]
    raise ValueError(f"unsupported numeric conversion: {conversion}")


def build_daily_snapshot(
    connection,
    config: SourceConfig,
    resolved_sources,
    local_date: date,
) -> dict[str, object]:
    tables = {
        source.canonical_name: source.table_name
        for source in resolved_sources
        if source.table_name is not None
    }
    missing = REQUIRED_DAILY - set(tables)
    if missing:
        raise ValueError(f"daily sources unresolved: {sorted(missing)}")
    definitions = {source.canonical_name: source for source in config.sources}
    start, end = local_day_bounds(local_date, config.timezone)
    max_gap = end - start

    def series(name: str) -> list[Point]:
        raw = fetch_numeric_series(connection, tables[name], start, end)
        return _convert(raw, definitions[name].conversion)

    battery = aggregate_battery(
        soc_points=series("battery.soc_pct"),
        power_points=series("battery.dc_power_w"),
        temperature_c_points=series("battery.temperature_c"),
        window_start=start,
        window_end=end,
        max_gap=max_gap,
        nominal_usable_kwh=20.48,
        power_sign=definitions["battery.dc_power_w"].sign,
    )
    pv = aggregate_power(
        series("pv.input_power_w"), start, end, max_gap=max_gap
    )
    load = aggregate_power(
        series("house.ac_power_w"), start, end, max_gap=max_gap
    )
    weather = aggregate_weather(
        temperature_c_points=series("weather.outdoor_temperature_c"),
        irradiance_points=series("weather.irradiance_w_m2"),
        window_start=start,
        window_end=end,
        max_gap=max_gap,
    )
    ratio = pv.energy_kwh / load.energy_kwh if load.energy_kwh > 0 else None
    return {
        "status": "ok",
        "mode": "read_only_dry_run",
        "local_date": local_date.isoformat(),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "battery": asdict(battery),
        "pv": asdict(pv),
        "load": asdict(load),
        "weather": asdict(weather),
        "balance": {
            "pv_load_ratio": ratio,
            "surplus_deficit_kwh": pv.energy_kwh - load.energy_kwh,
        },
    }
