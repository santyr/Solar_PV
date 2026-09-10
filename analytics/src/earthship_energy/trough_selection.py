"""Deterministic candidate selection; persistence must freeze the first choice."""
from datetime import datetime, timezone

from advisory_windows import trough_window
from .advisory_store import validate_decision_record, validate_result_record

SELECTION_VERSION = "completed-night-v1"
MAX_CANDIDATES = 1000


def choose_trough_origin(candidates, *, prediction_day, site_timezone, bank_epoch,
                         cutover_at, now):
    for stamp in (cutover_at, now):
        if not isinstance(stamp, datetime) or stamp.utcoffset() is None:
            raise ValueError("selection timestamps must be timezone-aware")
    window = trough_window(prediction_day, site_timezone)
    base = dict(selection_version=SELECTION_VERSION, prediction_day=prediction_day.isoformat(),
                site_timezone=site_timezone, bank_epoch=bank_epoch,
                cutover_at=cutover_at.astimezone(timezone.utc).isoformat())
    if not window.is_complete(now):
        return dict(base, status="pending", reason="target_window_incomplete")
    if len(candidates) > MAX_CANDIDATES:
        raise ValueError("trough candidate limit exceeded")
    eligible = []
    for encoded_decision, encoded_result in candidates:
        decision = validate_decision_record(encoded_decision)
        result = validate_result_record(encoded_result)
        issued = datetime.fromisoformat(decision["issued_at"])
        published = datetime.fromisoformat(result["observed_at"])
        if result["decision_id"] != decision["decision_id"] or published < issued:
            raise ValueError("publication does not belong to the decision chronology")
        if (decision["prediction_day"] != prediction_day.isoformat()
            or decision["site_timezone"] != site_timezone or decision["bank_epoch"] != bank_epoch
            or not cutover_at <= issued < window.start or published > now
            or result["kind"] != "publication" or result["target"] != "Predicted_SoC_Trough_Tomorrow"
            or result["status"] != "accepted"):
            continue
        eligible.append((published, issued, decision["decision_id"], result["result_id"]))
    if not eligible:
        return dict(base, status="unavailable", reason="no_accepted_pre_window_origin")
    published, issued, decision_id, result_id = min(eligible)
    return dict(base, status="selected", reason=None, decision_id=decision_id,
                publication_result_id=result_id, issued_at=issued.isoformat(),
                publication_observed_at=published.isoformat())
