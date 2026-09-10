from contextlib import closing
from copy import deepcopy
from datetime import timedelta

import pytest

from advisory_db_fixture import advisory_db
from advisory_windows import trough_window
from earthship_energy import advisory_store as store_module
from earthship_energy.trough_selection import choose_trough_origin
from earthship_energy.trough_outcomes import assess_trough_decision
from earthship_energy.trough_projection import build_trough_projection, fetch_current_trough_outcomes
from test_trough_outcome_store import BANK
from test_trough_selection import candidate, save
from test_trough_assessment import rows as evidence_rows
from test_trough_outcomes import DAY


def pair(day=DAY, soc=75):
    window = trough_window(day, "America/Denver")
    decision, publication = candidate(day=day)
    selection = choose_trough_origin([(decision, publication)], prediction_day=day,
        site_timezone="America/Denver", bank_epoch=BANK.epoch_id,
        cutover_at=window.start-timedelta(days=30), now=window.end)
    outcome = assess_trough_decision(decision, observations=evidence_rows(window.start, int((window.end-window.start).total_seconds()), soc),
                                    assessed_at=window.end, bank_epoch=BANK)
    return selection, outcome


def project(rows, **changes):
    args = dict(bank_epoch=BANK.epoch_id, site_timezone="America/Denver",
                start_day=DAY, end_day=DAY+timedelta(days=11),
                now=trough_window(DAY+timedelta(days=10), "America/Denver").end)
    args.update(changes)
    return build_trough_projection(rows, **args)


def test_last_seven_distinct_verified_nights_are_rebuilt_not_appended():
    inputs = [pair(DAY+timedelta(days=n), soc=75+n) for n in range(10)]
    before = deepcopy(inputs)
    result = project(inputs)
    assert result["sample_count"] == 7
    assert result["mean_absolute_error_pct_points"] == result["item_value"] == 16
    assert result["samples"][0]["prediction_day"] == (DAY+timedelta(days=3)).isoformat()
    assert project(list(reversed(inputs))) == result
    assert inputs == before
    assert result["bandit_eligible"] is False


def test_no_outcome_or_insufficient_latest_revision_is_unavailable():
    selection, outcome = pair()
    assert project([])["item_value"] is None
    missing = project([(selection, None)])
    assert missing["missing_outcome_dates"] == [DAY.isoformat()]
    assert missing["sample_count"] == 0
    outcome["measurement"]["status"] = "insufficient_data"
    outcome["measurement"]["min_soc_pct"] = None
    outcome["signed_residual_pct_points"] = None
    result = project([(selection, outcome)])
    assert result["insufficient_dates"] == [DAY.isoformat()]
    assert result["item_value"] is None


def test_one_night_does_not_claim_seven_days():
    result = project([pair()])
    assert result["sample_count"] == 1
    assert len(result["samples"]) == 1
    assert result["item_value"] == 10


@pytest.mark.parametrize("field,value", [("coverage", 0.89), ("coverage", True),
                                         ("min_soc_pct", float("nan")), ("min_soc_pct", 101)])
def test_unqualified_measurement_cannot_enter_diagnostic(field, value):
    selection, outcome = pair()
    outcome["measurement"][field] = value
    with pytest.raises(ValueError):
        project([(selection, outcome)])


def test_duplicate_nights_and_mismatched_origins_are_rejected():
    row = pair()
    with pytest.raises(ValueError, match="duplicate"):
        project([row, row])
    other = pair()
    with pytest.raises(ValueError, match="frozen target"):
        project([(row[0], other[1])])


def test_incomplete_target_is_pending_and_date_span_is_bounded():
    row = pair()
    window = trough_window(DAY, "America/Denver")
    result = project([row], now=window.end-timedelta(hours=4))
    assert result["pending_dates"] == [DAY.isoformat()]
    assert result["item_value"] is None
    with pytest.raises(ValueError, match="1..30"):
        project([], end_day=DAY+timedelta(days=31))


def test_current_reader_never_falls_back_from_insufficient_revision(advisory_db):
    day = DAY+timedelta(days=20)
    window = trough_window(day, "America/Denver")
    decision, publication = candidate(day=day)
    capture = store_module.AdvisoryStore(advisory_db.writer)
    assessor = store_module.AdvisoryStore(advisory_db.assessor)
    save(capture, (decision, publication))
    cutoff = window.start-timedelta(days=1)
    assessor.freeze_trough_selection(prediction_day=day, site_timezone="America/Denver",
        bank_epoch=BANK.epoch_id, cutover_at=cutoff, now=window.end)
    assessor.put_trough_outcome(decision, observations=evidence_rows(window.start, 54000),
        assessed_at=window.end, bank_epoch=BANK)
    later = window.end+timedelta(hours=1)
    assessor.put_trough_outcome(decision, observations=[], assessed_at=later, bank_epoch=BANK)
    with closing(advisory_db.connect_assessor()) as connection:
        kwargs = dict(bank_epoch=BANK.epoch_id, start_day=day, end_day=day+timedelta(days=1), cutover_at=cutoff)
        original = fetch_current_trough_outcomes(connection, now=window.end, **kwargs)
        current = fetch_current_trough_outcomes(connection, now=later, **kwargs)
    assert original[0][1]["measurement"]["status"] == "measured"
    assert current[0][1]["measurement"]["status"] == "insufficient_data"
    report = build_trough_projection(current, bank_epoch=BANK.epoch_id, site_timezone="America/Denver",
                                     start_day=day, end_day=day+timedelta(days=1), now=later)
    assert report["sample_count"] == 0 and report["item_value"] is None
