from datetime import date, datetime, timedelta, timezone
import json

import pytest

from advisory_windows import trough_window
from earthship_energy.trough_assessment import assess_trough_measurement


def rows(start, seconds, soc=75):
    result = []
    for n in range(0, seconds, 60):
        at = start + timedelta(seconds=n)
        ms = int(at.timestamp()*1000)
        result.append((at, json.dumps(dict(version=1,
            streamEpoch="864142d5-99ee-4b7a-b5fc-e6a96e7274d8", recordedAt=ms,
            status="valid", reason="ok", observedAt=ms, scaleObservedAt=ms,
            validUntil=ms+120000, soc=soc))))
    return result


def assess(day=date(2026, 9, 10), **changes):
    window = trough_window(day, "America/Denver")
    args = dict(prediction_day=day, site_timezone="America/Denver", assessed_at=window.end,
                observations=rows(window.start, int((window.end-window.start).total_seconds())),
                epoch_start=window.start-timedelta(days=30))
    args.update(changes)
    return assess_trough_measurement(**args)


@pytest.mark.parametrize("day", [date(2026, 1, 10), date(2026, 7, 10),
                                 date(2026, 3, 7), date(2026, 10, 31)])
def test_0640_is_pending_and_exact_1100_boundary_is_complete(day):
    window = trough_window(day, "America/Denver")
    # No read/iteration of telemetry is allowed before completion.
    pending = assess(day, assessed_at=window.end-timedelta(hours=4, minutes=20), observations=None)
    assert pending["status"] == "pending"
    assert pending["coverage"] is pending["min_soc_pct"] is None
    complete = assess(day)
    assert complete["status"] == "measured"
    assert complete["coverage"] == 1
    assert complete["min_soc_pct"] == 75


def test_expiry_gap_cannot_be_scored_even_with_many_value_changes():
    window = trough_window(date(2026, 9, 10), "America/Denver")
    result = assess(observations=rows(window.start, 60, soc=20))
    assert result["status"] == "insufficient_data"
    assert result["min_soc_pct"] is None
    assert result["observed_min_soc_pct"] == 20
    assert result["covered_seconds"] == 120


def test_repeated_assessment_is_same_evidence_identity_and_changed_evidence_is_not():
    first = assess()
    later = assess(assessed_at=datetime(2026, 9, 12, tzinfo=timezone.utc))
    assert first["evidence_digest"] == later["evidence_digest"]
    window = trough_window(date(2026, 9, 10), "America/Denver")
    revised = assess(observations=rows(window.start, 54000, soc=74))
    assert revised["evidence_digest"] != first["evidence_digest"]


def test_duplicate_evidence_is_explicitly_unscorable():
    window = trough_window(date(2026, 9, 10), "America/Denver")
    evidence = rows(window.start, 54000)
    evidence.insert(1, evidence[0])
    result = assess(observations=evidence)
    assert result["status"] == "insufficient_data"
    assert result["reason"] == "ambiguous_evidence_sequence"
    assert result["min_soc_pct"] is None


def test_empty_history_and_limit_never_invent_measurements():
    assert assess(observations=[])["min_soc_pct"] is None
    assert assess(observations=[None]*10001)["reason"] == "observation_limit_exceeded"


@pytest.mark.parametrize("ratio,status", [(0.9, "measured"), (0.899, "insufficient_data")])
def test_ninety_percent_gate_is_not_relaxed(ratio, status):
    window = trough_window(date(2026, 9, 10), "America/Denver")
    # A physical bank end clips coverage precisely, including partial seconds.
    result = assess(epoch_end=window.start + (window.end-window.start)*ratio)
    assert result["coverage"] == pytest.approx(ratio)
    assert result["status"] == status


def test_oversize_record_and_naive_bank_are_not_authorizing():
    window = trough_window(date(2026, 9, 10), "America/Denver")
    assert assess(observations=[(window.start, 'x'*4097)])["reason"] == "evidence_record_limit_exceeded"
    with pytest.raises(ValueError, match="bank boundaries"):
        assess(epoch_start=datetime(2026, 1, 1))


def test_digest_covers_all_sequence_validation_inputs():
    window = trough_window(date(2026, 9, 10), "America/Denver")
    evidence = rows(window.start, 54000)
    first = assess(observations=evidence)
    future = rows(window.end, 60)[0]
    invalid = assess(observations=evidence + [future, future])
    assert invalid["reason"] == "ambiguous_evidence_sequence"
    assert invalid["evidence_digest"] != first["evidence_digest"]
