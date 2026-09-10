"""Completed-night SoC measurement only; no scoring, learning, storage or actions."""
from datetime import date, datetime, timezone
from hashlib import sha256
import json

from advisory_windows import trough_window
from .bms_evidence import EvidenceSequenceError, build_soc_intervals

ASSESSMENT_VERSION = "atomic-soc-trough-v1"
MAX_OBSERVATIONS = 10000


def assess_trough_measurement(*, prediction_day: date, site_timezone: str,
                             assessed_at: datetime, observations,
                             epoch_start: datetime, epoch_end: datetime | None = None):
    """Qualify an entire target night, retaining incomplete/insufficient evidence.

    Caller supplies bounded original JDBC rows, including the reader's 120-second
    lookback and original carry. This is measurement evidence, not a reward or
    an attribution to an advisory. An origin-aware outcome layer must associate
    this result with an immutable decision before any diagnostic projection.
    """
    if not isinstance(assessed_at, datetime) or assessed_at.utcoffset() is None:
        raise ValueError("assessment time must be timezone-aware")
    now = assessed_at.astimezone(timezone.utc)
    window = trough_window(prediction_day, site_timezone)
    result = {
        "assessment_version": ASSESSMENT_VERSION,
        "prediction_day": prediction_day.isoformat(), "site_timezone": site_timezone,
        "assessed_at": now.isoformat(), "window_start": window.start.isoformat(),
        "window_end": window.end.isoformat(), "source": "BMS_SOC_Evidence_JSON",
        "status": "pending", "reason": "target_window_incomplete",
        "min_soc_pct": None, "observed_min_soc_pct": None,
        "observed_max_soc_pct": None, "coverage": None,
        "covered_seconds": None, "window_seconds": (window.end-window.start).total_seconds(),
        "record_count": None, "segment_count": None, "evidence_digest": None,
    }
    if not window.is_complete(now):
        # In particular, 06:40 must not even consume a partial-night sample list.
        return result
    result.update(status="insufficient_data", reason="insufficient_validated_coverage")
    if len(observations) > MAX_OBSERVATIONS:
        result["reason"] = "observation_limit_exceeded"
        return result
    for boundary in (epoch_start, epoch_end):
        if boundary is not None and (not isinstance(boundary, datetime) or boundary.utcoffset() is None):
            raise ValueError("bank boundaries must be timezone-aware")
    if epoch_start is None:
        raise ValueError("a physical bank start is required")
    digest_rows = []
    for persisted, raw in observations:
        if not isinstance(persisted, datetime) or persisted.utcoffset() is None:
            raise ValueError("persistence time must be timezone-aware")
        if not isinstance(raw, str):
            raise ValueError("raw evidence must be text")
        if len(raw) > 4096:
            result["reason"] = "evidence_record_limit_exceeded"
            return result
        # Include every row passed to sequence validation, even an irrelevant
        # post-window row: it can expose ambiguous ordering and change status.
        digest_rows.append((persisted.astimezone(timezone.utc).isoformat(), raw))
    digest = {"version": ASSESSMENT_VERSION, "window": [result["window_start"], result["window_end"]],
              "epoch_start": epoch_start.astimezone(timezone.utc).isoformat(),
              "epoch_end": epoch_end.astimezone(timezone.utc).isoformat() if epoch_end is not None else None,
              "rows": digest_rows}
    result["evidence_digest"] = sha256(json.dumps(digest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    result["record_count"] = sum(window.contains(at) for at, _ in observations)
    try:
        intervals = build_soc_intervals(observations, window.start, window.end,
                                       epoch_start=epoch_start, epoch_end=epoch_end)
    except EvidenceSequenceError:
        result.update(reason="ambiguous_evidence_sequence", coverage=0.0,
                      covered_seconds=0.0, segment_count=0)
        return result
    covered = sum((interval.end-interval.start).total_seconds() for interval in intervals)
    minimum = min((interval.soc for interval in intervals), default=None)
    result.update(coverage=covered/result["window_seconds"], covered_seconds=covered,
                  segment_count=len(intervals), observed_min_soc_pct=minimum,
                  observed_max_soc_pct=max((interval.soc for interval in intervals), default=None))
    if result["coverage"] >= 0.9 and minimum is not None:
        result.update(status="measured", reason=None, min_soc_pct=minimum)
    return result
