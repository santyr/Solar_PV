from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import timedelta
import json
import time

import psycopg2
import pytest

from advisory_db_fixture import advisory_db
from earthship_energy import advisory_store as module
from test_advisory_store import decision
from test_trough_outcomes import DAY, EPOCH, WINDOW
from test_trough_assessment import rows

BANK = replace(EPOCH, epoch_id="test_bank")


def origin():
    return decision(prediction_day=DAY, bank_epoch=BANK.epoch_id,
                    issued_at=WINDOW.start-timedelta(hours=1))


def put(store, encoded, **changes):
    args = dict(observations=rows(WINDOW.start, 54000), assessed_at=WINDOW.end, bank_epoch=BANK)
    args.update(changes)
    return store.put_trough_outcome(encoded, **args)


def test_outcome_retry_preserves_original_assessment_and_revision_history(advisory_db):
    encoded = origin()
    module.AdvisoryStore(advisory_db.writer).put_decision(encoded)
    store = module.AdvisoryStore(advisory_db.assessor)
    assert put(store, encoded) is True
    assert put(store, encoded, assessed_at=WINDOW.end+timedelta(hours=1)) is False
    assert put(store, encoded, observations=rows(WINDOW.start, 54000, soc=74),
               assessed_at=WINDOW.end+timedelta(hours=2)) is True
    with closing(advisory_db.connect_assessor()) as c, c.cursor() as cursor:
        cursor.execute("""SELECT assessed_at, payload FROM energy_analytics.advisory_trough_outcomes
                          WHERE decision_id=%s ORDER BY assessed_at, evidence_digest""",
                       (json.loads(encoded)["decision_id"],))
        saved = cursor.fetchall()
    assert len(saved) == 2
    assert saved[0][0] == WINDOW.end
    assert saved[0][1]["signed_residual_pct_points"] == -10
    assert saved[1][1]["signed_residual_pct_points"] == -9
    assert all(row[1]["bandit_eligible"] is False for row in saved)


def test_concurrent_replay_inserts_one_outcome(advisory_db):
    encoded = origin()
    module.AdvisoryStore(advisory_db.writer).put_decision(encoded)
    store = module.AdvisoryStore(advisory_db.assessor)
    with ThreadPoolExecutor(max_workers=2) as executor:
        result = list(executor.map(lambda _: put(store, encoded), range(2)))
    assert sorted(result) == [False, True]


def test_missing_or_conflicting_parent_is_not_attributed(advisory_db):
    encoded = origin()
    store = module.AdvisoryStore(advisory_db.assessor)
    with pytest.raises(module.AdvisoryStorageError):
        put(store, encoded)
    module.AdvisoryStore(advisory_db.writer).put_decision(encoded)
    assert put(store, encoded)
    changed = json.loads(encoded)
    changed["inputs"]["trough_tomorrow_pct"] = 66.0
    with pytest.raises(module.AdvisoryConflictError):
        put(store, json.dumps(changed))


def test_capture_and_assessment_roles_have_separate_writes(advisory_db):
    encoded = origin()
    capture = module.AdvisoryStore(advisory_db.writer)
    assessor = module.AdvisoryStore(advisory_db.assessor)
    capture.put_decision(encoded)
    with pytest.raises(module.AdvisoryStorageError):
        put(capture, encoded)
    with pytest.raises(module.AdvisoryStorageError):
        assessor.put_decision(origin())
    assert put(assessor, encoded)


def test_retry_rechecks_parent_fields_not_projected_into_outcome(advisory_db):
    encoded = origin()
    module.AdvisoryStore(advisory_db.writer).put_decision(encoded)
    store = module.AdvisoryStore(advisory_db.assessor)
    assert put(store, encoded)
    changed = json.loads(encoded)
    changed["advisory"] = "close_up_tomorrow"
    with pytest.raises(module.AdvisoryConflictError):
        put(store, json.dumps(changed))


@pytest.mark.parametrize("operation", ["UPDATE energy_analytics.advisory_trough_outcomes SET status=status",
                                       "DELETE FROM energy_analytics.advisory_trough_outcomes",
                                       "TRUNCATE energy_analytics.advisory_trough_outcomes"])
def test_outcomes_are_append_only_even_for_owner(advisory_db, operation):
    with closing(advisory_db.connect_owner()) as c, c.cursor() as cursor:
        with pytest.raises(psycopg2.Error, match="append only"):
            cursor.execute(operation)


def test_pending_outcome_does_not_open_a_connection(monkeypatch):
    store = module.AdvisoryStore("host=127.0.0.1 port=5432 dbname=test user=test password=test")
    def forbidden(*args, **kwargs):
        raise AssertionError("pending evidence must not connect")
    monkeypatch.setattr(module.psycopg2, "connect", forbidden)
    with pytest.raises(module.InvalidAdvisoryRecord, match="completed bounded"):
        put(store, origin(), assessed_at=WINDOW.end-timedelta(hours=4), observations=None)


def test_insufficient_completed_measurement_is_preserved_as_unscorable(advisory_db):
    encoded = origin()
    module.AdvisoryStore(advisory_db.writer).put_decision(encoded)
    assert put(module.AdvisoryStore(advisory_db.assessor), encoded, observations=[])
    with closing(advisory_db.connect_assessor()) as c, c.cursor() as cursor:
        cursor.execute("SELECT payload FROM energy_analytics.advisory_trough_outcomes WHERE decision_id=%s",
                       (json.loads(encoded)["decision_id"],))
        saved = cursor.fetchone()[0]
    assert saved["measurement"]["status"] == "insufficient_data"
    assert saved["signed_residual_pct_points"] is None


def test_lock_timeout_is_bounded_and_leaves_no_partial_outcome(advisory_db):
    encoded = origin()
    module.AdvisoryStore(advisory_db.writer).put_decision(encoded)
    store = module.AdvisoryStore(advisory_db.assessor)
    with closing(advisory_db.connect_owner()) as blocker:
        with blocker.cursor() as cursor:
            cursor.execute("LOCK TABLE energy_analytics.advisory_trough_outcomes IN ACCESS EXCLUSIVE MODE")
        started = time.monotonic()
        with pytest.raises(module.AdvisoryStorageError, match="outcome storage unavailable"):
            put(store, encoded)
        assert time.monotonic()-started < 5
        blocker.rollback()
    with closing(advisory_db.connect_assessor()) as c, c.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM energy_analytics.advisory_trough_outcomes WHERE decision_id=%s",
                       (json.loads(encoded)["decision_id"],))
        assert cursor.fetchone()[0] == 0
    assert put(store, encoded)  # only an explicit later invocation retries
