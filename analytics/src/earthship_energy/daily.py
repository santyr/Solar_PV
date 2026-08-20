"""Compose a read-only daily analytics snapshot from resolved raw sources."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta

from .aggregation import (
    aggregate_battery,
    aggregate_power,
    aggregate_weather,
    value_at,
)
from .config import SourceConfig
from .events import fetch_snow_state_as_of
from .reader import (
    datetime_state_for_local_date,
    fetch_numeric_series,
    fetch_text_series,
    state_duration_seconds,
)
from .series import (
    Point,
    fahrenheit_to_celsius,
    integrate_trapezoid,
    local_day_bounds,
)


REQUIRED_DAILY = {
    "battery.soc_pct",
    "battery.dc_power_w",
    "battery.temperature_c",
    "pv.input_power_w",
    "pv.output_power_w",
    "house.ac_power_w",
    "weather.irradiance_w_m2",
    "weather.outdoor_temperature_c",
}


def _convert(points: list[Point], conversion: str | None) -> list[Point]:
    if conversion is None:
        return points
    if conversion == "fahrenheit_to_celsius":
        return [(at, fahrenheit_to_celsius(value)) for at, value in points]
    if conversion == "inches_to_millimeters":
        return [(at, float(value) * 25.4) for at, value in points]
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

    series_cache: dict[str, list[Point]] = {}

    def series(name: str) -> list[Point]:
        if name in series_cache:
            return series_cache[name]
        raw = fetch_numeric_series(connection, tables[name], start, end)
        series_cache[name] = _convert(raw, definitions[name].conversion)
        return series_cache[name]

    def optional_series(name: str) -> list[Point]:
        return series(name) if name in tables else []

    def event_time(name: str, day: date, window_start, window_end):
        if name not in tables:
            return None
        return datetime_state_for_local_date(
            fetch_text_series(connection, tables[name], window_start, window_end),
            day,
            config.timezone,
        )

    sunrise = event_time("solar.sunrise_at", local_date, start, end)
    sunset = event_time("solar.sunset_at", local_date, start, end)
    battery_soc = series("battery.soc_pct")

    battery = aggregate_battery(
        soc_points=battery_soc,
        power_points=series("battery.dc_power_w"),
        temperature_c_points=series("battery.temperature_c"),
        window_start=start,
        window_end=end,
        max_gap=max_gap,
        nominal_usable_kwh=20.48,
        power_sign=definitions["battery.dc_power_w"].sign,
        sunrise=sunrise,
        sunset=sunset,
    )
    pv = aggregate_power(
        series("pv.input_power_w"), start, end, max_gap=max_gap
    )
    pv_output = aggregate_power(
        series("pv.output_power_w"), start, end, max_gap=max_gap
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
        precipitation_mm_points=optional_series("weather.precipitation_mm"),
    )
    ratio = pv.energy_kwh / load.energy_kwh if load.energy_kwh > 0 else None
    pv_payload = asdict(pv)
    pv_payload.update({
        "before_solar_noon_kwh": None,
        "after_solar_noon_kwh": None,
        "output_energy_kwh": pv_output.energy_kwh,
        "mppt_efficiency": (
            pv_output.energy_kwh / pv.energy_kwh if pv.energy_kwh > 0 else None
        ),
    })
    battery_payload = asdict(battery)
    previous_day = local_date - timedelta(days=1)
    previous_start, previous_end = local_day_bounds(previous_day, config.timezone)
    previous_sunset = event_time(
        "solar.sunset_at", previous_day, previous_start, previous_end
    )
    if sunrise is not None and previous_sunset is not None:
        previous_soc = _convert(
            fetch_numeric_series(
                connection, tables["battery.soc_pct"], previous_start, previous_end
            ),
            definitions["battery.soc_pct"].conversion,
        )
        previous_sunset_soc = value_at(previous_soc, previous_sunset)
        sunrise_soc = value_at(battery_soc, sunrise)
        if previous_sunset_soc is not None and sunrise_soc is not None:
            battery_payload["overnight_soc_drop_pct"] = (
                previous_sunset_soc - sunrise_soc
            )

    def energy_between(points, left, right):
        if left is None or right is None or right <= left:
            return None
        selected = [(at, value) for at, value in points if left <= at <= right]
        left_value = value_at(points, left)
        right_value = value_at(points, right)
        if left_value is not None:
            selected.append((left, left_value))
        if right_value is not None:
            selected.append((right, right_value))
        selected = sorted(set(selected))
        return integrate_trapezoid(selected, max_gap).value_hours / 1000.0

    if sunrise is not None and sunset is not None and sunset > sunrise:
        solar_noon = sunrise + (sunset - sunrise) / 2
        pv_payload["before_solar_noon_kwh"] = energy_between(
            series("pv.input_power_w"), start, solar_noon
        )
        pv_payload["after_solar_noon_kwh"] = energy_between(
            series("pv.input_power_w"), solar_noon, end
        )

    active_loads = {}
    for canonical, label in (
        ("load.dishwasher_state", "dishwasher"),
        ("load.shurflo_pump_state", "shurflo_pump"),
    ):
        if canonical in tables:
            states = fetch_text_series(connection, tables[canonical], start, end)
            active_loads[label] = {
                "state_on_hours": state_duration_seconds(states, "ON") / 3600.0,
                "measurement": "switch_state_only",
                "energy_kwh": None,
            }
    load_payload = asdict(load)
    load_payload["active_loads"] = active_loads
    weather_payload = asdict(weather)
    weather_payload["snow_state"] = fetch_snow_state_as_of(connection, end)
    return {
        "status": "ok",
        "mode": "read_only_dry_run",
        "local_date": local_date.isoformat(),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "battery": battery_payload,
        "pv": pv_payload,
        "load": load_payload,
        "weather": weather_payload,
        "balance": {
            "pv_load_ratio": ratio,
            "surplus_deficit_kwh": pv.energy_kwh - load.energy_kwh,
        },
    }
