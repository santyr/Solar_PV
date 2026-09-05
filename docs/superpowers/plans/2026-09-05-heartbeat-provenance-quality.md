# Historical Heartbeat Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent future-dated heartbeat reports, including reports hidden by synthetic carry boundaries, from granting historical daily source coverage.

**Architecture:** Add a dedicated reader returning original freshness observations, including the original pre-window carry timestamp. The quality assessor clips observation intervals to the requested window and validates heartbeat time against the original observation before granting coverage; daily analytics uses this reader exclusively for freshness companions. Existing text duration and numeric integration readers retain their contracts.

**Tech Stack:** Python >=3.12, existing psycopg2 cursor interface, pytest; no new dependencies.

## Global Constraints

- Keep JDBC everyChange and restoreOnStartup unchanged.
- Do not alter estimator gates, advisory thresholds, household controls, the forecast schedule, or counters.
- Task 82 remains on hold. Never send test DMs or save decrypted DM archives.
- Do not silently rewrite EFC accounting/history.
- No production database, service, OpenHAB, configuration, or learned-state writes; no backfill, reset, recomputation of stored reports, or deployment in this task.
- This plan covers only the reproduced Solar_PV historical heartbeat defect. Approval event 8668 authorizes the pending correction, not unrelated physical actions.
- Work in an isolated Solar_PV checkout using the worktree skill, preserve unrelated edits, and verify the base before editing. Baseline inspected: clean Solar_PV main `7f0b583`.

## Evidence and remaining scope

Read `/home/sat/earthship-ui/docs/operations/2026-09-05-outcome-source-health-preflight.md`, especially “Heartbeat provenance reproduction after storage integration”, and `/home/sat/earthship-ui/docs/superpowers/specs/2026-09-05-change-only-alerts-design.md`, especially “Remaining all-algorithm audit”. Retrieve private Hexmem context for `/home/sat/Solar_PV` before execution.

The existing `normalize_window_text_series` changes carry timestamps to window start. Existing `assess_source_quality` grants timestamp coverage from expiry without checking whether the report was future-dated when observed. Daily analytics uses both functions along the freshness path. Two synthetic reproductions already demonstrate full erroneous coverage: a report beyond the entire window, and a carry observed an hour earlier reporting window start.

One task contains the reader, assessor, daily wiring, and their tests because accepting any component independently would leave the production path vulnerable. New reader tuples mean `(original_observed_at, raw_value)`; they are not interpolation points. Original timestamps themselves are the provenance, so no new schema or third tuple field is necessary. Existing callers supplying valid clipped points still produce the same coverage, but historical timestamp callers must use original observations. End-boundary records grant no time in a half-open window. A final raw observation remains effective until the requested end, subject to timestamp expiry and subsequent observations.

Restart/epoch identification and explicit independent comms-fault intersection remain separate gates: this patch cannot prove them from a heartbeat alone. Existing status/numeric policies keep their present semantics. Weather field validation, weather age rounding, hourly learning, outcome capture, historical graphs/extrema, midnight counters, and broader rule inventory remain open. Passing these tests does not close the all-algorithm audit or justify changing existing EFC totals.

### Task 1: Preserve observation provenance throughout daily heartbeat assessment

**Files (relative to the isolated Solar_PV checkout):**

- Modify: `analytics/src/earthship_energy/reader.py` — add freshness-specific original-observation query.
- Modify: `analytics/src/earthship_energy/quality.py` — clip raw intervals and reject future reports at observation time.
- Modify: `analytics/src/earthship_energy/daily.py` — route freshness companions through the new reader.
- Create: `analytics/tests/test_heartbeat_provenance.py` — regression, query, and daily-path tests.
- Existing regression tests: `analytics/tests/test_reader.py`, `analytics/tests/test_quality.py`, `analytics/tests/test_daily.py`, plus the full analytics suite.

**Interfaces:**

- Consumes: existing DB-API connection/cursor; `ITEM_TABLE`; unchanged `assess_source_quality` keyword arguments and result dictionary.
- Produces: `fetch_freshness_observations(connection, table_name: str, window_start: datetime, window_end: datetime) -> list[tuple[datetime, str]]`, with original carry observation time, actual in-window records, no synthetic boundaries, and half-open `[start, end)` querying.
- Timestamp validity: aware reported timestamps must satisfy `reported_at <= observed_at`; comparison is by instant, including different explicit offsets. Invalid/missing timezone reports authorize zero time. Naive observation or window timestamps raise a descriptive `ValueError` rather than guessing a timezone. This does not reinterpret stored timestamps.

