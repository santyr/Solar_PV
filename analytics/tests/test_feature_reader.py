from datetime import datetime, timezone

from earthship_energy.feature_reader import fetch_feature_rows


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
    assert "public.item0001" in sql
    assert "public.item0007" in sql
    assert "- 32.0) * 5.0 / 9.0" in sql
    assert params == (
        START, END, 15,
        "America/Denver", "America/Denver",
        "America/Denver", "America/Denver",
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
