from contextlib import closing
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from types import SimpleNamespace

import pytest

from advisory_db_fixture import advisory_db
from test_power_store import snapshot
from earthship_energy.power_store import store_power_snapshot
from earthship_energy.power_snapshot_reader import read_power_snapshots
from earthship_energy.power_report import read_power_report

CUTOVER = datetime.fromisoformat('2026-08-20T15:18:58.261099+00:00')


def settings(db):
    return SimpleNamespace(connect_kwargs=dict(host=db.host,port=db.port,dbname=db.dbname,
                           user=db.owner_user,password=db.owner_password))


def read(db, **overrides):
    args=dict(epoch_id='test_bank',cutover=CUTOVER,start_date=date(2026,8,21),
              end_date=date(2026,8,25),as_of=datetime(2030,1,1,tzinfo=timezone.utc))
    args.update(overrides)
    return read_power_snapshots(settings(db),**args)


def test_latest_revision_selected_before_quality_and_missing_days_preserved(advisory_db):
    with closing(advisory_db.connect_owner()) as connection:
        first=snapshot();first['battery']['coverage']=1
        store_power_snapshot(connection,first,'test_bank')
        later=snapshot(efc=.02);later['battery']['coverage']=.1
        selected=store_power_snapshot(connection,later,'test_bank')
        store_power_snapshot(connection,snapshot(day=23),'test_bank')
        store_power_snapshot(connection,snapshot(day=24,cutover='2026-08-21T00:00:00+00:00'),'test_bank')
    rows=read(advisory_db)
    assert [r['local_date'] for r in rows]==[date(2026,8,21),date(2026,8,23)]
    assert rows[0]['snapshot_id']==selected['snapshot_id']
    assert rows[0]['payload']['battery']['coverage']==.1
    assert all(r['cutover']==CUTOVER for r in rows)


def test_other_bank_and_pre_cutover_asof_do_not_fall_back(advisory_db):
    assert read(advisory_db,epoch_id='missing_bank')==[]
    assert read(advisory_db,as_of=CUTOVER-timedelta(seconds=1))==[]


def test_report_uses_latest_database_revision_and_discloses_missing_day(advisory_db):
    with closing(advisory_db.connect_owner()) as connection:
        store_power_snapshot(connection,snapshot(day=27,efc=.8),'test_bank')
        later=snapshot(day=27,efc=.02)
        later['battery']['coverage']=.1
        selected=store_power_snapshot(connection,later,'test_bank')
        store_power_snapshot(connection,snapshot(day=29,efc=.03),'test_bank')
    result=read_power_report(settings(advisory_db),epoch_id='test_bank',cutover=CUTOVER,
        start_date=date(2026,8,27),end_date=date(2026,8,30),
        as_of=datetime(2030,1,1,tzinfo=timezone.utc))
    assert result['totals']['daily_efc']==pytest.approx(.05)
    assert result['missing_dates']==['2026-08-28']
    assert result['daily'][0]['snapshot_id']==selected['snapshot_id']
    assert result['daily'][0]['battery_daily_coverage']==.1


def test_latest_invalid_revision_does_not_resurrect_older_valid_one(advisory_db):
    with closing(advisory_db.connect_owner()) as connection:
        store_power_snapshot(connection,snapshot(day=25),'test_bank')
        bad=snapshot(day=25);bad['battery']['coverage']=2
        encoded=json.dumps(bad,sort_keys=True,separators=(',',':'))
        with connection.cursor() as cursor:
            cursor.execute('''INSERT INTO energy_analytics.daily_power_snapshots
                (local_date,epoch_id,policy,cutover_at,payload_sha256,payload)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb)''',
                (date(2026,8,25),'test_bank','qualified_power_evidence_v1',CUTOVER,
                 hashlib.sha256(encoded.encode()).hexdigest(),encoded))
        connection.commit()
    with pytest.raises(ValueError,match='coverage'):
        read(advisory_db,start_date=date(2026,8,25),end_date=date(2026,8,26))


@pytest.mark.parametrize('days',[0,-1,367])
def test_unbounded_or_empty_ranges_refused_before_connection(days):
    with pytest.raises(ValueError,match='1 to 366'):
        read_power_snapshots(object(),epoch_id='bank',cutover=CUTOVER,
            start_date=date(2026,8,21),end_date=date(2026,8,21)+timedelta(days=days),as_of=CUTOVER)