- [ ] **Step 1: Add the complete failing regression module.**

Create `analytics/tests/test_heartbeat_provenance.py` with:

```python
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
    (0, 0, 120),                 # ordinary heartbeat expires
    (0, 86400, 0),               # future report after the whole window
    (-3600, 0, 0),               # future at carry, seemingly valid at start
    (-3600, -3600, 0),           # normally expired carry
    (-60, -60, 60),              # valid sparse carry retains remaining life
    (-120, -120, 0),             # expiry exactly at start grants no time
    (480, 480, 120),             # expiry exactly at end
    (600, 600, 0),               # observation at end grants no time
    (700, 700, 0),               # later observations grant no time
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
    "NULL", "UNDEF", "bad", "2026-09-04T00:00:00",
    "2026-09-04T00:00:00+99:00",
])
def test_invalid_or_unzoned_report_grants_no_coverage(raw):
    assert assess([(START, raw)])["coverage"] == 0


def test_explicit_offset_is_compared_as_an_instant():
    assert assess([(START, "2026-09-03T18:00:00-06:00")])["coverage"] == 0.2


def test_later_invalid_observation_stops_previous_authorization():
    points = [
        (START, START.isoformat()),
        (START + timedelta(seconds=60), "UNDEF"),
        (START + timedelta(seconds=300),
         (START + timedelta(seconds=300)).isoformat()),
    ]
    result = assess(points)
    assert result["detail"]["valid_seconds"] == 180
    assert result["stale_intervals"] == 2


def test_no_observation_means_no_coverage():
    assert assess([])["coverage"] == 0


def test_naive_observation_is_rejected_without_timezone_guess():
    with pytest.raises(ValueError, match="timezone-aware"):
        assess([(START.replace(tzinfo=None), START.isoformat())])


@pytest.mark.parametrize("policy,value", [
    ("status_must_equal_OK", "ok"), ("numeric_must_equal_1", "1"),
])
def test_existing_status_and_numeric_companion_contracts(policy, value):
    points = [(START, value), (END, value)]
    assert assess(points, policy=policy, threshold=None)["coverage"] == 1.0
    assert assess([(START - timedelta(days=1), value)],
                  policy=policy, threshold=None)["coverage"] == 1.0


class ObservationCursor:
    def __init__(self, carry, rows):
        self.carry = carry
        self.rows = rows
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        assert "SELECT" in sql and "public.item9999" in sql
        self.queries.append((sql, params))

    def fetchone(self):
        return self.carry

    def fetchall(self):
        return self.rows


class ObservationConnection:
    def __init__(self, carry, rows):
        self.observations = ObservationCursor(carry, rows)

    def cursor(self):
        return self.observations


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
    assert reader.fetch_freshness_observations(connection, "item9999", START, END) == [
        carry, (START, "newer"),
    ]
    assert reader.fetch_freshness_observations(
        ObservationConnection(None, []), "item9999", START, END,
    ) == []


def test_reader_rejects_invalid_table_and_window_before_query():
    for table, end, message in [
        ("item9999; DROP TABLE x", END, "table"),
        ("item9999", START, "window_end"),
    ]:
        connection = ObservationConnection(None, [])
        with pytest.raises(ValueError, match=message):
            reader.fetch_freshness_observations(connection, table, START, end)
        assert connection.observations.queries == []


@pytest.mark.parametrize("start,end", [
    (START.replace(tzinfo=None), END.replace(tzinfo=None)),
    (START.replace(tzinfo=None), END),
    (START, END.replace(tzinfo=None)),
])
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


@pytest.mark.parametrize("case,expected_seconds", [
    ("future", 0), ("future_carry", 0), ("valid_carry", 60),
])
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
    resolved = [
        SimpleNamespace(
            canonical_name=name, table_name=f"item{index:04d}",
            freshness_table_name="item9999" if name == "battery.dc_power_w" else None,
        )
        for index, name in enumerate(sorted(daily.REQUIRED_DAILY), start=1)
    ]
    monkeypatch.setattr(daily, "fetch_numeric_series",
                        lambda _c, _t, left, right: [(left, 1.0), (right, 1.0)])
    monkeypatch.setattr(daily, "fetch_observation_stats", lambda *_: (0, None, None))
    monkeypatch.setattr(daily, "fetch_snow_state_as_of", lambda *_: "unknown")

    def forbidden_text(*args):
        raise AssertionError("freshness path must not use clipped text reader")

    monkeypatch.setattr(daily, "fetch_text_series", forbidden_text)
    result = daily.build_daily_snapshot(connection, config, resolved, day)
    quality = next(row for row in result["source_quality"]
                   if row["canonical_name"] == "battery.dc_power_w")
    assert quality["detail"]["valid_seconds"] == expected_seconds
    assert quality["coverage"] == expected_seconds / (end - start).total_seconds()
    assert quality["quality"] == "insufficient_data"
    assert result["mode"] == "read_only_dry_run"
    assert len(connection.observations.queries) == 2
```

