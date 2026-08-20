from datetime import date
import json

import pytest

from earthship_energy.config import load_source_config
from earthship_energy.materialize import (
    EpochConfigError,
    _recompute_battery_rollups,
    load_epoch_config,
    materialize_daily_snapshot,
    seed_reference_data,
    select_epoch,
)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, statement, params=None):
        self.connection.statements.append((statement, params))
        if statement.startswith("SELECT COALESCE"):
            self._rows = [(1.25, date(2026, 8, 18))]
        elif "SELECT local_date, daily_efc, reached_99" in statement:
            self._rows = [(date(2026, 8, 19), 0.125, True)]

    def fetchone(self):
        return self._rows.pop(0)

    def fetchall(self):
        rows = self._rows
        self._rows = []
        return rows


class FakeConnection:
    def __init__(self):
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_load_and_select_current_epoch(tmp_path):
    path = tmp_path / "epochs.json"
    path.write_text(json.dumps({
        "version": 1,
        "timezone": "America/Denver",
        "epochs": [
            {"id": "old", "start_local_date": None,
             "end_local_date_exclusive": "2026-07-19", "current_analytics": False},
            {"id": "current", "start_local_date": "2026-07-19",
             "end_local_date_exclusive": None, "current_analytics": True,
             "nominal_usable_kwh": 20.48},
        ],
    }))
    epochs = load_epoch_config(path)
    assert select_epoch(epochs, date(2026, 8, 1)).epoch_id == "current"
    assert select_epoch(epochs, date(2026, 7, 1)).epoch_id == "old"


def test_rejects_overlapping_epochs(tmp_path):
    path = tmp_path / "epochs.json"
    path.write_text(json.dumps({"version": 1, "timezone": "UTC", "epochs": [
        {"id": "a", "start_local_date": "2026-01-01", "end_local_date_exclusive": None, "current_analytics": True},
        {"id": "b", "start_local_date": "2026-02-01", "end_local_date_exclusive": None, "current_analytics": False},
    ]}))
    with pytest.raises(EpochConfigError, match="overlap"):
        load_epoch_config(path)


def test_seed_reference_data_is_idempotent_upsert():
    connection = FakeConnection()
    sources = load_source_config()
    epochs = load_epoch_config()
    result = seed_reference_data(connection, sources, epochs)
    assert result == {"metric_sources": 21, "system_epochs": 3}
    assert connection.commits == 1
    sql = "\n".join(statement for statement, _ in connection.statements)
    assert "ON CONFLICT (canonical_name) DO UPDATE" in sql
    assert "ON CONFLICT (epoch_id) DO UPDATE" in sql


def test_materialize_daily_snapshot_upserts_all_daily_tables():
    connection = FakeConnection()
    snapshot = {
        "status": "ok", "mode": "read_only_dry_run", "local_date": "2026-08-19",
        "battery": {
            "min_soc_pct": 80, "max_soc_pct": 100, "mean_soc_pct": 91,
            "sunrise_soc_pct": None, "sunset_soc_pct": None,
            "overnight_soc_drop_pct": None, "depth_of_discharge_pct": 20,
            "hours_above_90": 10, "hours_above_95": 5, "hours_below_50": 0,
            "hours_below_25": 0, "charge_kwh": 3, "discharge_kwh": 2,
            "net_kwh": 1, "daily_efc": .125, "min_temperature_c": 20,
            "max_temperature_c": 25, "mean_temperature_c": 22,
            "reached_95": True, "reached_99": True, "reached_100": True,
            "first_reached_99_at": None, "coverage": .99, "quality": "ok",
        },
        "pv": {
            "energy_kwh": 7, "peak_w": 3000, "productive_hours": 8.5,
            "first_productive_at": "2026-08-19T13:00:00+00:00",
            "last_productive_at": "2026-08-19T23:00:00+00:00",
            "before_solar_noon_kwh": None, "after_solar_noon_kwh": None,
            "output_energy_kwh": 6.5, "mppt_efficiency": 0.928571,
            "coverage": .98, "quality": "ok",
        },
        "load": {
            "energy_kwh": 5, "peak_w": 1200,
            "active_loads": {"dishwasher": {
                "state_on_hours": 1.5,
                "measurement": "switch_state_only",
                "energy_kwh": None,
            }},
            "coverage": .97, "quality": "ok",
        },
        "weather": {"min_temperature_c": 10, "max_temperature_c": 25,
                    "mean_temperature_c": 18, "irradiance_wh_m2": 5000,
                    "peak_irradiance_w_m2": 800, "precipitation_mm": 2.5,
                    "snow_state": None, "coverage": .96, "quality": "ok"},
        "balance": {"pv_load_ratio": 1.4, "surplus_deficit_kwh": 2},
    }
    result = materialize_daily_snapshot(connection, snapshot, "discover_4_module_2026")
    assert result["tables_written"] == 4
    assert result["cumulative_efc"] == 0.125
    assert connection.commits == 1
    sql = "\n".join(statement for statement, _ in connection.statements)
    for table in ("daily_battery", "daily_pv", "daily_load", "daily_weather"):
        assert f"energy_analytics.{table}" in sql
        assert "ON CONFLICT" in sql
    pv_statement = next(
        (statement, params) for statement, params in connection.statements
        if "INSERT INTO energy_analytics.daily_pv" in statement
    )
    assert "productive_hours" in pv_statement[0]
    assert "mppt_efficiency" in pv_statement[0]
    assert 0.928571 in pv_statement[1]
    load_statement = next(
        (statement, params) for statement, params in connection.statements
        if "INSERT INTO energy_analytics.daily_load" in statement
    )
    assert "active_loads" in load_statement[0]
    weather_statement = next(
        (statement, params) for statement, params in connection.statements
        if "INSERT INTO energy_analytics.daily_weather" in statement
    )
    assert "precipitation_mm" in weather_statement[0]


def test_recomputes_cumulative_efc_and_true_contiguous_no_full_streaks():
    class RollupCursor:
        def __init__(self):
            self.updates = []

        def execute(self, statement, params=None):
            if statement.startswith("SELECT local_date"):
                return
            self.updates.append(params)

        def fetchall(self):
            return [
                (date(2026, 8, 1), 0.1, False),
                (date(2026, 8, 2), 0.2, True),
                (date(2026, 8, 4), 0.1, False),
                (date(2026, 8, 5), 0.1, False),
            ]

    cursor = RollupCursor()
    cumulative = _recompute_battery_rollups(cursor, "discover")
    assert cumulative == {
        date(2026, 8, 1): 0.1,
        date(2026, 8, 2): 0.3,
        date(2026, 8, 4): 0.4,
        date(2026, 8, 5): 0.5,
    }
    assert cursor.updates == [
        (0.1, None, 1, "discover", date(2026, 8, 1)),
        (0.3, 0, 0, "discover", date(2026, 8, 2)),
        (0.4, 2, 1, "discover", date(2026, 8, 4)),
        (0.5, 3, 2, "discover", date(2026, 8, 5)),
    ]
