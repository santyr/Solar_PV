from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from earthship_energy import daily, reader
from earthship_energy.config import load_source_config
from earthship_energy.quality import assess_source_quality
from earthship_energy.series import integrate_trapezoid, local_day_bounds


START = datetime(2026, 9, 4, tzinfo=timezone.utc)
END = START + timedelta(minutes=10)


def assess(points, *, policy="timestamp_threshold", threshold=120):
    return assess_source_quality(
        canonical_name="battery.dc_power_w", row_count=0,
        first_at=None, last_at=None, window_start=START, window_end=END,
        stale_policy=policy, stale_after_seconds=threshold,
        freshness_item="Schneider_DCData_LastUpdate",
        freshness_points=points,
    )


@pytest.mark.parametrize("offset,reported_offset,seconds", [
    (0, 0, 120), (0, 86400, 0), (-3600, 0, 0), (-3600, -3600, 0),
    (-60, -60, 60), (-120, -120, 0), (480, 480, 120),
    (600, 600, 0), (700, 700, 0),
])
def test_heartbeat_coverage_uses_original_observation(offset, reported_offset, seconds):
    result = assess([(
        START + timedelta(seconds=offset),
        (START + timedelta(seconds=reported_offset)).isoformat(),
    )])
    assert result["detail"]["valid_seconds"] == seconds
    assert result["coverage"] == seconds / 600
    assert result["quality"] == "insufficient_data"


def test_valid_sparse_carry_can_cover_whole_window_with_approved_allowance():
    observed = START - timedelta(seconds=60)
    result = assess([(observed, observed.isoformat())], threshold=720)
    assert result["coverage"] == 1.0
    assert result["quality"] == "ok"


@pytest.mark.parametrize("raw", [
    "NULL", "UNDEF", "bad", "2026-09-04T00:00:00", "2026-09-04T00:00:00+99:00",
])
def test_invalid_or_unzoned_report_grants_no_coverage(raw):
    assert assess([(START, raw)])["coverage"] == 0


def test_explicit_offset_is_compared_as_an_instant():
    assert assess([(START, "2026-09-03T18:00:00-06:00")])["coverage"] == 0.2


def test_later_invalid_observation_stops_previous_authorization():
    points = [
        (START, START.isoformat()), (START + timedelta(seconds=60), "UNDEF"),
        (START + timedelta(seconds=300), (START + timedelta(seconds=300)).isoformat()),
    ]
    result = assess(points)
    assert result["detail"]["valid_seconds"] == 180
    assert result["stale_intervals"] == 2


@pytest.mark.parametrize("points,expected_seconds", [
    ([(START, "UNDEF"), (START, START.isoformat())], 120),
    ([(START, START.isoformat()), (START, "UNDEF")], 0),
])
def test_equal_timestamp_observations_preserve_input_order(points, expected_seconds):
    assert assess(points)["detail"]["valid_seconds"] == expected_seconds


def test_no_observation_means_no_coverage():
    assert assess([])["coverage"] == 0


def test_naive_observation_is_rejected_without_timezone_guess():
    with pytest.raises(ValueError, match="timezone-aware"):
        assess([(START.replace(tzinfo=None), START.isoformat())])


@pytest.mark.parametrize("points", [
    [(START, START.isoformat()), (START.replace(tzinfo=None), START.isoformat())],
    [(START.replace(tzinfo=None), START.isoformat()), (START, START.isoformat())],
])
def test_mixed_aware_and_naive_observations_are_rejected_before_sort(points):
    with pytest.raises(ValueError, match="freshness observation timestamps must be timezone-aware"):
        assess(points)


@pytest.mark.parametrize("policy,value", [("status_must_equal_OK", "ok"), ("numeric_must_equal_1", "1")])
def test_existing_status_and_numeric_companion_contracts(policy, value):
    points = [(START, value), (END, value)]
    assert assess(points, policy=policy, threshold=None)["coverage"] == 1.0
    assert assess([(START - timedelta(days=1), value)], policy=policy, threshold=None)["coverage"] == 1.0


class ObservationCursor:
    def __init__(self, carry, rows):
        self.carry, self.rows, self.queries = carry, rows, []

    def __enter__(self): return self
    def __exit__(self, *args): return False

    def execute(self, sql, params):
        assert "SELECT" in sql and "public.item9999" in sql
        self.queries.append((sql, params))

    def fetchone(self): return self.carry
    def fetchall(self): return self.rows


class ObservationConnection:
    def __init__(self, carry, rows): self.observations = ObservationCursor(carry, rows)
    def cursor(self): return self.observations