- [ ] **Step 2: Verify the tests fail for the reproduced defects.**

From the isolated Solar_PV checkout root, use the known shared-builder import environment:

```bash
PYTHONPATH=/home/sat/earthship-ui/openhab/scripts:$PWD/analytics/src python3 -m pytest analytics/tests/test_heartbeat_provenance.py -q
```

Expected: failures for missing `reader.fetch_freshness_observations`, raw-observation coverage, and daily's forbidden text-reader call. Existing unchanged-contract tests may already pass. Do not install packages globally if dependencies are missing; use the repository's existing test environment or a disposable environment.

- [ ] **Step 3: Add the dedicated reader without changing existing readers.**

Append this complete function to `analytics/src/earthship_energy/reader.py`:

```python
def fetch_freshness_observations(
    connection,
    table_name: str,
    window_start: datetime,
    window_end: datetime,
) -> list[tuple[datetime, str]]:
    """Read original health observation times; never synthesize boundaries."""
    if not ITEM_TABLE.fullmatch(table_name):
        raise ValueError("invalid OpenHAB Item table name")
    for at in (window_start, window_end):
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("freshness window timestamps must be timezone-aware")
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")
    with connection.cursor() as cursor:
        cursor.execute(
            f"""SELECT time, value FROM public.{table_name}
                WHERE time < %s ORDER BY time DESC LIMIT 1""",
            (window_start,),
        )
        carry_in = cursor.fetchone()
        cursor.execute(
            f"""SELECT time, value FROM public.{table_name}
                WHERE time >= %s AND time < %s ORDER BY time""",
            (window_start, window_end),
        )
        rows = cursor.fetchall()
    observations = []
    if carry_in is not None and carry_in[0] < window_start:
        observations.append((carry_in[0], str(carry_in[1])))
    observations.extend(
        (at, str(raw)) for at, raw in rows if window_start <= at < window_end
    )
    return observations
```

- [ ] **Step 4: Correct interval assessment and wire the daily reader.**

In `quality.py`, replace the function docstring with:

```python
    """Measure coverage from (original_observed_at, raw_value) health evidence.

    The final observation lasts until window_end, subject to its policy.
    Historical callers must retain original times, especially for carry-in.
    """
```

Immediately before computing `window_seconds`, insert:

```python
    for at in (window_start, window_end):
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("quality window timestamps must be timezone-aware")
```

Replace the block beginning `ordered = sorted(freshness_points)` through the end of the existing loop, stopping before `coverage = ...`, with:

```python
    for observed_at, _ in freshness_points:
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("freshness observation timestamps must be timezone-aware")
    ordered = sorted(freshness_points, key=lambda point: point[0])
    for index, (observed_at, raw) in enumerate(ordered):
        next_at = ordered[index + 1][0] if index + 1 < len(ordered) else window_end
        interval_start = max(window_start, observed_at)
        interval_end = min(window_end, next_at)
        seconds = max(0.0, (interval_end - interval_start).total_seconds())
        if seconds == 0:
            continue
        authorized = 0.0
        if stale_policy == "timestamp_threshold":
            if stale_after_seconds is None:
                raise ValueError("timestamp_threshold requires stale_after_seconds")
            reported_at = _parse_aware_datetime(raw)
            if reported_at is not None and reported_at <= observed_at:
                expiry = reported_at + timedelta(seconds=stale_after_seconds)
                authorized = min(seconds, max(
                    0.0,
                    (min(interval_end, expiry) - interval_start).total_seconds(),
                ))
        elif stale_policy == "status_must_equal_OK":
            authorized = seconds if raw.strip().upper() == "OK" else 0.0
        elif stale_policy == "numeric_must_equal_1":
            try:
                authorized = seconds if float(raw) == 1.0 else 0.0
            except ValueError:
                authorized = 0.0
        else:
            raise ValueError(f"unsupported companion freshness policy: {stale_policy}")
        valid_seconds += authorized
        if authorized < seconds:
            stale_intervals += 1
```

