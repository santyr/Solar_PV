"""Read current committed revisions and rebuild the observational diagnostic."""
from datetime import date, datetime, timezone
import math

from advisory_windows import trough_window
from .trough_assessment import ASSESSMENT_VERSION
from .trough_selection import SELECTION_VERSION


def _bounds(start_day, end_day, now):
    if any(not isinstance(day, date) or isinstance(day, datetime) for day in (start_day, end_day)):
        raise ValueError("explicit date bounds required")
    if not 0 < (end_day-start_day).days <= 30:
        raise ValueError("projection must cover 1..30 target days")
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("projection time must be timezone-aware")


def fetch_current_trough_outcomes(connection, *, bank_epoch, start_day, end_day,
                                  cutover_at, now):
    """At most 30 frozen nights; select newest revision BEFORE checking quality."""
    _bounds(start_day, end_day, now)
    if not isinstance(cutover_at, datetime) or cutover_at.utcoffset() is None:
        raise ValueError("cutover time must be timezone-aware")
    with connection.cursor() as cursor:
        cursor.execute("""SELECT s.payload, latest.payload
            FROM energy_analytics.advisory_trough_selection s
            LEFT JOIN LATERAL (
                SELECT o.payload FROM energy_analytics.advisory_trough_outcomes o
                WHERE o.decision_id=s.decision_id AND o.assessment_version=%s
                  AND o.assessed_at <= %s
                ORDER BY o.assessed_at DESC, o.evidence_digest DESC LIMIT 1
            ) latest ON true
            WHERE s.bank_epoch=%s AND s.selection_version=%s
              AND s.prediction_day >= %s AND s.prediction_day < %s
              AND s.cutover_at=%s AND s.selected_at <= %s
            ORDER BY s.prediction_day LIMIT 31""",
            (ASSESSMENT_VERSION, now, bank_epoch, SELECTION_VERSION,
             start_day, end_day, cutover_at, now))
        rows = cursor.fetchall()
    if len(rows) > 30:
        raise ValueError("projection row limit exceeded")
    return rows


def build_trough_projection(rows, *, bank_epoch, site_timezone, start_day, end_day, now):
    """One current revision per frozen night; no append or consumption marker."""
    _bounds(start_day, end_day, now)
    if len(rows) > 30:
        raise ValueError("projection row limit exceeded")
    seen = set()
    verified = []
    missing, insufficient, pending = [], [], []
    for selection, outcome in rows:
        day = date.fromisoformat(selection["prediction_day"])
        if (day in seen or not start_day <= day < end_day
            or selection["bank_epoch"] != bank_epoch or selection["site_timezone"] != site_timezone
            or selection["selection_version"] != SELECTION_VERSION or selection["status"] != "selected"):
            raise ValueError("invalid or duplicate frozen night")
        seen.add(day)
        window = trough_window(day, site_timezone)
        if not window.is_complete(now):
            pending.append(day.isoformat())
            continue
        if outcome is None:
            missing.append(day.isoformat())
            continue
        m = outcome["measurement"]
        if (outcome["decision_id"] != selection["decision_id"]
            or outcome["prediction_day"] != day.isoformat() or outcome["bank_epoch"] != bank_epoch
            or outcome["bandit_eligible"] is not False or outcome["issued_before_target_start"] is not True
            or m["assessment_version"] != ASSESSMENT_VERSION
            or m["site_timezone"] != site_timezone
            or datetime.fromisoformat(m["window_start"]) != window.start
            or datetime.fromisoformat(m["window_end"]) != window.end):
            raise ValueError("outcome does not match frozen target")
        assessed = datetime.fromisoformat(m["assessed_at"])
        if assessed.utcoffset() is None or not window.end <= assessed <= now:
            raise ValueError("outcome assessment is outside completed evidence time")
        if m["status"] == "insufficient_data":
            insufficient.append(day.isoformat())
            continue
        if m["status"] != "measured":
            raise ValueError("unknown completed outcome status")
        coverage, actual, predicted, residual = (m["coverage"], m["min_soc_pct"],
                                                  outcome["predicted_soc_pct"], outcome["signed_residual_pct_points"])
        if any(type(value) not in (int, float) or not math.isfinite(value)
               for value in (coverage, actual, predicted, residual)):
            raise ValueError("nonfinite outcome measurement")
        if not (0.9 <= coverage <= 1 and 0 <= actual <= 100 and 0 <= predicted <= 100
                and math.isclose(residual, predicted-actual, rel_tol=0, abs_tol=1e-9)):
            raise ValueError("inconsistent qualified outcome")
        verified.append(dict(prediction_day=day.isoformat(), decision_id=selection["decision_id"],
                             evidence_digest=m["evidence_digest"], coverage=coverage,
                             signed_residual_pct_points=residual))
    samples = sorted(verified, key=lambda row: row["prediction_day"])[-7:]
    mean = sum(abs(row["signed_residual_pct_points"]) for row in samples)/len(samples) if samples else None
    return dict(schema_version=1, diagnostic_version=SELECTION_VERSION,
                assessment_version=ASSESSMENT_VERSION, bank_epoch=bank_epoch,
                generated_at=now.astimezone(timezone.utc).isoformat(),
                target_start_day=start_day.isoformat(), target_end_day_exclusive=end_day.isoformat(),
                status="available" if samples else "unavailable", sample_count=len(samples),
                mean_absolute_error_pct_points=mean, item_value=round(mean, 1) if mean is not None else None,
                samples=samples, missing_outcome_dates=sorted(missing),
                insufficient_dates=sorted(insufficient), pending_dates=sorted(pending), bandit_eligible=False)
