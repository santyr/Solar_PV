from datetime import datetime, timedelta, timezone

import pytest

from earthship_energy.aggregation import aggregate_power
from earthship_energy.reader import (
    datetime_state_for_local_date,
    fetch_numeric_series,
    fetch_observation_stats,
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


def test_fetch_observation_stats_counts_only_raw_rows_in_window():
    class StatsCursor(Cursor):
        def fetchone(self):
            return (2, START + timedelta(minutes=1), END - timedelta(minutes=1))

    class StatsConnection:
        def cursor(self):
            return StatsCursor()

    assert fetch_observation_stats(
        StatsConnection(), "item0550", START, END
    ) == (2, START + timedelta(minutes=1), END - timedelta(minutes=1))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), "NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("rows", [[], [(START, 90.0)]])
def test_rejects_nonfinite_selected_carry_before_normalization(value, rows):
    with pytest.raises(ValueError, match="^series values must be finite$"):
        normalize_window_series((START - timedelta(minutes=1), value), rows, START, END)


@pytest.mark.parametrize("value", [float("nan"), float("-inf")])
def test_nonfinite_carry_cannot_be_clipped_to_healthy_zero_power(value):
    with pytest.raises(ValueError, match="^series values must be finite$"):
        points = normalize_window_series((START - timedelta(minutes=1), value), [], START, END)
        aggregate_power(points, START, END, max_gap=END - START)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_fetch_numeric_series_rejects_nonfinite_carry(value):
    class NonfiniteCursor(Cursor):
        def fetchone(self):
            return (START - timedelta(minutes=1), value)

    class NonfiniteConnection:
        def cursor(self):
            return NonfiniteCursor()

    with pytest.raises(ValueError, match="^series values must be finite$"):
        fetch_numeric_series(NonfiniteConnection(), "item0550", START, END)


@pytest.mark.parametrize("value", [0, -10.0, "80.5"])
def test_finite_unchanged_carry_still_covers_window(value):
    assert normalize_window_series((START - timedelta(days=2), value), [], START, END) == [
        (START, float(value)), (END, float(value))
    ]


def test_unused_out_of_range_carry_is_not_interpreted_as_evidence():
    assert normalize_window_series((END, float("nan")), [(START, 80.0)], START, END) == [
        (START, 80.0), (END, 80.0)
    ]