def test_reader_retains_original_carry_and_half_open_rows_without_sentinels():
    carry = (START - timedelta(hours=1), START.isoformat())
    later = (START + timedelta(seconds=300), "UNDEF")
    connection = ObservationConnection(carry, [later, (END, "OK")])
    points = reader.fetch_freshness_observations(connection, "item9999", START, END)
    assert points == [carry, later]
    assert assess(points)["coverage"] == 0
    queries = connection.observations.queries
    assert len(queries) == 2
    assert "time < %s" in queries[0][0] and "LIMIT 1" in queries[0][0]
    assert queries[0][1] == (START,)
    assert "time >= %s AND time < %s" in queries[1][0]
    assert queries[1][1] == (START, END)


def test_reader_keeps_real_start_record_and_handles_empty_history():
    carry = (START - timedelta(seconds=60), "older")
    connection = ObservationConnection(carry, [(START, "newer")])
    assert reader.fetch_freshness_observations(connection, "item9999", START, END) == [carry, (START, "newer")]
    assert reader.fetch_freshness_observations(ObservationConnection(None, []), "item9999", START, END) == []


def test_reader_rejects_invalid_table_and_window_before_query():
    for table, end, message in [("item9999; DROP TABLE x", END, "table"), ("item9999", START, "window_end")]:
        connection = ObservationConnection(None, [])
        with pytest.raises(ValueError, match=message):
            reader.fetch_freshness_observations(connection, table, START, end)
        assert connection.observations.queries == []


@pytest.mark.parametrize("start,end", [(START.replace(tzinfo=None), END.replace(tzinfo=None)), (START.replace(tzinfo=None), END), (START, END.replace(tzinfo=None))])
def test_reader_rejects_naive_or_mixed_window_before_query(start, end):
    connection = ObservationConnection(None, [])
    with pytest.raises(ValueError, match="timezone-aware"):
        reader.fetch_freshness_observations(connection, "item9999", start, end)
    assert connection.observations.queries == []


def test_general_text_and_numeric_contracts_remain_clipped():
    carry_at = START - timedelta(days=1)
    text = reader.normalize_window_text_series((carry_at, "ON"), [], START, END)
    assert text == [(START, "ON"), (END, "ON")]
    assert reader.state_duration_seconds(text, "ON") == 600
    numeric = reader.normalize_window_series((carry_at, 60), [], START, END)
    assert numeric == [(START, 60.0), (END, 60.0)]
    integral = integrate_trapezoid(numeric, END - START)
    assert integral.value_hours == 10
    assert integral.covered_seconds == 600


@pytest.mark.parametrize("case,expected_seconds", [("future", 0), ("future_carry", 0), ("valid_carry", 60)])
def test_daily_uses_original_observations_through_real_reader(monkeypatch, case, expected_seconds):
    config = load_source_config()
    day = date(2026, 9, 4)
    start, end = local_day_bounds(day, config.timezone)
    if case == "future":
        carry, rows = None, [(start, (end + timedelta(days=1)).isoformat())]
    elif case == "future_carry":
        carry, rows = (start - timedelta(hours=1), start.isoformat()), []
    else:
        observed = start - timedelta(seconds=60)
        carry, rows = (observed, observed.isoformat()), []
    connection = ObservationConnection(carry, rows)
    resolved = [SimpleNamespace(canonical_name=name, table_name=f"item{index:04d}", freshness_table_name="item9999" if name == "battery.dc_power_w" else None) for index, name in enumerate(sorted(daily.REQUIRED_DAILY), start=1)]
    monkeypatch.setattr(daily, "fetch_numeric_series", lambda _c, _t, left, right: [(left, 1.0), (right, 1.0)])
    monkeypatch.setattr(daily, "fetch_observation_stats", lambda *_: (0, None, None))
    monkeypatch.setattr(daily, "fetch_snow_state_as_of", lambda *_: "unknown")

    def forbidden_text(*args):
        raise AssertionError("freshness path must not use clipped text reader")

    monkeypatch.setattr(daily, "fetch_text_series", forbidden_text)
    from earthship_energy.materialize import load_epoch_config, select_epoch
    result = daily.build_daily_snapshot(connection, config, resolved, day,
                                        bank_epoch=select_epoch(load_epoch_config(), day))
    quality = next(row for row in result["source_quality"] if row["canonical_name"] == "battery.dc_power_w")
    assert quality["detail"]["valid_seconds"] == expected_seconds
    assert quality["coverage"] == expected_seconds / (end - start).total_seconds()
    assert quality["quality"] == "insufficient_data"
    assert result["mode"] == "read_only_dry_run"
    assert len(connection.observations.queries) == 2
