from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import json

import pytest

from earthship_energy.feature_reader import fetch_feature_rows
from earthship_energy import feature_reader
from earthship_energy.bms_evidence import build_soc_intervals, EvidenceSequenceError
from earthship_energy.series import local_day_bounds


UTC = timezone.utc
START = datetime(2026, 8, 1, tzinfo=UTC)
END = datetime(2026, 8, 2, tzinfo=UTC)


class Cursor:
    def __init__(self):
        self.executed = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.executed = (sql, params)

    def fetchall(self):
        return [(
            START, "discover", 80.0, 78.0, 1000.0, 500.0, 400.0, 450.0,
            12.0, 700.0, True, False, True, 55.0, 650.0, 7.2,
            START, START, START, START, "current", 0.2, 0.1,
        )]


class Connection:
    def __init__(self):
        self.cursor_instance = Cursor()

    def cursor(self):
        return self.cursor_instance


def test_feature_reader_uses_validated_tables_and_as_of_forecast_constraints():
    connection = Connection()
    tables = {
        "battery.soc_pct": "item0001",
        "pv.input_power_w": "item0002",
        "house.ac_power_w": "item0003",
        "weather.outdoor_temperature_c": "item0004",
        "weather.irradiance_w_m2": "item0005",
        "load.dishwasher_state": "item0006",
        "load.shurflo_pump_state": "item0007",
    }
    rows = fetch_feature_rows(
        connection, tables, START, END,
        cadence_minutes=15, timezone_name="America/Denver",
        conversions={"weather.outdoor_temperature_c": "fahrenheit_to_celsius"},
    )
    assert rows[0]["forecast_status"] == "current"
    assert rows[0]["dishwasher_active"] is False
    sql, params = connection.cursor_instance.executed
    assert "generate_series" in sql
    assert "issued_at <= r.at" in sql
    assert sql.count("captured_at <= r.at") == 3
    assert "valid_for = (((r.at AT TIME ZONE %s)::date + 1)::timestamp AT TIME ZONE %s)" in " ".join(sql.split())
    assert "payload->>'forecast_day' = (r.at AT TIME ZONE %s)::date::text" in " ".join(sql.split())
    assert "ftemp.issued_at IS NULL OR frad.issued_at IS NULL" in sql
    assert "public.item0001" in sql
    assert "public.item0007" in sql
    assert "- 32.0) * 5.0 / 9.0" in sql
    assert params == (
        START, END, 15,
        "America/Denver", "America/Denver",
        "America/Denver", "America/Denver",
        "America/Denver",
    )


def test_feature_reader_rejects_unvalidated_table_names():
    import pytest

    with pytest.raises(ValueError, match="table"):
        fetch_feature_rows(
            Connection(), {"battery.soc_pct": "item0001;drop"},
            START, END, cadence_minutes=15, timezone_name="America/Denver",
        )


def test_feature_reader_rejects_unknown_conversion():
    import pytest

    tables = {
        "battery.soc_pct": "item0001",
        "pv.input_power_w": "item0002",
        "house.ac_power_w": "item0003",
        "weather.outdoor_temperature_c": "item0004",
        "weather.irradiance_w_m2": "item0005",
    }
    with pytest.raises(ValueError, match="conversion"):
        fetch_feature_rows(
            Connection(), tables, START, END,
            cadence_minutes=15, timezone_name="America/Denver",
            conversions={"weather.outdoor_temperature_c": "mystery"},
        )


TABLES = {name: f"item{index:04d}" for index, name in
          enumerate(sorted(feature_reader.REQUIRED_TABLES), 1)}
EPOCH = SimpleNamespace(start_local_date=date(2026, 7, 19), end_local_date_exclusive=None)


def evidence(at, soc):
    millis = int(at.timestamp() * 1000)
    return (at, json.dumps({
        "version": 1, "streamEpoch": "864142d5-99ee-4b7a-b5fc-e6a96e7274d8",
        "recordedAt": millis, "status": "valid", "reason": "ok",
        "observedAt": millis, "scaleObservedAt": millis,
        "validUntil": millis + 120000, "soc": soc,
    }))


@pytest.mark.parametrize("current,lag", [(True, True), (True, False), (False, True), (False, False)])
def test_atomic_current_and_lag_are_independent_and_other_fields_unchanged(monkeypatch, current, lag):
    connection = Connection()
    baseline = fetch_feature_rows(connection, TABLES, START, END,
                                  cadence_minutes=15, timezone_name="America/Denver")
    observations = []
    if lag:
        observations.append(evidence(START - timedelta(hours=1), 25))
    if current:
        observations.append(evidence(START, 95))

    def read(_connection, table, left, right, *, epoch_start, epoch_end):
        assert left == START - timedelta(hours=1)
        assert right == END
        assert table == "item0613"
        assert epoch_start == local_day_bounds(EPOCH.start_local_date, "America/Denver")[0]
        return build_soc_intervals(observations, left, right,
                                   epoch_start=epoch_start, epoch_end=epoch_end)

    monkeypatch.setattr(feature_reader, "fetch_bms_soc_intervals", read)
    rows = fetch_feature_rows(connection, TABLES, START, END, cadence_minutes=15,
                              timezone_name="America/Denver", atomic_soc=True,
                              soc_evidence_table="item0613", bank_epochs=(EPOCH,))
    assert rows[0]["battery_soc_pct"] == (95 if current else None)
    assert rows[0]["battery_soc_pct_lag_1h"] == (25 if lag else None)
    for name in feature_reader.FEATURE_FIELDS:
        if name not in {"battery_soc_pct", "battery_soc_pct_lag_1h"}:
            assert rows[0][name] == baseline[0][name]
    sql = connection.cursor_instance.executed[0]
    assert f"public.{TABLES['battery.soc_pct']}" not in sql


