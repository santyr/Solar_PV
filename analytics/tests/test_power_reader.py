from datetime import timedelta
from types import SimpleNamespace
import sys

import pytest

from earthship_energy.power_evidence import BOUNDS, PowerSequenceError
from earthship_energy.power_reader import PowerHistoryLimitError, read_power_history
from test_power_evidence import at, data, row


class Cursor:
    def __init__(self, owner): self.owner=owner
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params): self.owner.queries.append((sql,params))
    def fetchall(self):
        if self.owner.error: raise self.owner.error
        return self.owner.rows


class Connection:
    def __init__(self, rows):
        self.rows=rows; self.queries=[]; self.closed=False; self.error=None
    def set_session(self, **kwargs): self.session=kwargs
    def cursor(self): return Cursor(self)
    def close(self): self.closed=True


@pytest.fixture
def fake_db(monkeypatch):
    conn=Connection([]); calls=[]
    def connect(**kwargs): calls.append(kwargs); return conn
    monkeypatch.setitem(sys.modules,'psycopg2',SimpleNamespace(connect=connect))
    settings=SimpleNamespace(connect_kwargs={'dbname':'fixture','user':'fixture'})
    def read(**kwargs):
        return read_power_history(settings,kwargs.pop('table','item0999'),
                                  kwargs.pop('start',at(0)),kwargs.pop('end',at(300)),
                                  cutover=kwargs.pop('cutover',at(0)),**kwargs)
    return conn,calls,read


def test_single_snapshot_bounded_read_preserves_original_receipt_time(fake_db):
    conn,calls,read=fake_db
    persisted,raw=row(data(),delay=2);conn.rows=[(persisted,raw,True)]
    result=read()
    assert set(result)==set(BOUNDS)
    assert result['battery.dc_power_w'][0].start==at(3)
    assert conn.closed and conn.session=={'readonly':True,'autocommit':True}
    assert calls[0]['connect_timeout']==5
    assert 'default_transaction_read_only=on' in calls[0]['options']
    assert 'statement_timeout=5000' in calls[0]['options']
    assert 'lock_timeout=1000' in calls[0]['options']
    assert len(conn.queries)==1
    sql,params=conn.queries[0]
    assert 'UNION ALL' in sql and 'LIMIT 2' in sql and 'LIMIT %s' in sql
    assert 'octet_length(value::text) <= 4096' in sql
    assert params==(at(-120),at(-120),at(300),60001)


def test_overflow_rejects_not_partial_output(fake_db):
    conn,_,read=fake_db
    conn.rows=[(*row(data(1,1)),True),(*row(data(2,2)),True)]
    with pytest.raises(PowerHistoryLimitError): read(row_limit=1)
    assert conn.closed


def test_two_carry_rows_are_not_counted_against_window_budget(fake_db):
    conn,_,read=fake_db
    conn.rows=[(*row(data(-200,1,None)),False),(*row(data(-190,2,None)),False),(*row(data(1,3)),True)]
    assert read(row_limit=1)['battery.dc_power_w']


def test_database_failure_is_propagated_and_connection_closed(fake_db):
    conn,_,read=fake_db;conn.error=TimeoutError('fixture')
    with pytest.raises(TimeoutError): read()
    assert conn.closed


def test_oversized_null_placeholder_remains_an_invalid_barrier(fake_db):
    conn,_,read=fake_db
    conn.rows=[(*row(data()),True),(at(10),None,True)]
    assert read()['battery.dc_power_w'][0].end==at(10)


def test_duplicate_carry_times_are_not_deduplicated(fake_db):
    conn,_,read=fake_db
    value=(*row(data(-200,1,None)),False);conn.rows=[value,value]
    with pytest.raises(PowerSequenceError): read()


@pytest.mark.parametrize('kwargs', [
    {'table':'item0999; SELECT 1'}, {'table':None}, {'row_limit':True},
    {'row_limit':0}, {'row_limit':60001}, {'end':at(0)},
    {'end':at(90001)}, {'start':at(0).replace(tzinfo=None)},
])
def test_bad_requests_fail_before_connect(fake_db,kwargs):
    _,calls,read=fake_db
    with pytest.raises(ValueError): read(**kwargs)
    assert calls==[]


def test_pre_cutover_window_requires_no_database_connection(fake_db):
    _,calls,read=fake_db
    assert all(not value for value in read(cutover=at(300)).values())
    assert calls==[]


def test_25_hour_dst_day_supported(fake_db):
    _,calls,read=fake_db
    assert all(not value for value in read(end=at(0)+timedelta(hours=25)).values())
    assert len(calls)==1
