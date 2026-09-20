from contextlib import closing
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone

import psycopg2
import pytest

from advisory_db_fixture import advisory_db
from earthship_energy.materialize import materialize_daily_snapshot
from earthship_energy.power_store import encode_snapshot, store_power_snapshot


def snapshot(day=21, efc=.1, cutover='2026-09-20T15:18:58.261099+00:00'):
    start=datetime(2026,9,day,6,tzinfo=timezone.utc)
    return {
        'status':'ok','mode':'read_only_dry_run','local_date':start.date().isoformat(),
        'window_start':start.isoformat(),'window_end':(start+timedelta(days=1)).isoformat(),
        'power_accounting':{'version':1,'policy':'qualified_power_evidence_v1',
            'cutover':cutover,'qualified_fields':['battery.dc_power_w','pv.input_power_w','pv.output_power_w'],
            'balance_reason':'ac_load_evidence_unqualified','efficiency_reason':None,'efficiency_coverage':.9},
        'battery':{'daily_efc':efc,'charge_kwh':efc*20.48,'discharge_kwh':efc*20.48,'coverage':.9},
        'pv':{'energy_kwh':10,'output_energy_kwh':9,'coverage':.9},
        'load':{},'weather':{},'balance':{'pv_load_ratio':None,'surplus_deficit_kwh':None},
        'source_quality':[],
    }


def test_retries_and_revisions_do_not_mix_legacy_or_double_count(advisory_db):
    with closing(advisory_db.connect_owner()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""INSERT INTO energy_analytics.daily_battery
                (local_date,epoch_id,daily_efc,coverage,quality)
                VALUES ('2026-09-19','test_bank',99,1,'ok')""")
        connection.commit()
        first=materialize_daily_snapshot(connection,snapshot(),'test_bank')
        retry=materialize_daily_snapshot(connection,deepcopy(snapshot()),'test_bank')
        assert first['inserted'] and not retry['inserted']
        assert first['snapshot_id']==retry['snapshot_id']
        assert first['cumulative_efc']==retry['cumulative_efc']==.1
        revised=store_power_snapshot(connection,snapshot(efc=.2),'test_bank')
        assert revised['snapshot_id']!=first['snapshot_id']
        assert revised['cumulative_efc']==.2
        next_day=store_power_snapshot(connection,snapshot(day=22,efc=.3),'test_bank')
        assert next_day['cumulative_efc']==.5
        # Retrying an older revision cannot select it over the newer revision.
        assert store_power_snapshot(connection,snapshot(),'test_bank')['cumulative_efc']==.2
        other=store_power_snapshot(connection,snapshot(day=22,efc=.7,
            cutover='2026-09-21T00:00:00+00:00'),'test_bank')
        assert other['cumulative_efc']==.7
        with connection.cursor() as cursor:
            cursor.execute('SELECT local_date,daily_efc FROM energy_analytics.daily_battery')
            assert cursor.fetchall()==[(date(2026,9,19),99.0)]


@pytest.mark.parametrize('operation',[
    'UPDATE energy_analytics.daily_power_snapshots SET computed_at=now()',
    'DELETE FROM energy_analytics.daily_power_snapshots',
    'TRUNCATE energy_analytics.daily_power_snapshots',
])
def test_database_refuses_mutation(advisory_db,operation):
    with closing(advisory_db.connect_owner()) as connection:
        with pytest.raises(psycopg2.Error,match='append-only'):
            with connection.cursor() as cursor:cursor.execute(operation)
        connection.rollback()


def test_existing_advisory_writer_has_no_power_write_privileges(advisory_db):
    with closing(advisory_db.connect_writer()) as connection:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            store_power_snapshot(connection,snapshot(day=23),'test_bank')


def test_autocommit_cannot_drop_the_series_lock_between_statements(advisory_db):
    with closing(advisory_db.connect_owner()) as connection:
        connection.autocommit=True
        with pytest.raises(ValueError,match='require a transaction'):
            store_power_snapshot(connection,snapshot(day=24),'test_bank')


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-1,True])
def test_invalid_efc_is_rejected_before_io(value):
    payload=snapshot(efc=value)
    with pytest.raises(ValueError):store_power_snapshot(object(),payload,'test_bank')


def test_unqualified_balance_and_provenance_are_rejected():
    payload=snapshot();payload['balance']['pv_load_ratio']=1
    with pytest.raises(ValueError,match='AC balance'):encode_snapshot(payload)
    payload=snapshot();payload['power_accounting']['version']=True
    with pytest.raises(ValueError,match='provenance'):encode_snapshot(payload)
    payload=snapshot();payload['power_accounting']['cutover']='2026-09-20T15:00:00'
    with pytest.raises(ValueError,match='timezone-aware'):encode_snapshot(payload)