@pytest.mark.parametrize("mode", ["missing", "expired", "sequence", "prebank"])
def test_atomic_feature_gaps_never_fall_back_to_sql_soc(monkeypatch, mode):
    def read(_connection, table, left, right, *, epoch_start, epoch_end):
        if mode == "sequence":
            raise EvidenceSequenceError("conflicting timestamps")
        # Exact expiry has no ownership of the point, even with status=valid.
        observations = [evidence(START - timedelta(seconds=120), 99)]
        return build_soc_intervals(observations, left, right,
                                   epoch_start=epoch_start, epoch_end=epoch_end)

    monkeypatch.setattr(feature_reader, "fetch_bms_soc_intervals", read)
    epoch = (SimpleNamespace(start_local_date=date(2026, 8, 3), end_local_date_exclusive=None)
             if mode == "prebank" else EPOCH)
    rows = fetch_feature_rows(Connection(), TABLES, START, END, cadence_minutes=5,
                              timezone_name="America/Denver", atomic_soc=True,
                              soc_evidence_table=None if mode == "missing" else "item0613",
                              bank_epochs=(epoch,))
    assert rows[0]["battery_soc_pct"] is None
    assert rows[0]["battery_soc_pct_lag_1h"] is None


def test_atomic_feature_options_fail_before_queries():
    connection = Connection()
    with pytest.raises(ValueError, match="bank epochs"):
        fetch_feature_rows(connection, TABLES, START, END, cadence_minutes=15,
                           timezone_name="America/Denver", atomic_soc=True)
    with pytest.raises(ValueError, match="evidence table"):
        fetch_feature_rows(connection, TABLES, START, END, cadence_minutes=15,
                           timezone_name="America/Denver", atomic_soc=True,
                           bank_epochs=(EPOCH,), soc_evidence_table="item0613;DROP")
    with pytest.raises(ValueError, match="timezone-aware"):
        fetch_feature_rows(connection, TABLES, START.replace(tzinfo=None), END,
                           cadence_minutes=15, timezone_name="America/Denver")
    assert connection.cursor_instance.executed is None


@pytest.mark.parametrize("point", [datetime(2026, 3, 8, 3, 30, tzinfo=ZoneInfo("America/Denver")),
                                  datetime(2026, 11, 1, 1, 30, fold=1, tzinfo=ZoneInfo("America/Denver"))])
def test_one_hour_lag_is_elapsed_time_across_dst(monkeypatch, point):
    connection = Connection()
    row = list(connection.cursor_instance.fetchall()[0])
    row[0] = point
    monkeypatch.setattr(connection.cursor_instance, "fetchall", lambda: [tuple(row)])
    instant = point.astimezone(UTC)
    observations = [evidence(instant - timedelta(hours=1), 65), evidence(instant, 75)]

    def read(_connection, table, left, right, **kwargs):
        assert left == instant - timedelta(hours=1)
        return build_soc_intervals(observations, left, right, **kwargs)

    monkeypatch.setattr(feature_reader, "fetch_bms_soc_intervals", read)
    epoch = SimpleNamespace(start_local_date=date(2026, 1, 1), end_local_date_exclusive=None)
    rows = fetch_feature_rows(connection, TABLES, point, instant + timedelta(minutes=15),
                              cadence_minutes=15, timezone_name="America/Denver",
                              atomic_soc=True, soc_evidence_table="item0613", bank_epochs=(epoch,))
    assert rows[0]["battery_soc_pct"] == 75
    assert rows[0]["battery_soc_pct_lag_1h"] == 65


def test_each_lag_uses_its_own_physical_bank_window(monkeypatch):
    boundary = local_day_bounds(date(2026, 7, 19), "America/Denver")[0]
    previous = SimpleNamespace(start_local_date=date(2026, 7, 1),
                               end_local_date_exclusive=date(2026, 7, 19))
    observations = [evidence(boundary - timedelta(hours=1), 55),
                    evidence(boundary - timedelta(seconds=30), 60)]

    def read(_connection, table, left, right, **kwargs):
        return build_soc_intervals(observations, left, right, **kwargs)

    monkeypatch.setattr(feature_reader, "fetch_bms_soc_intervals", read)
    lookup = feature_reader._soc_lookup(object(), "item0613", boundary - timedelta(hours=1),
                                        boundary + timedelta(minutes=15), (previous, EPOCH),
                                        "America/Denver")
    assert lookup(boundary - timedelta(hours=1)) == 55
    assert lookup(boundary) is None  # prior bank carry cannot authorize the new bank
    observations.append(evidence(boundary, 75))
    lookup = feature_reader._soc_lookup(object(), "item0613", boundary - timedelta(hours=1),
                                        boundary + timedelta(minutes=15), (previous, EPOCH),
                                        "America/Denver")
    assert lookup(boundary) == 75
    assert lookup(boundary - timedelta(hours=1)) == 55
