from datetime import datetime, timedelta, timezone

import pytest

from earthship_energy.reader import fetch_numeric_series, normalize_window_series


UTC = timezone.utc
START = datetime(2026, 1, 1, tzinfo=UTC)
END = START + timedelta(hours=2)


def test_normalizes_carry_in_and_extends_every_change_state_to_window_end():
    result = normalize_window_series(
        (START - timedelta(days=1), 80.0),
        [(START + timedelta(hours=1), 90.0)],
        START,
        END,
    )
    assert result == [
        (START, 80.0),
        (START + timedelta(hours=1), 90.0),
        (END, 90.0),
    ]


def test_does_not_fabricate_series_without_any_value():
    assert normalize_window_series(None, [], START, END) == []


class Cursor:
    def __init__(self):
        self.query = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.query += 1
        assert "public.item0550" in sql

    def fetchone(self):
        return (START - timedelta(hours=1), "80")

    def fetchall(self):
        return [(START + timedelta(hours=1), "90")]


class Connection:
    def cursor(self):
        return Cursor()


def test_fetch_numeric_series_uses_validated_table_and_numeric_values():
    assert fetch_numeric_series(Connection(), "item0550", START, END) == [
        (START, 80.0),
        (START + timedelta(hours=1), 90.0),
        (END, 90.0),
    ]
    with pytest.raises(ValueError, match="table"):
        fetch_numeric_series(Connection(), "item0550; DROP TABLE x", START, END)
