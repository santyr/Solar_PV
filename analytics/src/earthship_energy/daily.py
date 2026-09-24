"""Compose a read-only daily analytics snapshot from resolved raw sources."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta

from .aggregation import (
    aggregate_battery,
    aggregate_power,
    aggregate_weather,
    value_at,
)
from .config import SourceConfig
from .bms_evidence import EvidenceSequenceError, soc_at
from .events import fetch_snow_state_as_of
from .reader import (
    datetime_state_for_local_date,
    fetch_bms_soc_intervals,
    fetch_freshness_observations,
    fetch_numeric_series,
    fetch_observation_stats,
    fetch_text_series,
    state_duration_seconds,
)
from .series import (
    Point,
    fahrenheit_to_celsius,
    integrate_trapezoid,
    local_day_bounds,
)
from .quality import assess_source_quality, assess_bms_source_quality
from .quality import assess_power_source_quality
from .power_reader import read_power_history
from .power_evidence import BOUNDS, utc
from .power_intervals import account_power_intervals, account_common_power
from .temperature_quality import NORTH_WALL_ITEM, NORTH_WALL_SOURCE, read_north_wall_quality


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
    *,
    bank_epoch=None,
    power_evidence_settings=None,
    power_evidence_table=None,
    power_evidence_cutover=None,
    temperature_evidence_settings=None,
    temperature_evidence_policy=None,
    temperature_evidence_assessed_at: datetime | None = None,
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
    power_options = (power_evidence_settings, power_evidence_table, power_evidence_cutover)
    configured_power = any(option is not None for option in power_options)
    if configured_power and any(option is None for option in power_options):
        raise ValueError('complete power evidence configuration is required')
    cutover = utc(power_evidence_cutover) if configured_power else None
    qualified_power = configured_power and end > cutover
    temperature_options = (temperature_evidence_settings, temperature_evidence_policy,
                           temperature_evidence_assessed_at)
    qualified_north_wall = any(option is not None for option in temperature_options)
    if qualified_north_wall and any(option is None for option in temperature_options):
        raise ValueError('complete temperature evidence configuration is required')
    if qualified_north_wall and (temperature_evidence_assessed_at.tzinfo is None
                                 or temperature_evidence_assessed_at.utcoffset() is None):
        raise ValueError('north-wall assessment time must be aware')
    if qualified_north_wall and end > temperature_evidence_assessed_at:
        raise ValueError('north-wall evidence requires an elapsed local day')
    if qualified_north_wall and NORTH_WALL_SOURCE not in tables:
        raise ValueError('north-wall source unresolved')
    power_history = None
    power_stats = None
    if qualified_power:
        # One bounded independent read-only snapshot for all three fields.
        # Errors propagate: never silently substitute numeric held history.
        power_history = read_power_history(
            power_evidence_settings, power_evidence_table, start, end, cutover=cutover,
        )
        if set(power_history) != set(BOUNDS):
            raise ValueError('incomplete qualified power history')
        power_stats = fetch_observation_stats(connection, power_evidence_table, start, end)

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
    atomic_soc = definitions["battery.soc_pct"].stale_policy == "atomic_bms_evidence"
    evidence_table = next((getattr(source, "freshness_table_name", None)
                           for source in resolved_sources
                           if source.canonical_name == "battery.soc_pct"), None)
    evidence_errors = {}

    def qualified_soc(left, right):
        if bank_epoch is None:
            raise ValueError("atomic SoC requires a configured physical bank start")
        if evidence_table is None or bank_epoch.start_local_date is None:
            return []
        bank_start = local_day_bounds(bank_epoch.start_local_date, config.timezone)[0]
        bank_end = (local_day_bounds(bank_epoch.end_local_date_exclusive, config.timezone)[0]
                    if bank_epoch.end_local_date_exclusive is not None else None)
        try:
            return fetch_bms_soc_intervals(
                connection, evidence_table, left, right,
                epoch_start=bank_start, epoch_end=bank_end,
            )
        except EvidenceSequenceError:
            evidence_errors[(left, right)] = "ambiguous_evidence_sequence"
            return []

    battery_soc = [] if atomic_soc else series("battery.soc_pct")
    battery_intervals = qualified_soc(start, end) if atomic_soc else None

    battery = aggregate_battery(
        soc_points=battery_soc,
        power_points=[] if qualified_power else series("battery.dc_power_w"),
        temperature_c_points=series("battery.temperature_c"),
        window_start=start,
        window_end=end,
        max_gap=max_gap,
        nominal_usable_kwh=20.48,
        power_sign=definitions["battery.dc_power_w"].sign,
        sunrise=sunrise,
        sunset=sunset,
        soc_intervals=battery_intervals,
        power_intervals=power_history['battery.dc_power_w'] if qualified_power else None,
    )
    pv = aggregate_power(
        [] if qualified_power else series("pv.input_power_w"), start, end, max_gap=max_gap,
        power_intervals=power_history['pv.input_power_w'] if qualified_power else None,
    )
    pv_output = aggregate_power(
        [] if qualified_power else series("pv.output_power_w"), start, end, max_gap=max_gap,
        power_intervals=power_history['pv.output_power_w'] if qualified_power else None,
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
    ratio = pv.energy_kwh / load.energy_kwh if not qualified_power and load.energy_kwh > 0 else None
    pv_payload = asdict(pv)
    pv_payload.update({
        "before_solar_noon_kwh": None,
        "after_solar_noon_kwh": None,
        "output_energy_kwh": pv_output.energy_kwh,
        "mppt_efficiency": (
            pv_output.energy_kwh / pv.energy_kwh if not qualified_power and pv.energy_kwh > 0 else None
        ),
    })
    common_pv = None
    if qualified_power:
        common_pv = account_common_power(
            power_history['pv.input_power_w'], power_history['pv.output_power_w'],
            window_start=start, window_end=end,
        )
        pv_payload['mppt_efficiency'] = (
            common_pv[1].positive_kwh / common_pv[0].positive_kwh
            if common_pv[0].positive_kwh > 0 else None
        )
    battery_payload = asdict(battery)
    previous_day = local_date - timedelta(days=1)
    previous_start, previous_end = local_day_bounds(previous_day, config.timezone)
    previous_sunset = event_time(
        "solar.sunset_at", previous_day, previous_start, previous_end
    )
    if sunrise is not None and previous_sunset is not None:
        if atomic_soc:
            previous_sunset_soc = soc_at(qualified_soc(previous_start, previous_end), previous_sunset)
            sunrise_soc = soc_at(battery_intervals, sunrise)
        else:
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
        if qualified_power:
            return account_power_intervals(
                power_history['pv.input_power_w'], window_start=left, window_end=right,
            ).positive_kwh
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
            [] if qualified_power else series("pv.input_power_w"), start, solar_noon
        )
        pv_payload["after_solar_noon_kwh"] = energy_between(
            [] if qualified_power else series("pv.input_power_w"), solar_noon, end
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

    source_quality = []
    for resolved in resolved_sources:
        if resolved.table_name is None:
            continue
        definition = definitions[resolved.canonical_name]
        if qualified_power and resolved.canonical_name in BOUNDS:
            source_quality.append(assess_power_source_quality(
                canonical_name=resolved.canonical_name,
                intervals=power_history[resolved.canonical_name], window_start=start, window_end=end,
                row_count=power_stats[0], first_at=power_stats[1], last_at=power_stats[2], cutover=cutover,
            ))
            continue
        if atomic_soc and resolved.canonical_name == "battery.soc_pct":
            stats = (fetch_observation_stats(connection, evidence_table, start, end)
                     if evidence_table is not None else (0, None, None))
            source_quality.append(assess_bms_source_quality(
                intervals=battery_intervals, window_start=start, window_end=end,
                row_count=stats[0], first_at=stats[1], last_at=stats[2],
                freshness_item=definition.freshness_item,
                reason=evidence_errors.get((start, end)),
            ))
            continue
        row_count, first_at, last_at = fetch_observation_stats(
            connection, resolved.table_name, start, end
        )
        if qualified_north_wall and resolved.canonical_name == NORTH_WALL_SOURCE:
            if definition.item_name != NORTH_WALL_ITEM:
                raise ValueError('north-wall source Item identity mismatch')
            source_quality.append(read_north_wall_quality(
                temperature_evidence_settings, temperature_evidence_policy,
                start=start, end=end, assessed_at=temperature_evidence_assessed_at,
                row_count=row_count, first_at=first_at, last_at=last_at,
            ))
            continue
        freshness_table = getattr(resolved, "freshness_table_name", None)
        if (definition.stale_policy == "local_date_must_match"
                and definition.freshness_item != definition.item_name):
            raise ValueError("local-date schedule requires its own Item as evidence")
        freshness_points = (
            fetch_freshness_observations(connection, freshness_table, start, end)
            if freshness_table is not None else []
        )
        source_quality.append(assess_source_quality(
            canonical_name=resolved.canonical_name,
            row_count=row_count,
            first_at=first_at,
            last_at=last_at,
            window_start=start,
            window_end=end,
            stale_policy=definition.stale_policy,
            stale_after_seconds=definition.stale_after_seconds,
            freshness_item=definition.freshness_item,
            freshness_points=freshness_points,
            site_timezone=config.timezone,
        ))

    quality_by_name = {row["canonical_name"]: row for row in source_quality}

    def apply_source_quality(payload, names):
        rows = [quality_by_name[name] for name in names if name in quality_by_name]
        if not rows:
            payload["coverage"] = 0.0
            payload["quality"] = "insufficient_data"
            return
        payload["coverage"] = min(
            float(payload["coverage"]), *(float(row["coverage"]) for row in rows)
        )
        if any(row["quality"] not in {"ok", "partial"} for row in rows):
            payload["quality"] = "insufficient_data"
        elif payload["coverage"] < 0.9:
            payload["quality"] = "partial" if payload["coverage"] >= 0.5 else "insufficient_data"

    apply_source_quality(battery_payload, (
        "battery.soc_pct", "battery.dc_power_w", "battery.temperature_c",
    ))
    apply_source_quality(pv_payload, ("pv.input_power_w", "pv.output_power_w"))
    apply_source_quality(load_payload, ("house.ac_power_w",))
    apply_source_quality(weather_payload, (
        "weather.irradiance_w_m2", "weather.outdoor_temperature_c",
    ))
    snapshot = {
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
            "surplus_deficit_kwh": None if qualified_power else pv.energy_kwh - load.energy_kwh,
        },
        "source_quality": source_quality,
    }
    if configured_power:
        snapshot['power_accounting'] = {
            'version': 1,
            'policy': 'qualified_power_evidence_v1' if qualified_power else 'legacy_numeric_estimate',
            'cutover': cutover.isoformat(),
            'qualified_fields': sorted(BOUNDS) if qualified_power else [],
            'balance_reason': 'ac_load_evidence_unqualified' if qualified_power else None,
            'efficiency_reason': ('no_common_positive_input'
                                  if qualified_power and common_pv[0].positive_kwh == 0 else None),
            'efficiency_coverage': common_pv[0].coverage if qualified_power else None,
        }
    return snapshot
