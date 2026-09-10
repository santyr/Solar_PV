"""Bounded observational SoC assessment; no OpenHAB or notification imports."""
from datetime import datetime, timedelta, timezone
import math
import time
from zoneinfo import ZoneInfo

from advisory_windows import trough_window
from .advisory_store import validate_decision_record
from .reader import ITEM_TABLE, fetch_freshness_observations
from .trough_assessment import MAX_OBSERVATIONS
from .trough_outcomes import assess_trough_decision
from .trough_projection import fetch_current_trough_outcomes, build_trough_projection

MAX_DECISIONS = 1000


def completed_target_bounds(now, site_timezone):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("runner time must be timezone-aware")
    today = now.astimezone(ZoneInfo(site_timezone)).date()
    newest = today-timedelta(days=1)
    if not trough_window(newest, site_timezone).is_complete(now):
        newest -= timedelta(days=1)
    return newest-timedelta(days=29), newest+timedelta(days=1)


def run_trough_assessments(connection, store, *, now, site_timezone, bank_epoch,
                           cutover_at, evidence_table, budget_seconds=30.0, clock=time.monotonic):
    """Process at most 30 completed days/1000 decisions and return a private report.

    Supply a dedicated connection: READ COMMITTED sees this run's store commits.
    Each read uses a 2s statement limit, store calls have their existing bounded
    timeouts, and time is checked between operations. The process owner must also
    impose a hard wall-clock timeout; this cooperative budget cannot preempt I/O.
    No retries, Item publications, learning updates or side-effect replay occur.
    """
    start_day, end_day = completed_target_bounds(now, site_timezone)
    if not isinstance(cutover_at, datetime) or cutover_at.utcoffset() is None or cutover_at > now:
        raise ValueError("valid past cutover required")
    if not ITEM_TABLE.fullmatch(evidence_table):
        raise ValueError("invalid evidence table")
    if type(budget_seconds) not in (int, float) or not math.isfinite(budget_seconds) or not 0 < budget_seconds <= 120:
        raise ValueError("runner budget must be positive and at most120seconds")
    started = clock()
    def expired():
        return clock()-started >= budget_seconds
    report = dict(status="complete", generated_at=now.astimezone(timezone.utc).isoformat(),
                  target_start_day=start_day.isoformat(), target_end_day_exclusive=end_day.isoformat(),
                  decisions=0, processed=0, inserted=0, replayed=0, measured=0,
                  insufficient=0, unpersistable=0, expired_unscored=0, projection=None,
                  causal_reward_proven=False)
    connection.set_session(isolation_level="READ COMMITTED", readonly=True, autocommit=False)
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL statement_timeout=2000")
        cursor.execute("""SELECT count(*) FROM energy_analytics.advisory_decisions d
            WHERE d.bank_epoch=%s AND d.issued_at >= %s AND d.issued_at <= %s
              AND d.payload->>'prediction_day' < %s
              AND NOT EXISTS (SELECT 1 FROM energy_analytics.advisory_trough_outcomes o
                              WHERE o.decision_id=d.decision_id)""",
            (bank_epoch.epoch_id, cutover_at, now, start_day.isoformat()))
        report["expired_unscored"] = cursor.fetchone()[0]
        if expired():
            report["status"] = "time_budget_exhausted"
            return report
        cursor.execute("""SELECT payload::text FROM energy_analytics.advisory_decisions
            WHERE bank_epoch=%s AND issued_at >= %s AND issued_at <= %s
              AND payload->>'site_timezone'=%s
              AND payload->>'prediction_day' >= %s AND payload->>'prediction_day' < %s
            ORDER BY payload->>'prediction_day' DESC, issued_at, decision_id LIMIT %s""",
            (bank_epoch.epoch_id, cutover_at, now, site_timezone, start_day.isoformat(), end_day.isoformat(), MAX_DECISIONS+1))
        decisions = [row[0] for row in cursor.fetchall()]
    report["decisions"] = len(decisions)
    if len(decisions) > MAX_DECISIONS:
        report["status"] = "decision_limit_exceeded"
        return report
    cache = {}
    frozen_days = set()
    for encoded in decisions:
        if expired():
            report["status"] = "time_budget_exhausted"
            return report
        decision = validate_decision_record(encoded)
        day = datetime.fromisoformat(decision["prediction_day"]).date()
        window = trough_window(day, site_timezone)
        if not window.is_complete(now):
            raise ValueError("query returned an incomplete target")
        if day not in cache:
            # SQL groups decisions by target day: retain only the current
            # night's bounded rows, not 30 nights of potentially large records.
            cache.clear()
            cache[day] = fetch_freshness_observations(connection, evidence_table,
                window.start-timedelta(seconds=120), window.end, row_limit=MAX_OBSERVATIONS+1)
        if expired():
            report["status"] = "time_budget_exhausted"
            return report
        outcome = assess_trough_decision(encoded, observations=cache[day], assessed_at=now, bank_epoch=bank_epoch)
        if outcome["measurement"]["evidence_digest"] is None:
            report["unpersistable"] += 1
        else:
            inserted = store.put_trough_outcome(encoded, observations=cache[day], assessed_at=now, bank_epoch=bank_epoch)
            report["inserted" if inserted else "replayed"] += 1
            report["measured" if outcome["measurement"]["status"] == "measured" else "insufficient"] += 1
        report["processed"] += 1
        if expired():
            report["status"] = "time_budget_exhausted"
            return report
        if day not in frozen_days:
            store.freeze_trough_selection(prediction_day=day, site_timezone=site_timezone,
                bank_epoch=bank_epoch.epoch_id, cutover_at=cutover_at, now=now)
            frozen_days.add(day)
    if expired():
        report["status"] = "time_budget_exhausted"
        return report
    current = fetch_current_trough_outcomes(connection, bank_epoch=bank_epoch.epoch_id,
        start_day=start_day, end_day=end_day, cutover_at=cutover_at, now=now)
    if expired():
        report["status"] = "time_budget_exhausted"
        return report
    report["projection"] = build_trough_projection(current, bank_epoch=bank_epoch.epoch_id,
        site_timezone=site_timezone, start_day=start_day, end_day=end_day, now=now)
    if expired():
        report.update(status="time_budget_exhausted", projection=None)
    return report
