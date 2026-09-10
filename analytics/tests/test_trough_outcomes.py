from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json

import pytest

from advisory_windows import trough_window
from earthship_energy import advisory_store
from earthship_energy.materialize import load_epoch_config, select_epoch
from earthship_energy.trough_outcomes import assess_trough_decision
from test_advisory_store import decision
from test_trough_assessment import rows

DAY = date(2026, 9, 10)
EPOCH = select_epoch(load_epoch_config(), DAY)
WINDOW = trough_window(DAY, "America/Denver")


def origin(**changes):
    args = dict(prediction_day=DAY, bank_epoch=EPOCH.epoch_id,
                issued_at=WINDOW.start-timedelta(hours=1))
    args.update(changes)
    return decision(**args)


def assess(encoded=None, **changes):
    args = dict(observations=rows(WINDOW.start, 54000, soc=75),
                assessed_at=WINDOW.end, bank_epoch=EPOCH)
    args.update(changes)
    return assess_trough_decision(encoded or origin(), **args)


def test_residual_uses_exact_frozen_origin_and_is_not_a_reward():
    encoded = origin()
    output = assess(encoded)
    assert output["decision_id"] == json.loads(encoded)["decision_id"]
    assert output["predicted_soc_pct"] == 65
    assert output["measurement"]["min_soc_pct"] == 75
    assert output["signed_residual_pct_points"] == -10
    assert output["issued_before_target_start"] is True
    assert output["bandit_eligible"] is False
    assert output["publication_status"] == output["action_attribution"] == "not_assessed"


def test_pending_and_insufficient_outcomes_have_no_residual():
    pending = assess(assessed_at=WINDOW.end-timedelta(hours=4), observations=None)
    assert pending["measurement"]["status"] == "pending"
    assert pending["signed_residual_pct_points"] is None
    assert assess(observations=[])["signed_residual_pct_points"] is None


@pytest.mark.parametrize("issued", [WINDOW.start, WINDOW.start+timedelta(hours=1)])
def test_late_origin_cannot_claim_pre_window_issue(issued):
    result = assess(origin(issued_at=issued))
    assert result["issued_before_target_start"] is False
    assert result["bandit_eligible"] is False


def test_wrong_bank_or_time_cannot_attribute_an_outcome():
    with pytest.raises(ValueError, match="physical bank differ"):
        assess(bank_epoch=replace(EPOCH, epoch_id="another-bank"))
    with pytest.raises(ValueError, match="outside its physical bank"):
        assess(origin(issued_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    with pytest.raises(ValueError, match="precede the decision"):
        assess(assessed_at=WINDOW.start-timedelta(hours=2))


def test_mutated_target_or_extra_origin_field_is_rejected():
    payload = json.loads(origin())
    payload["targets"]["trough"]["end"] = WINDOW.start.isoformat()
    with pytest.raises(advisory_store.InvalidAdvisoryRecord):
        assess(json.dumps(payload))
    payload = json.loads(origin())
    payload["invented_success"] = True
    with pytest.raises(advisory_store.InvalidAdvisoryRecord):
        assess(json.dumps(payload))


def test_out_of_range_forecast_is_not_a_valid_soc_residual():
    payload = json.loads(origin())
    payload["inputs"]["trough_tomorrow_pct"] = 101.0
    with pytest.raises(ValueError, match="0..100"):
        assess(json.dumps(payload))