Leave `_coverage_quality`, `_parse_aware_datetime`, the missing-companion result, and all returned result keys unchanged. `stale_intervals` remains the count of assessed intervals with a shortfall; missing leading evidence reduces coverage but is not invented as an observation.

In `daily.py`, add this entry inside the existing `.reader` import list:

```python
    fetch_freshness_observations,
```

Replace only the freshness assignment inside the `for resolved in resolved_sources` quality loop with:

```python
        freshness_points = (
            fetch_freshness_observations(connection, freshness_table, start, end)
            if freshness_table is not None else []
        )
```

Retain `fetch_text_series` for sunrise/sunset and switch-state duration consumers. No changes to `series.py`, source definitions, aggregation, SQL schema, writers, or EFC calculations.

- [ ] **Step 5: Run focused and complete regression checks.**

From the isolated Solar_PV checkout root, retain the shared-builder import path for both runs:

```bash
PYTHONPATH=/home/sat/earthship-ui/openhab/scripts:$PWD/analytics/src python3 -m pytest analytics/tests/test_heartbeat_provenance.py analytics/tests/test_reader.py analytics/tests/test_quality.py analytics/tests/test_daily.py -q
PYTHONPATH=/home/sat/earthship-ui/openhab/scripts:$PWD/analytics/src python3 -m pytest analytics/tests -q
```

Expected: all focused tests pass; the complete analytics suite passes. The verified pre-change full-suite baseline is 240 passing tests; the new module increases that count. This module uses in-memory fake cursors, while existing full-suite integration fixtures use disposable PostgreSQL instances and are expected to run, not be skipped by default. Preserve that isolation and never point tests at a production database. Report any actual environmental failure or skip explicitly rather than treating it as an expected baseline. Do not invoke the production daily CLI to validate this correction.

From the isolated checkout root:

```bash
git diff --check
git diff --stat
git diff -- analytics/src/earthship_energy/reader.py analytics/src/earthship_energy/quality.py analytics/src/earthship_energy/daily.py
git status --short
```

Expected: no whitespace errors and only the four intended task files changed. Review the added test file separately because an untracked file is not shown by `git diff`.

- [ ] **Step 6: Commit the tested slice, then independently review the immutable diff before integration.**

After Step 5 passes, commit only the tested task files to create the commit-based SDD review package:

```bash
git add analytics/src/earthship_energy/reader.py analytics/src/earthship_energy/quality.py analytics/src/earthship_energy/daily.py analytics/tests/test_heartbeat_provenance.py
git commit -m "fix: preserve heartbeat observation provenance in daily quality"
```

Use the requesting-code-review skill for independent review of that immutable commit diff, covering original provenance, report/observation ordering, half-open boundaries, daily wiring, and unchanged text/numeric contracts. Fix findings, repeat the affected tests, commit the fixes, and obtain review of the final commits. Independent review is mandatory before merge or deployment; it is not a prerequisite for creating the tested review commit. Record actual pass counts and skips in the implementation handoff; never report planned tests as executed.

Integration/push follow the parent workflow's existing authorization; this plan alone does not deploy anything. Rollback before integration is simply to leave the isolated commit unmerged. After integration, a normal revert restores code behavior; do not restore or rewrite production history as part of rollback.

## Self-review and handoff

Covered in Task 1: original carry provenance, future reports at both original and synthetic boundaries, valid/expired sparse carries, malformed/unzoned reports, exact start/end/expiry boundaries, later invalid observations, real daily reader wiring, read-only query scope, and unchanged general text/numeric contracts. No schema changes or resets are needed. There is no unresolved implementation choice for this bounded correction; the separate producer/epoch/outcome gates above remain unresolved project work and must be reported as such.
