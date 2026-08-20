from datetime import date, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from earthship_energy import daily
from earthship_energy.config import load_source_config
from earthship_energy.series import local_day_bounds


def test_build_daily_snapshot_is_read_only_and_uses_canonical_conversions(monkeypatch):
    config = load_source_config()
    required = {
        "battery.soc_pct": "item0001",
        "battery.dc_power_w": "item0002",
        "battery.temperature_c": "item0003",
        "pv.input_power_w": "item0004",
        "pv.output_power_w": "item0008",
        "house.ac_power_w": "item0005",
        "weather.irradiance_w_m2": "item0006",
        "weather.outdoor_temperature_c": "item0007",
        "weather.precipitation_mm": "item0009",
        "solar.sunrise_at": "item0010",
        "solar.sunset_at": "item0011",
        "load.dishwasher_state": "item0012",
        "load.shurflo_pump_state": "item0013",
    }
    resolved = [
        SimpleNamespace(canonical_name=name, table_name=table)
        for name, table in required.items()
    ]
    start, end = local_day_bounds(date(2026, 1, 1), config.timezone)
    midpoint = start + (end - start) / 2

    def fake_fetch(_connection, table, _start, _end):
        values = {
            "item0001": [80, 90, 100],
            "item0002": [-1000, 1000, 1000],
            "item0003": [68, 71.6, 75.2],
            "item0004": [0, 1000, 0],
            "item0005": [500, 500, 500],
            "item0006": [0, 500, 0],
            "item0007": [32, 50, 68],
            "item0008": [0, 900, 0],
            "item0009": [0, 0.1, 0.2],
        }[table]
        midpoint_for_window = _start + (_end - _start) / 2
        return [(_start, values[0]), (midpoint_for_window, values[1]), (_end, values[2])]

    def fake_text(_connection, table, window_start, window_end):
        if table == "item0010":
            value = "2026-01-01T07:00:00-0700"
            return [(window_start, value), (window_end, value)]
        if table == "item0011":
            local_day = window_start.astimezone(ZoneInfo("America/Denver")).date()
            value = f"{local_day.isoformat()}T17:00:00-0700"
            return [(window_start, value), (window_end, value)]
        if table == "item0012":
            return [
                (window_start, "OFF"),
                (window_start + timedelta(hours=1), "ON"),
                (window_start + timedelta(hours=3), "OFF"),
                (window_end, "OFF"),
            ]
        return [(window_start, "OFF"), (window_end, "OFF")]

    monkeypatch.setattr(daily, "fetch_numeric_series", fake_fetch)
    monkeypatch.setattr(daily, "fetch_text_series", fake_text)
    monkeypatch.setattr(
        daily, "fetch_observation_stats", lambda *_: (3, start, end)
    )
    monkeypatch.setattr(daily, "fetch_snow_state_as_of", lambda *_: "snow_cleared")
    result = daily.build_daily_snapshot(object(), config, resolved, date(2026, 1, 1))
    assert result["mode"] == "read_only_dry_run"
    assert result["battery"]["min_temperature_c"] == 20
    assert result["weather"]["min_temperature_c"] == 0
    assert result["pv"]["energy_kwh"] == 12
    assert result["pv"]["output_energy_kwh"] == 10.8
    assert result["pv"]["mppt_efficiency"] == 0.9
    assert result["pv"]["productive_hours"] > 0
    assert result["pv"]["first_productive_at"] == midpoint
    assert result["pv"]["last_productive_at"] == midpoint
    assert result["pv"]["before_solar_noon_kwh"] is not None
    assert result["pv"]["after_solar_noon_kwh"] is not None
    assert result["battery"]["sunrise_soc_pct"] is not None
    assert result["battery"]["sunset_soc_pct"] is not None
    assert result["battery"]["overnight_soc_drop_pct"] is not None
    assert result["weather"]["precipitation_mm"] == 5.08
    assert result["weather"]["snow_state"] == "snow_cleared"
    assert result["load"]["active_loads"] == {
        "dishwasher": {
            "state_on_hours": 2.0,
            "measurement": "switch_state_only",
            "energy_kwh": None,
        },
        "shurflo_pump": {
            "state_on_hours": 0.0,
            "measurement": "switch_state_only",
            "energy_kwh": None,
        },
    }
    assert result["load"]["energy_kwh"] == 12
    assert result["balance"]["pv_load_ratio"] == 1
    assert result["battery"]["quality"] == "insufficient_data"
    assert len(result["source_quality"]) == len(required)
