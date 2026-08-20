from datetime import date
from types import SimpleNamespace

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
        "house.ac_power_w": "item0005",
        "weather.irradiance_w_m2": "item0006",
        "weather.outdoor_temperature_c": "item0007",
    }
    resolved = [
        SimpleNamespace(canonical_name=name, table_name=table)
        for name, table in required.items()
    ]
    start, end = local_day_bounds(date(2026, 1, 1), config.timezone)

    def fake_fetch(_connection, table, _start, _end):
        values = {
            "item0001": [80, 90, 100],
            "item0002": [-1000, 1000, 1000],
            "item0003": [68, 71.6, 75.2],
            "item0004": [0, 1000, 0],
            "item0005": [500, 500, 500],
            "item0006": [0, 500, 0],
            "item0007": [32, 50, 68],
        }[table]
        midpoint = start + (end - start) / 2
        return [(start, values[0]), (midpoint, values[1]), (end, values[2])]

    monkeypatch.setattr(daily, "fetch_numeric_series", fake_fetch)
    result = daily.build_daily_snapshot(object(), config, resolved, date(2026, 1, 1))
    assert result["mode"] == "read_only_dry_run"
    assert result["battery"]["min_temperature_c"] == 20
    assert result["weather"]["min_temperature_c"] == 0
    assert result["pv"]["energy_kwh"] == 12
    assert result["load"]["energy_kwh"] == 12
    assert result["balance"]["pv_load_ratio"] == 1
