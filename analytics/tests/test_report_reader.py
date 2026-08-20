from datetime import date

from earthship_energy.report_reader import (
    fetch_daily_report_rows,
    fetch_module_report_rows,
)


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
            date(2026, 8, 1), 80.0, True, 1.0, 0.5, .04, 4.04,
            3.0, 1.0, 12.0, 27.0, "ok", 7.0, 5.0,
        )]


class Connection:
    def __init__(self):
        self.cursor_instance = Cursor()

    def cursor(self):
        return self.cursor_instance


def test_fetch_daily_report_rows_uses_bounded_join():
    connection = Connection()
    rows = fetch_daily_report_rows(
        connection, "discover", date(2026, 8, 1), date(2026, 9, 1)
    )
    assert rows[0]["pv_kwh"] == 7
    assert rows[0]["load_kwh"] == 5
    assert rows[0]["cumulative_efc"] == 4.04
    assert rows[0]["hours_above_95"] == 1.0
    sql, params = connection.cursor_instance.executed
    assert "JOIN energy_analytics.daily_pv" in sql
    assert params == ("discover", date(2026, 8, 1), date(2026, 9, 1))


class ModuleCursor(Cursor):
    def fetchall(self):
        from datetime import datetime, timezone

        return [(
            7, "lynk.csv", "a" * 64, "module-1",
            datetime(2026, 8, 1, tzinfo=timezone.utc),
            90.0, 52.0, 1.0, 24.0, 8.0, 10.0, 9.0, [],
        )]


class ModuleConnection(Connection):
    def __init__(self):
        self.cursor_instance = ModuleCursor()


def test_fetch_module_report_rows_is_time_bounded_and_keeps_batch_provenance():
    from datetime import datetime, timezone

    connection = ModuleConnection()
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)
    end = datetime(2026, 9, 1, tzinfo=timezone.utc)
    rows = fetch_module_report_rows(connection, start, end)
    assert rows[0]["module_id"] == "module-1"
    assert rows[0]["source_name"] == "lynk.csv"
    sql, params = connection.cursor_instance.executed
    assert "JOIN energy_analytics.lynk_import_batches" in sql
    assert params == (start, end)
