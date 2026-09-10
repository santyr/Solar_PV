from contextlib import closing
from datetime import date, timedelta

import pytest

from advisory_db_fixture import advisory_db
from advisory_windows import trough_window
from earthship_energy import advisory_store as module
from earthship_energy import trough_runner as runner
from test_trough_selection import candidate, save
from test_trough_outcome_store import BANK
from test_trough_assessment import rows as evidence_rows


@pytest.mark.parametrize("day", [date(2026, 1, 10), date(2026, 7, 10), date(2026, 3, 7), date(2026, 10, 31)])
def test_backlog_bounds_exclude_unfinished_night_at_0640(day):
    window = trough_window(day, "America/Denver")
    early_start, early_end = runner.completed_target_bounds(window.end-timedelta(hours=4, minutes=20), "America/Denver")
    start, end = runner.completed_target_bounds(window.end, "America/Denver")
    assert early_end == day
    assert end == day+timedelta(days=1)
    assert (early_end-early_start).days == (end-start).days == 30


def test_real_runner_pending_then_complete_then_retry(advisory_db, monkeypatch):
    day = date(2026, 9, 13)
    window = trough_window(day, "America/Denver")
    cutoff = window.start-timedelta(days=40)
    capture = module.AdvisoryStore(advisory_db.writer)
    assessor = module.AdvisoryStore(advisory_db.assessor)
    save(capture, candidate(day=day, hours=2))
    save(capture, candidate(day=day, hours=1))
    # Older unassessed origins must be reported, not silently counted as done.
    save(capture, candidate(day=day-timedelta(days=31)))
    with closing(advisory_db.connect_owner()) as owner, owner:
        with owner.cursor() as cursor:
            cursor.execute("CREATE TABLE public.item0900 (time timestamptz NOT NULL, value text NOT NULL)")
            cursor.execute("CREATE INDEX ON public.item0900(time)")
            cursor.executemany("INSERT INTO public.item0900 VALUES (%s,%s)", evidence_rows(window.start, 54000))
            cursor.execute("GRANT SELECT ON public.item0900 TO advisory_assessor")
    reads = []
    actual_reader = runner.fetch_freshness_observations
    def read(*args, **kwargs):
        assert kwargs["row_limit"] == 10001
        reads.append(1)
        return actual_reader(*args, **kwargs)
    monkeypatch.setattr(runner, "fetch_freshness_observations", read)
    def run(now):
        with closing(advisory_db.connect_assessor()) as connection:
            return runner.run_trough_assessments(connection, assessor, now=now,
                site_timezone="America/Denver", bank_epoch=BANK, cutover_at=cutoff, evidence_table="item0900")
    early = run(window.end-timedelta(hours=4, minutes=20))
    assert early["processed"] == 0 and early["projection"]["item_value"] is None
    assert reads == []
    complete = run(window.end)
    assert complete["status"] == "complete"
    assert complete["decisions"] == complete["processed"] == complete["inserted"] == complete["measured"] == 2
    assert complete["expired_unscored"] == 1
    assert complete["projection"]["sample_count"] == 1
    assert complete["projection"]["item_value"] == 10
    assert len(reads) == 1
    retry = run(window.end+timedelta(minutes=1))
    assert retry["inserted"] == 0 and retry["replayed"] == 2
    assert retry["projection"]["samples"] == complete["projection"]["samples"]


class FakeConnection:
    def __init__(self, count=0):
        self.count = count
        self.queries = []
    def set_session(self, **kwargs):
        assert kwargs == dict(isolation_level="READ COMMITTED", readonly=True, autocommit=False)
    def cursor(self): return self
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def execute(self, sql, params=None): self.queries.append((sql, params))
    def fetchone(self): return (0,)
    def fetchall(self): return [("not consumed",)] * self.count


def invoke(connection, **changes):
    window = trough_window(date(2026, 9, 13), "America/Denver")
    options = dict(now=window.end, site_timezone="America/Denver", bank_epoch=BANK,
                   cutover_at=window.start-timedelta(days=1), evidence_table="item0900")
    options.update(changes)
    return runner.run_trough_assessments(connection, object(), **options)


def test_decision_limit_refuses_truncated_processing():
    c = FakeConnection(1001)
    report = invoke(c)
    assert report["status"] == "decision_limit_exceeded"
    assert report["processed"] == 0
    assert c.queries[-1][1][-1] == 1001


def test_elapsed_budget_stops_before_further_queries_or_store_calls():
    ticks = iter([0, 31])
    c = FakeConnection()
    report = invoke(c, clock=lambda: next(ticks))
    assert report["status"] == "time_budget_exhausted"
    assert report["processed"] == 0
    assert len(c.queries) == 2  # timeout setting and bounded historical count


def test_final_read_overrun_does_not_return_a_publishable_projection():
    ticks = iter([0, 0, 0, 31])
    report = invoke(FakeConnection(), clock=lambda: next(ticks))
    assert report["status"] == "time_budget_exhausted"
    assert report["projection"] is None


@pytest.mark.parametrize("changes", [dict(budget_seconds=0), dict(budget_seconds=float("inf")),
                                    dict(budget_seconds=True), dict(evidence_table="item0900;DROP")])
def test_invalid_runtime_limits_fail_before_queries(changes):
    c = FakeConnection()
    with pytest.raises(ValueError): invoke(c, **changes)
    assert c.queries == []
