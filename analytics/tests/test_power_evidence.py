from datetime import datetime, timedelta, timezone
import json

import pytest

from earthship_energy.power_evidence import (
    BOUNDS, PowerSequenceError, build_power_intervals, parse_power_evidence,
)
from earthship_energy.power_intervals import account_power_intervals

BASE = datetime(2026, 9, 20, tzinfo=timezone.utc)
EPOCH = '00000000-0000-4000-8000-000000000001'
OTHER = '00000000-0000-4000-8000-000000000002'
FIELD = 'battery.dc_power_w'


def at(seconds):
    return BASE + timedelta(seconds=seconds)


def ms(seconds):
    return int(at(seconds).timestamp() * 1000)


def data(t=1, seq=1, watts=1000, observed=None, epoch=EPOCH):
    fields = {name: dict(status='unavailable', reason='input_unavailable',
                        observedAt=None, validUntil=None, watts=None) for name in BOUNDS}
    if watts is not None:
        observed = t if observed is None else observed
        fields[FIELD] = dict(status='valid', reason='ok', observedAt=ms(observed),
                            validUntil=ms(observed+120), watts=watts)
    return dict(version=1, streamEpoch=epoch, sequence=seq, recordedAt=ms(t), fields=fields)


def row(value, delay=.01):
    return (datetime.fromtimestamp(value['recordedAt']/1000, timezone.utc) + timedelta(seconds=delay), json.dumps(value))


def build(rows, start=0, end=300, cutover=0):
    return build_power_intervals(rows, FIELD, at(start), at(end), cutover=at(cutover))


def test_only_qualified_120_seconds_not_whole_day_are_integrated():
    intervals = build([row(data(), delay=0)], end=86400)
    result = account_power_intervals(intervals, window_start=at(0), window_end=at(86400))
    assert result.covered_seconds == 120
    assert result.positive_kwh == pytest.approx(1/30)


def test_persistence_delay_is_not_backdated():
    intervals = build([row(data(), delay=10)])
    assert [(i.start, i.end) for i in intervals] == [(at(11), at(121))]


def test_unchanged_other_field_does_not_make_a_false_gap():
    first = data(); second = data(t=10, seq=2, observed=1)
    second['fields']['pv.input_power_w'] = dict(status='valid', reason='ok', observedAt=ms(10), validUntil=ms(130), watts=200)
    intervals = build([row(first), row(second, delay=5)])
    assert [(i.start, i.end) for i in intervals] == [(at(1.01), at(121))]


def test_changed_receipt_preserves_publication_gap():
    intervals = build([row(data()), row(data(10,2,2000),delay=2)])
    assert [(i.start,i.end,i.watts) for i in intervals] == [(at(1.01),at(10),1000),(at(12),at(130),2000)]


def test_same_millisecond_publications_are_ordered_by_sequence():
    first = data(); second = data(seq=2,watts=None)
    assert build([row(first),row(second,delay=.02)]) == []


def test_invalid_field_then_fresh_recovery():
    intervals = build([row(data()), row(data(10,2,None)), row(data(20,3))])
    assert [(i.start,i.end) for i in intervals] == [(at(1.01),at(10)),(at(20.01),at(140))]


def test_malformed_row_is_a_barrier_not_discarded():
    intervals = build([row(data()),(at(10),'not-json'),row(data(20,2,observed=1)),row(data(30,3))])
    assert [(i.start,i.end) for i in intervals] == [(at(1.01),at(10)),(at(30.01),at(150))]


def test_missing_sequence_cannot_carry_an_old_field_across_unknown_publications():
    intervals = build([row(data()),row(data(10,2)),row(data(30,4,observed=10)),row(data(40,5))])
    assert [(i.start,i.end) for i in intervals] == [(at(1.01),at(10)),(at(40.01),at(160))]


def test_restore_does_not_renew_or_bridge_invalid_barrier():
    first = data()
    assert build([row(first),(at(50),json.dumps(first))]) == build([row(first)])
    assert [(i.start,i.end) for i in build([row(first),(at(10),'bad'),(at(50),json.dumps(first))])] == [(at(1.01),at(10))]


def test_epoch_boundary_and_retired_epoch_rejection():
    rows = [row(data()),row(data(10,1,None,epoch=OTHER)),row(data(20,2,epoch=OTHER))]
    assert [(i.start,i.end) for i in build(rows)] == [(at(1.01),at(10)),(at(20.01),at(140))]
    with pytest.raises(PowerSequenceError,match='retired'):
        build(rows+[row(data(30,3))])


@pytest.mark.parametrize('rows', [
    [row(data()),row(data())],
    [row(data(10)),row(data())],
    [row(data()),row(data(10,1,2000))],
    [row(data(10)),row(data(9,2),delay=3)],
    [row(data(10)),row(data(20,2,observed=9))],
])
def test_ambiguous_sequence_fails_closed(rows):
    with pytest.raises(PowerSequenceError):
        build(rows)


def test_window_and_cutover_do_not_relabel_pre_activation_readings():
    assert build([row(data())],cutover=2) == []
    intervals=build([row(data(10))],start=20,end=30,cutover=2)
    assert [(i.start,i.end) for i in intervals] == [(at(20),at(30))]
    assert build([row(data(10))],end=10) == []


@pytest.mark.parametrize('key,value', [('version',True),('version',2),('sequence',True),('sequence',0),('streamEpoch','bad'),('extra',1)])
def test_closed_record_schema(key,value):
    d=data(); d[key]=value
    assert parse_power_evidence(json.dumps(d),at(2)) is None


@pytest.mark.parametrize('key,value', [('watts',True),('watts',1.5),('watts',-32768),('watts',32768),('watts',float('nan')),
                                     ('observedAt',True),('observedAt',ms(3)),('validUntil',ms(120)),('reason','other'),('status','other'),('extra',1)])
def test_closed_field_schema(key,value):
    d=data(); d['fields'][FIELD][key]=value
    assert parse_power_evidence(json.dumps(d),at(2)) is None


def test_duplicate_keys_oversize_and_future_persistence_rejected():
    raw=json.dumps(data())
    assert parse_power_evidence(raw.replace('"version": 1','"version": 1, "version": 1'),at(2)) is None
    assert parse_power_evidence(' '*4097,at(2)) is None
    assert parse_power_evidence(raw,at(0)) is None


def test_expired_at_publication_rejected_and_late_persistence_has_no_coverage():
    assert parse_power_evidence(json.dumps(data(121,observed=1)),at(122)) is None
    assert build([row(data(),delay=121)]) == []


def test_unknown_field_naive_timestamp_and_nonpositive_window_rejected():
    with pytest.raises(ValueError): build_power_intervals([], 'unknown', at(0), at(1),cutover=at(0))
    with pytest.raises(ValueError): build_power_intervals([], FIELD, BASE.replace(tzinfo=None),at(1),cutover=at(0))
    with pytest.raises(ValueError): build([],end=0)
