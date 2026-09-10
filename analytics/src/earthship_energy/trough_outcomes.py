"""Associate qualified trough measurements with immutable forecast origins."""
from datetime import date, datetime

from .advisory_store import validate_decision_record
from .series import local_day_bounds
from .trough_assessment import assess_trough_measurement


def assess_trough_decision(encoded_decision, *, observations, assessed_at, bank_epoch):
    """Return observational residuals, never a reward or publication-success claim.

    Origin must be a canonical stored decision, not reconstructed mutable daily
    state. Publication eligibility and frozen per-night selection are separate:
    a measured outcome alone must not update the seven-night diagnostic.
    """
    decision = validate_decision_record(encoded_decision)
    if bank_epoch.epoch_id != decision["bank_epoch"]:
        raise ValueError("decision and configured physical bank differ")
    if bank_epoch.start_local_date is None:
        raise ValueError("decision requires a dated physical bank")
    predicted = decision["inputs"]["trough_tomorrow_pct"]
    if not 0 <= predicted <= 100:
        raise ValueError("predicted SoC must be within 0..100")
    timezone_name = decision["site_timezone"]
    bank_start = local_day_bounds(bank_epoch.start_local_date, timezone_name)[0]
    bank_end = (local_day_bounds(bank_epoch.end_local_date_exclusive, timezone_name)[0]
                if bank_epoch.end_local_date_exclusive is not None else None)
    issued = datetime.fromisoformat(decision["issued_at"])
    if issued < bank_start or (bank_end is not None and issued >= bank_end):
        raise ValueError("decision issue time is outside its physical bank")
    if not isinstance(assessed_at, datetime) or assessed_at.utcoffset() is None or assessed_at < issued:
        raise ValueError("assessment must not precede the decision")
    measurement = assess_trough_measurement(
        prediction_day=date.fromisoformat(decision["prediction_day"]),
        site_timezone=timezone_name, assessed_at=assessed_at, observations=observations,
        epoch_start=bank_start, epoch_end=bank_end,
    )
    actual = measurement["min_soc_pct"]
    return {
        "schema_version": 1, "record_type": "advisory_trough_outcome",
        "decision_id": decision["decision_id"], "issued_at": decision["issued_at"],
        "bank_epoch": decision["bank_epoch"], "source_revision": decision["source_revision"],
        "policy_version": decision["policy_version"], "prediction_day": decision["prediction_day"],
        "predicted_soc_pct": predicted, "measurement": measurement,
        "signed_residual_pct_points": predicted-actual if actual is not None else None,
        "issued_before_target_start": issued < datetime.fromisoformat(measurement["window_start"]),
        "publication_status": "not_assessed", "action_attribution": "not_assessed",
        "bandit_eligible": False,
    }
