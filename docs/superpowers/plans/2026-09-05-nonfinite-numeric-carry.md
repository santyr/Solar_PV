# Nonfinite Numeric Carry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject nonfinite carry-in values before synthetic boundary creation or power clipping can mislabel them as healthy zero power.

**Architecture:** Apply the reader's existing in-window finite-value validation to its pre-window carry. Keep all temporal, interpolation, query and persistence behavior unchanged. This is the already approved all-algorithm validation scope, not a new estimator or freshness policy.

**Tech Stack:** Python3.12, pytest, existing earthship_energy reader/aggregation.

## Global Constraints

- Preserve everyChange plus restoreOnStartup.
- Preserve hardware controls, BMS counters, learned state, DM behavior and schedules; Task82 remains held.
- No production database/configuration writes, backfill or recomputation in this implementation task.
- Keep healthy unchanged finite carries, boundary timestamps, row ordering, query contracts and public signatures unchanged.
- Invalid selected numeric evidence raises the existing ValueError("series values must be finite"); never silently convert it to zero or skip it.
- No new dependencies or unrelated refactoring.

### Task 1: Equal finite validation for carries and rows

**Files:**
- Modify: `analytics/src/earthship_energy/reader.py`
- Test: `analytics/tests/test_reader.py`

**Interfaces:**
- Consumes `normalize_window_series(carry_in, rows, window_start, window_end)` and unchanged fetch wrapper.
- Produces the same list of timestamp/float points for valid evidence; nonfinite selected carry raises ValueError before normalization.

- [ ] **Step 1: Add the following regression tests first.** Add the aggregation import alongside reader imports, then append these tests. Existing START/END, Cursor and Connection fixtures are reused.

```python
from earthship_energy.aggregation import aggregate_power


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
```

- [ ] **Step 2: Run genuine RED.** From analytics, run
`PYTHONPATH=/home/sat/earthship-ui/openhab/scripts python3 -m pytest -q tests/test_reader.py`.
Expected17newfailures:12selected-carry,2power-path,3fetch-wrapper. Preserve relevant output.
The healthy/out-of-range controls and existing tests should pass.

- [ ] **Step 3: Implement only this replacement in normalize_window_series.**

```python
    if carry_in is not None and carry_in[0] < window_start:
        value = float(carry_in[1])
        if not isfinite(value):
            raise ValueError("series values must be finite")
        values[window_start] = value
```

- [ ] **Step 4: Verify GREEN.** Run the focused command again, then once run
`PYTHONPATH=/home/sat/earthship-ui/openhab/scripts python3 -m pytest -q` from analytics.
Run git diff --check and inspect that only the intended carry branch changed.
No database/runtime invocation or data mutation is allowed.

- [ ] **Step 5: Commit and report.** Stage only the reader and its test file;
commit `fix: reject nonfinite numeric carry before normalization`.
Write full report with exact RED/GREEN evidence and self-review to coordinator's
specified report path. Return short status, commit, tests, concerns. No merge/push.

## Coordinator integration gate

Task review and whole-branch review are required before integration. Verify a
read-only completed-day production snapshot remains identical to baseline before
changing the checkout used by scheduled analytics. Reverify merged tests and
remote SHA after approved push. No manual apply/backfill, schedule change or
learning reset. A finite-validation source fix is not a claim that all source-
health or broader outcome work is complete.
