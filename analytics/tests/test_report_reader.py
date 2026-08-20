from datetime import date

from earthship_energy.report_reader import fetch_daily_report_rows


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
        return [(date(2026, 8, 1), 80.0, True, 1.0, 0.5, .04, "ok", 7.0, 5.0)]


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
    sql, params = connection.cursor_instance.executed
    assert "JOIN energy_analytics.daily_pv" in sql
    assert params == ("discover", date(2026, 8, 1), date(2026, 9, 1))
