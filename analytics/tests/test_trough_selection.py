from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import timedelta
import json

import psycopg2
import pytest

from advisory_db_fixture import advisory_db
from advisory_windows import trough_window
from earthship_energy import advisory_store as module
from earthship_energy.trough_selection import choose_trough_origin
from test_advisory_store import decision, result
from test_trough_outcomes import DAY, WINDOW

CUTOVER = WINDOW.start-timedelta(days=1)
OPTIONS = dict(prediction_day=DAY, site_timezone="America/Denver", bank_epoch="test_bank",
               cutover_at=CUTOVER, now=WINDOW.end)


def candidate(hours=1, delay=1, day=DAY, **changes):
    issued = trough_window(day, "America/Denver").start-timedelta(hours=hours)
    origin = decision(prediction_day=day, bank_epoch="test_bank", issued_at=issued)
    args = dict(observed_at=issued+timedelta(seconds=delay))
    args.update(changes)
    return origin, result(origin, **args)


def test_selects_first_accepted_publication_not_first_issue_or_input_order():
    early_issue_late_publish = candidate(hours=2, delay=3700)
    first_publish = candidate(hours=1)
    selected = choose_trough_origin([early_issue_late_publish, first_publish], **OPTIONS)
    assert selected["decision_id"] == json.loads(first_publish[0])["decision_id"]
    assert selected == choose_trough_origin([first_publish, early_issue_late_publish], **OPTIONS)


@pytest.mark.parametrize("changes", [dict(status="failed"), dict(status="unknown"),
                                    dict(target="Thermal_Advisory"),
                                    dict(kind="notification", target="deep_cycle_dm", status="attempted_reported_success"),
                                    dict(observed_at=WINDOW.end+timedelta(seconds=1))])
def test_only_observed_accepted_trough_publication_qualifies(changes):
    assert choose_trough_origin([candidate(**changes)], **OPTIONS)["status"] == "unavailable"


@pytest.mark.parametrize("hours", [0, -1, 25])
def test_late_or_pre_cutover_issue_is_ineligible(hours):
    assert choose_trough_origin([candidate(hours=hours)], **OPTIONS)["status"] == "unavailable"


def test_pending_does_not_consume_candidates_and_overflow_fails_closed():
    assert choose_trough_origin(None, **dict(OPTIONS, now=WINDOW.end-timedelta(hours=4)))["status"] == "pending"
    with pytest.raises(ValueError, match="limit"):
        choose_trough_origin([None]*1001, **OPTIONS)


def test_mismatched_parent_and_chronology_are_rejected():
    first, second = candidate(), candidate()
    with pytest.raises(ValueError, match="chronology"):
        choose_trough_origin([(first[0], second[1])], **OPTIONS)
    with pytest.raises(ValueError, match="chronology"):
        choose_trough_origin([candidate(delay=-1)], **OPTIONS)


def save(store, pair):
    store.put_decision(pair[0])
    store.put_result(pair[1])


def test_frozen_choice_survives_later_arrival_of_earlier_publication(advisory_db):
    capture = module.AdvisoryStore(advisory_db.writer)
    assessor = module.AdvisoryStore(advisory_db.assessor)
    first = candidate(hours=1)
    save(capture, first)
    frozen = assessor.freeze_trough_selection(**OPTIONS)
    save(capture, candidate(hours=2))
    assert assessor.freeze_trough_selection(**dict(OPTIONS, now=WINDOW.end+timedelta(hours=1))) == frozen
    assert frozen["decision_id"] == json.loads(first[0])["decision_id"]
    with pytest.raises(module.AdvisoryConflictError, match="configuration conflict"):
        assessor.freeze_trough_selection(**dict(OPTIONS, cutover_at=CUTOVER-timedelta(seconds=1)))


def test_no_candidate_does_not_freeze_unavailability(advisory_db):
    # Use a separate day so session-shared fixture selections cannot collide.
    options = dict(OPTIONS, prediction_day=DAY+timedelta(days=1), now=WINDOW.end+timedelta(days=1))
    assessor = module.AdvisoryStore(advisory_db.assessor)
    assert assessor.freeze_trough_selection(**options)["status"] == "unavailable"
    with closing(advisory_db.connect_assessor()) as c, c.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM energy_analytics.advisory_trough_selection WHERE prediction_day=%s",
                       (options["prediction_day"],))
        assert cursor.fetchone()[0] == 0


def test_concurrent_selection_returns_one_frozen_identity(advisory_db):
    day = DAY+timedelta(days=2)
    options = dict(OPTIONS, prediction_day=day, now=WINDOW.end+timedelta(days=2))
    save(module.AdvisoryStore(advisory_db.writer), candidate(day=day))
    assessor = module.AdvisoryStore(advisory_db.assessor)
    with ThreadPoolExecutor(max_workers=2) as executor:
        selected = list(executor.map(lambda _: assessor.freeze_trough_selection(**options), range(2)))
    assert selected[0] == selected[1]
    assert selected[0]["status"] == "selected"


@pytest.mark.parametrize("operation", ["UPDATE energy_analytics.advisory_trough_selection SET selected_at=selected_at",
                                       "DELETE FROM energy_analytics.advisory_trough_selection",
                                       "TRUNCATE energy_analytics.advisory_trough_selection"])
def test_selection_is_append_only(advisory_db, operation):
    with closing(advisory_db.connect_owner()) as c, c.cursor() as cursor:
        with pytest.raises(psycopg2.Error, match="append only"):
            cursor.execute(operation)


def test_capture_role_cannot_freeze_selection(advisory_db):
    with pytest.raises(module.AdvisoryStorageError):
        module.AdvisoryStore(advisory_db.writer).freeze_trough_selection(**OPTIONS)
