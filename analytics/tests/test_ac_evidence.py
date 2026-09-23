from datetime import timedelta
from types import SimpleNamespace
import json
import sys

import pytest

from earthship_energy.ac_evidence import FIELD, build_ac_intervals, parse_ac_evidence
from earthship_energy.ac_reader import read_ac_history
from earthship_energy.power_evidence import PowerSequenceError
from earthship_energy.power_reader import PowerHistoryLimitError
from test_power_evidence import EPOCH, OTHER, at, ms


def data(t=1, seq=1, watts=1000, observed=None, epoch=EPOCH, reason='input_unavailable'):
    field = (dict(status='valid', reason='ok', observedAt=ms(t if observed is None else observed),
                  validUntil=ms((t if observed is None else observed)+30), watts=watts)
             if watts is not None else dict(status='unavailable', reason=reason,
                                           observedAt=None, validUntil=None, watts=None))
    return dict(version=1, basis='inverter_output', streamEpoch=epoch,
                sequence=seq, recordedAt=ms(t), fields={FIELD:field})


def row(value, delay=.01):
    return at(0)+timedelta(milliseconds=value['recordedAt']-ms(0), seconds=delay), json.dumps(value)


def build(rows, start=0, end=90, cutover=0, topology_start=0, topology_end=90):
    return build_ac_intervals(rows, at(start), at(end), cutover=at(cutover),
                              topology_start=at(topology_start), topology_end=at(topology_end))


def test_strict_envelope_and_unavailable_reasons():
    for reason in ('source_unavailable','input_unavailable','invalid_input','input_stale'):
        assert parse_ac_evidence(json.dumps(data(watts=None,reason=reason)),at(2)).fields[FIELD] is None
    for key,value in [('basis','household_load'),('version',True),('sequence',0),('streamEpoch','bad')]:
        candidate=data(); candidate[key]=value
        assert parse_ac_evidence(json.dumps(candidate),at(2)) is None
    candidate=data(); candidate['fields'][FIELD]['watts']=True
    assert parse_ac_evidence(json.dumps(candidate),at(2)) is None
    candidate=data(); candidate['fields'][FIELD]['validUntil']=ms(121)
    assert parse_ac_evidence(json.dumps(candidate),at(2)) is None
    assert parse_ac_evidence(json.dumps(data()),at(0)) is None


def test_topology_is_finite_and_preperiod_evidence_not_promoted():
    assert build([row(data())],topology_start=2)==[]
    assert build([row(data(10))],start=20,end=40,topology_start=2,topology_end=25)[0].end==at(25)
    assert build([row(data(10))],topology_start=50)==[]
    with pytest.raises(ValueError): build([],topology_start=90,topology_end=90)


def test_expiry_invalid_gap_and_epoch_boundaries():
    rows=[row(data()),row(data(10,2,watts=None)),row(data(20,3))]
    assert [(i.start,i.end) for i in build(rows)]==[(at(1.01),at(10)),(at(20.01),at(50))]
    assert [(i.start,i.end) for i in build([row(data()),row(data(40,2,observed=1))])]==[(at(1.01),at(31))]
    assert build([row(data()),row(data(10,3,observed=1))])==[]
    assert build([row(data()),(at(10),'bad'),row(data(20,2,observed=1))])[0].end==at(10)
    assert build([row(data()),row(data(10,1,watts=None,epoch=OTHER))])[0].end==at(10)
    with pytest.raises(PowerSequenceError):
        build([row(data()),row(data(10,1,watts=None,epoch=OTHER)),row(data(20,2,epoch=EPOCH))])


class Cursor:
    def __init__(self, conn): self.conn=conn
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql,params): self.conn.query=(sql,params)
    def fetchall(self): return self.conn.rows


class Connection:
    def __init__(self,rows): self.rows=rows;self.closed=False
    def set_session(self,**kwargs): self.session=kwargs
    def cursor(self): return Cursor(self)
    def close(self): self.closed=True


def test_bounded_read_preserves_receipts_and_does_not_infer_history(monkeypatch):
    conn=Connection([(*row(data()),True)])
    calls=[]
    def connect(**kwargs): calls.append(kwargs);return conn
    monkeypatch.setitem(sys.modules,'psycopg2',SimpleNamespace(connect=connect))
    settings=SimpleNamespace(connect_kwargs={'dbname':'fixture'})
    def read(**kwargs):
        return read_ac_history(settings,'item0999',at(0),at(90),cutover=at(0),
                               topology_start=at(0),topology_end=at(90),**kwargs)
    assert read()[0].start==at(1.01)
    assert conn.closed and conn.session=={'readonly':True,'autocommit':True}
    assert conn.query[1]==(at(-30),at(-30),at(90),60001)
    assert calls[0]['connect_timeout']==5
    conn.rows=[(*row(data()),True),(*row(data(10,2)),True)]
    with pytest.raises(PowerHistoryLimitError): read(row_limit=1)
    assert read_ac_history(settings,'item0999',at(0),at(90),cutover=at(91),
                           topology_start=at(0),topology_end=at(90))==[]


def test_bad_request_rejected_before_connection():
    settings=SimpleNamespace(connect_kwargs={})
    with pytest.raises(ValueError):
        read_ac_history(settings,'item0999;DROP',at(0),at(90),cutover=at(0),
                        topology_start=at(0),topology_end=at(90))
