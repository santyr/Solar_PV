"""Real subprocess + isolated PostgreSQL; never uses production credentials."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import os

import psycopg2
import pytest

from advisory_db_fixture import advisory_db
from advisory_windows import trough_window
from earthship_energy.advisory_store import AdvisoryStore
from earthship_energy.materialize import load_epoch_config
from earthship_energy.trough_publish import diagnostic_state
from earthship_energy.trough_runner import completed_target_bounds
from earthship_energy.trough_runtime import run_assessment_process
from test_advisory_store import decision, result
from test_trough_assessment import rows


def test_real_worker_success_replay_and_exact_reader_privileges(advisory_db):
    bank = next(epoch for epoch in load_epoch_config() if epoch.current_analytics)
    now = datetime.now(timezone.utc)
    _, end = completed_target_bounds(now, "America/Denver")
    day = end-timedelta(days=2)  # comfortably complete, including near 11:00
    window = trough_window(day, "America/Denver")
    cutoff = window.start-timedelta(days=1)
    with closing(advisory_db.connect_owner()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO energy_analytics.system_epochs (epoch_id, current_analytics) VALUES (%s,true)", (bank.epoch_id,))
            cursor.execute("CREATE TABLE public.items (itemid integer, itemname text)")
            cursor.execute("INSERT INTO public.items VALUES (901,'BMS_SOC_Evidence_JSON')")
            cursor.execute("CREATE TABLE public.item0901 (time timestamptz NOT NULL, value text NOT NULL)")
            cursor.execute("CREATE INDEX ON public.item0901(time)")
            cursor.executemany("INSERT INTO public.item0901 VALUES (%s,%s)", rows(window.start, int((window.end-window.start).total_seconds()), soc=75))
            cursor.execute("GRANT SELECT ON public.items, public.item0901 TO advisory_assessor")
    capture = AdvisoryStore(advisory_db.writer)
    origin = decision(prediction_day=day, bank_epoch=bank.epoch_id,
                      issued_at=window.start-timedelta(hours=1))
    capture.put_decision(origin)
    capture.put_result(result(origin, observed_at=window.start-timedelta(minutes=59)))
    env = dict(ADVISORY_ASSESS_ENABLED="1", ADVISORY_ASSESS_DSN=advisory_db.assessor,
        ADVISORY_ASSESS_BANK_EPOCH=bank.epoch_id, ADVISORY_ASSESS_CUTOVER_AT=cutoff.isoformat(),
        ADVISORY_ASSESS_TIMEZONE="America/Denver", PYTHONPATH=os.environ["PYTHONPATH"])
    first = run_assessment_process(env)
    assert first["status"] == "complete"
    assert first["processed"] == first["inserted"] == first["measured"] == 1
    assert first["projection"]["sample_count"] == 1
    assert diagnostic_state(first, now=datetime.now(timezone.utc)) == "10.0"
    second = run_assessment_process(env)
    assert second["status"] == "complete" and second["inserted"] == 0 and second["replayed"] == 1
    assert second["projection"]["samples"] == first["projection"]["samples"]

    # Read access is required to both exact sources; absence fails closed.
    for table in ("public.items", "public.item0901"):
        with closing(advisory_db.connect_owner()) as connection, connection:
            with connection.cursor() as cursor:
                cursor.execute(f"REVOKE SELECT ON {table} FROM advisory_assessor")
        try:
            assert run_assessment_process(env) == {"status":"unavailable", "reason":"assessment_process_failed"}
        finally:
            with closing(advisory_db.connect_owner()) as connection, connection:
                with connection.cursor() as cursor:
                    cursor.execute(f"GRANT SELECT ON {table} TO advisory_assessor")
    # Assessor cannot mutate raw evidence even though it can store outcomes.
    with closing(advisory_db.connect_assessor()) as connection:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM public.item0901")

    # A duplicate registry identity must not silently choose a telemetry table.
    with closing(advisory_db.connect_owner()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.items VALUES (902,'BMS_SOC_Evidence_JSON')")
    assert run_assessment_process(env) == {"status":"unavailable", "reason":"assessment_process_failed"}
    with closing(advisory_db.connect_owner()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM energy_analytics.advisory_trough_outcomes")
            assert cursor.fetchone()[0] == 1
