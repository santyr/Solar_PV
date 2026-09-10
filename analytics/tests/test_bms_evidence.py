from datetime import datetime, timedelta, timezone
import json
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from unittest.mock import patch

from earthship_energy.bms_evidence import EvidenceSequenceError, build_soc_intervals, parse_evidence, soc_at
from earthship_energy.reader import fetch_bms_soc_intervals

BASE = datetime(2026, 9, 10, tzinfo=timezone.utc)
EPOCH = str(UUID(int=1))
OTHER = str(UUID(int=2))


def at(seconds):
    return BASE + timedelta(seconds=seconds)


def ms(seconds):
    return int(at(seconds).timestamp()*1000)


def record(second=0, **changes):
    body = dict(version=1, streamEpoch=EPOCH, recordedAt=ms(second), status='valid',
                reason='ok', observedAt=ms(second), scaleObservedAt=ms(second),
                validUntil=ms(second+120), soc=50)
    body.update(changes)
    return json.dumps(body)


def unavailable(second):
    return record(second, status='unavailable', reason='input_stale', observedAt=None,
                  scaleObservedAt=None, validUntil=None, soc=None)


def intervals(rows, start=0, end=300, **kwargs):
    return build_soc_intervals(rows, at(start), at(end), epoch_start=at(-86400), **kwargs)


@pytest.mark.parametrize('changes', [
    {'version': True}, {'version': 2}, {'streamEpoch': 'bad'}, {'soc': True},
    {'soc': '50'}, {'soc': -1}, {'soc': 101}, {'soc': float('nan')},
    {'soc': float('inf')}, {'reason': 'unknown'}, {'status': 'unknown'},
    {'recordedAt': ms(1)}, {'observedAt': ms(1)}, {'scaleObservedAt': ms(1)},
    {'validUntil': ms(121)}, {'recordedAt': 1.5}, {'observedAt': True},
    {'extra': 1}, {'observedAt': 2**53}, {'soc': None},
    {'status': 'unavailable', 'reason': 'input_stale'},
])
def test_invalid_record(changes):
    assert parse_evidence(record(**changes), at(0)) is None


def test_valid_and_unavailable_records():
    assert parse_evidence(record(), at(.01)).soc == 50
    assert parse_evidence(unavailable(0), at(0)).valid_until is None
    assert parse_evidence(record(soc=0), at(0)).soc == 0


@pytest.mark.parametrize('raw', ['{}', '[]', 'null', 'NULL', '{', ' '*4097,
                                 record().replace('"version": 1', '"version": 1, "version": 1')])
def test_malformed_json(raw):
    assert parse_evidence(raw, at(0)) is None


def test_unchanged_soc_has_fresh_intervals_without_publication_delay_carry():
    result = intervals([(at(.01), record()), (at(60.02), record(60))])
    assert [(r.start, r.end) for r in result] == [(at(.01), at(60)), (at(60.02), at(180))]
    assert soc_at(result, at(60.01)) is None
    assert soc_at(result, at(180)) is None
    assert soc_at(result, at(61)) == 50


def test_original_carry_time_and_expiry_are_not_relabelled():
    result = intervals([(at(-10), record(-10))], start=0)
    assert result[0].start == at(0)
    assert result[0].persisted_at == at(-10)
    assert result[0].record.observed_at == at(-10)
    assert result[0].end == at(110)


def test_fault_and_recovery_keep_gap():
    result = intervals([(at(0), record()), (at(31), unavailable(30)),
                        (at(90), record(90, soc=40))])
    assert [(r.start, r.end, r.soc) for r in result] == [(at(0), at(30), 50), (at(90), at(210), 40)]
    assert soc_at(result, at(60)) is None


def test_malformed_record_is_a_barrier_not_a_skipped_row():
    result = intervals([(at(0), record()), (at(30), 'NULL'), (at(90), record(90))])
    assert result[0].end == at(30)
    assert soc_at(result, at(50)) is None


def test_duplicate_restore_cannot_renew_or_recover_after_fault():
    assert intervals([(at(0), record()), (at(100), record())])[0].end == at(120)
    result = intervals([(at(0), record()), (at(30), '{}'), (at(100), record())])
    assert len(result) == 1 and result[0].end == at(30)


