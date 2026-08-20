from datetime import datetime, timedelta, timezone

import pytest

from earthship_energy.reader import (
    datetime_state_for_local_date,
    fetch_numeric_series,
    fetch_text_series,
    normalize_window_series,
    normalize_window_text_series,
    state_duration_seconds,
)


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


def test_text_series_supports_datetime_selection_and_state_duration():
    rows = normalize_window_text_series(
        (START - timedelta(hours=1), "OFF"),
        [(START + timedelta(minutes=30), "ON"), (START + timedelta(hours=1), "OFF")],
        START,
        END,
    )
    assert rows == [
        (START, "OFF"),
        (START + timedelta(minutes=30), "ON"),
        (START + timedelta(hours=1), "OFF"),
        (END, "OFF"),
    ]
    assert state_duration_seconds(rows, "ON") == 1800
    astro = [
        (START, "2026-01-01T06:30:00-0700"),
        (END, "2026-01-02T06:30:00-0700"),
    ]
    assert datetime_state_for_local_date(
        astro, __import__("datetime").date(2026, 1, 1), "America/Denver"
    ).isoformat() == "2026-01-01T06:30:00-07:00"


def test_fetch_text_series_uses_same_bounded_validated_query():
    class TextCursor(Cursor):
        def fetchone(self):
            return (START - timedelta(hours=1), "OFF")

        def fetchall(self):
            return [(START + timedelta(hours=1), "ON")]

    class TextConnection:
        def cursor(self):
            return TextCursor()

    assert fetch_text_series(TextConnection(), "item0550", START, END) == [
        (START, "OFF"),
        (START + timedelta(hours=1), "ON"),
        (END, "ON"),
    ]
