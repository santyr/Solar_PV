from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import psycopg2
import pytest

from advisory_db_fixture import advisory_db
from earthship_energy.ac_policy import AcEvidencePolicy
from earthship_energy.ac_store import encode_ac_snapshot, store_ac_snapshot


def observation(day=date(2026, 9, 22), *, kwh=12.5, coverage=.95):
    zone = ZoneInfo('America/Denver')
    start = datetime.combine(day, datetime.min.time(), tzinfo=zone)
    end = datetime.combine(day+timedelta(days=1), datetime.min.time(), tzinfo=zone)
    cutover = (start-timedelta(days=1)).astimezone(timezone.utc)
    policy = AcEvidencePolicy(cutover, cutover, None)
    payload = {
        'local_date': day.isoformat(), 'window_start': start.isoformat(),
        'window_end': end.isoformat(), 'ac_item': 'Inverter_AC_Evidence_JSON',
        'ac_cutover': cutover.isoformat(), 'topology_from': cutover.isoformat(),
        'topology_until': None, 'basis': 'inverter_output_observed_with_attested_topology',
        'observed_ac_load_kwh': kwh, 'ac_coverage': coverage,
        'common_pv_dc_kwh': 10.0, 'common_ac_load_kwh': 11.0,
        'common_coverage': .9, 'balance_kwh': None,
        'balance_reason': 'dc_pv_and_ac_load_cross_domain',
    }
    return payload, policy


def test_idempotent_append_only_revisions_and_no_legacy_write(advisory_db):
    payload, policy = observation()
    with closing(advisory_db.connect_owner()) as connection:
        first = store_ac_snapshot(connection, payload, policy)
        retry = store_ac_snapshot(connection, payload, policy)
        assert first['inserted'] and not retry['inserted']
        assert first['snapshot_id'] == retry['snapshot_id']
        revised = dict(payload, observed_ac_load_kwh=13.0)
        next_revision = store_ac_snapshot(connection, revised, policy)
        assert next_revision['inserted']
        assert next_revision['snapshot_id'] > first['snapshot_id']
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM energy_analytics.daily_ac_snapshots')
            assert cursor.fetchone()[0] == 2
            cursor.execute('SELECT count(*) FROM energy_analytics.daily_power_snapshots')
            assert cursor.fetchone()[0] == 0


@pytest.mark.parametrize('operation', [
    'UPDATE energy_analytics.daily_ac_snapshots SET computed_at=now()',
    'DELETE FROM energy_analytics.daily_ac_snapshots',
    'TRUNCATE energy_analytics.daily_ac_snapshots',
])
def test_database_refuses_ac_revision_mutation(advisory_db, operation):
    with closing(advisory_db.connect_owner()) as connection:
        with pytest.raises(psycopg2.Error, match='append-only'):
            with connection.cursor() as cursor:
                cursor.execute(operation)
        connection.rollback()


def test_advisory_writer_has_no_ac_revision_access(advisory_db):
    payload, policy = observation(day=date(2026, 9, 21))
    with closing(advisory_db.connect_writer()) as connection:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            store_ac_snapshot(connection, payload, policy)


def test_unfinished_day_and_autocommit_are_refused_before_write(advisory_db):
    future, policy = observation(day=date(2050, 1, 1))
    with pytest.raises(ValueError, match='unfinished'):
        store_ac_snapshot(object(), future, policy)
    payload, policy = observation(day=date(2026, 9, 20))
    with closing(advisory_db.connect_owner()) as connection:
        connection.autocommit = True
        with pytest.raises(ValueError, match='transaction'):
            store_ac_snapshot(connection, payload, policy)


@pytest.mark.parametrize('day,hours', [(date(2025, 3, 9), 23),
                                      (date(2025, 11, 2), 25)])
def test_dst_full_days(advisory_db, day, hours):
    payload, policy = observation(day=day)
    start = datetime.fromisoformat(payload['window_start']).astimezone(timezone.utc)
    end = datetime.fromisoformat(payload['window_end']).astimezone(timezone.utc)
    assert (end-start).total_seconds() == hours*3600
    assert encode_ac_snapshot(payload, policy)[0] == day
    with closing(advisory_db.connect_owner()) as connection:
        assert store_ac_snapshot(connection, payload, policy)['inserted']


@pytest.mark.parametrize('mutate', [
    lambda p: p.update(extra=1),
    lambda p: p.update(ac_coverage=True),
    lambda p: p.update(ac_coverage=1.1),
    lambda p: p.update(observed_ac_load_kwh=-1),
    lambda p: p.update(observed_ac_load_kwh=None),
    lambda p: p.update(common_coverage=.99),
    lambda p: p.update(balance_kwh=2),
    lambda p: p.update(balance_reason='surplus'),
    lambda p: p.update(window_start='2026-09-22T07:00:00Z'),
    lambda p: p.update(local_date='2026-09-23'),
])
def test_invalid_ac_snapshot_refused_before_io(mutate):
    payload, policy = observation()
    mutate(payload)
    with pytest.raises(ValueError):
        encode_ac_snapshot(payload, policy)


def test_zero_coverage_stays_unavailable_not_zero_load():
    payload, policy = observation()
    payload.update(observed_ac_load_kwh=None, ac_coverage=0,
                   common_pv_dc_kwh=None, common_ac_load_kwh=None,
                   common_coverage=0, balance_reason='no_common_qualified_intervals')
    encode_ac_snapshot(payload, policy)
    payload['observed_ac_load_kwh'] = 0
    with pytest.raises(ValueError, match='coverage or balance'):
        encode_ac_snapshot(payload, policy)