@pytest.mark.parametrize('rows', [
    [(at(0), record()), (at(0), record(0, soc=51))],
    [(at(1), record()), (at(0), record())],
    [(at(0), record()), (at(10), record(0, soc=51))],
    [(at(20), record(20)), (at(30), record(10))],
    [(at(0), record()), (at(301), record(301)), (at(10), unavailable(10))],
    [(at(0), record()), (at(30), '{}'), (at(40), record(20, soc=60))],
    [(at(0), record()), (at(30), record(30, streamEpoch=OTHER)), (at(60), record(60))],
])
def test_ambiguous_order_rejected(rows):
    with pytest.raises(ValueError):
        intervals(rows)


def test_epoch_transition_is_a_boundary_not_a_bank_reset():
    result = intervals([(at(0), record()), (at(60), record(60, streamEpoch=OTHER))])
    assert [r.record.stream_epoch for r in result] == [EPOCH, OTHER]
    assert result[0].end == result[1].start == at(60)


def test_future_row_does_not_rewrite_past_window():
    result = intervals([(at(0), record()), (at(301), unavailable(30))])
    assert result[0].end == at(120)


def test_expired_valid_status_cannot_extend_to_delayed_unavailable():
    result = intervals([(at(0), record()), (at(171), unavailable(171)), (at(175), record(175))])
    assert result[0].end == at(120)
    assert soc_at(result, at(170)) is None
    assert soc_at(result, at(175)) == 50


def test_bank_epoch_and_empty_history():
    assert intervals([]) == []
    assert build_soc_intervals([], at(-20), at(-10), epoch_start=at(0)) == []
    result = intervals([(at(0), record())], epoch_end=at(60))
    assert result[0].end == at(60)


def test_prior_bank_observation_cannot_be_carried_into_new_bank():
    result = build_soc_intervals([(at(-1), record(-1)), (at(60), record(60))],
                                 at(0), at(300), epoch_start=at(0))
    assert len(result) == 1 and result[0].start == at(60)


@pytest.mark.parametrize('day,hours', [(datetime(2026, 3, 8), 23), (datetime(2026, 11, 1), 25)])
def test_denver_dst_windows_are_utc_intersections(day, hours):
    zone = ZoneInfo('America/Denver')
    start = day.replace(tzinfo=zone)
    end = (day+timedelta(days=1)).replace(tzinfo=zone)
    assert (end.astimezone(timezone.utc)-start.astimezone(timezone.utc)).total_seconds() == hours*3600
    rows = []
    for stamp in (start, end-timedelta(seconds=60)):
        timestamp = int(stamp.timestamp()*1000)
        rows.append((stamp, record(recordedAt=timestamp, observedAt=timestamp,
                                   scaleObservedAt=timestamp, validUntil=timestamp+120000)))
    result = build_soc_intervals(rows, start, end, epoch_start=BASE-timedelta(days=365))
    assert len(result) == 2
    assert result[0].start == start.astimezone(timezone.utc)
    assert result[-1].end == end.astimezone(timezone.utc)
    assert sum((r.end-r.start).total_seconds() for r in result) == 180


def test_naive_and_empty_window_rejected():
    with pytest.raises(ValueError):
        parse_evidence(record(), datetime(2026, 9, 10))
    with pytest.raises(ValueError):
        intervals([], start=1, end=1)


def test_database_adapter_retains_fault_before_restored_carry():
    rows = [(at(-100), record(-100)), (at(-50), unavailable(-50)),
            (at(-10), record(-100))]
    # A single carry would wrongly authorize the old record's remaining lifetime.
    assert soc_at(intervals([rows[-1]]), at(0)) == 50
    with patch('earthship_energy.reader.fetch_freshness_observations', return_value=rows) as fetch:
        with pytest.raises(EvidenceSequenceError):
            fetch_bms_soc_intervals('connection', 'item0613', at(0), at(300), epoch_start=at(-86400))
    fetch.assert_called_once_with('connection', 'item0613', at(-120), at(300))


def test_adapter_rejects_bad_window_before_query():
    with patch('earthship_energy.reader.fetch_freshness_observations') as fetch:
        with pytest.raises(ValueError):
            fetch_bms_soc_intervals(None, 'item0613', at(1), at(0), epoch_start=at(-86400))
    fetch.assert_not_called()
