from datetime import date
import json

import pytest

from earthship_energy.config import load_source_config
from earthship_energy.materialize import (
    EpochConfigError,
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

    def fetchone(self):
        return self._rows.pop(0)


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
    assert result == {"metric_sources": 15, "system_epochs": 3}
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
        "pv": {"energy_kwh": 7, "peak_w": 3000, "coverage": .98, "quality": "ok"},
        "load": {"energy_kwh": 5, "peak_w": 1200, "coverage": .97, "quality": "ok"},
        "weather": {"min_temperature_c": 10, "max_temperature_c": 25,
                    "mean_temperature_c": 18, "irradiance_wh_m2": 5000,
                    "peak_irradiance_w_m2": 800, "coverage": .96, "quality": "ok"},
        "balance": {"pv_load_ratio": 1.4, "surplus_deficit_kwh": 2},
    }
    result = materialize_daily_snapshot(connection, snapshot, "discover_4_module_2026")
    assert result["tables_written"] == 4
    assert result["cumulative_efc"] == 1.375
    assert connection.commits == 1
    sql = "\n".join(statement for statement, _ in connection.statements)
    for table in ("daily_battery", "daily_pv", "daily_load", "daily_weather"):
        assert f"energy_analytics.{table}" in sql
        assert "ON CONFLICT" in sql
