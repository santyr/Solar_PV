from contextlib import closing
from datetime import date, datetime, timedelta, timezone
import hashlib
import json

import pytest

from advisory_db_fixture import advisory_db
from earthship_energy.ac_policy import AcEvidencePolicy
from earthship_energy.ac_snapshot_reader import read_ac_snapshots
from earthship_energy.ac_store import store_ac_snapshot
from earthship_energy.db import JdbcSettings
from test_ac_store import observation


def settings(db):
    return JdbcSettings(db.host, db.port, db.dbname, db.owner_user, db.owner_password)


def read(db, policy, start=date(2026, 9, 22), end=date(2026, 9, 23)):
    return read_ac_snapshots(settings(db), policy=policy, start_date=start,
                             end_date=end, as_of=datetime.now(timezone.utc))


def test_latest_revision_only_and_no_legacy_series(advisory_db):
    payload, policy = observation()
    with closing(advisory_db.connect_owner()) as connection:
        first = store_ac_snapshot(connection, payload, policy)
        updated = dict(payload, observed_ac_load_kwh=13.2)
        second = store_ac_snapshot(connection, updated, policy)
    rows = read(advisory_db, policy)
    assert len(rows) == 1
    assert rows[0]['snapshot_id'] == second['snapshot_id'] != first['snapshot_id']
    assert rows[0]['payload']['observed_ac_load_kwh'] == 13.2
    assert read(advisory_db, policy, date(2026, 9, 23), date(2026, 9, 24)) == []


def test_malformed_latest_revision_fails_without_older_fallback(advisory_db):
    payload, policy = observation()
    with closing(advisory_db.connect_owner()) as connection:
        store_ac_snapshot(connection, payload, policy)
        bad = dict(payload, balance_reason='surplus')
        encoded = json.dumps(bad, sort_keys=True, separators=(',', ':'))
        with connection.cursor() as cursor:
            cursor.execute('''INSERT INTO energy_analytics.daily_ac_snapshots
                (local_date,policy,cutover_at,topology_from,payload_sha256,payload)
                VALUES (%s,'qualified_inverter_ac_output_v1',%s,%s,%s,%s::jsonb)''',
                (payload['local_date'], policy.cutover, policy.topology_from,
                 hashlib.sha256(encoded.encode()).hexdigest(), encoded))
        connection.commit()
    with pytest.raises(ValueError, match='invalid selected AC payload'):
        read(advisory_db, policy)


def test_later_topology_end_narrows_existing_open_period(advisory_db):
    payload, policy = observation(day=date(2026, 9, 21))
    with closing(advisory_db.connect_owner()) as connection:
        store_ac_snapshot(connection, payload, policy)
    earlier = datetime.fromisoformat(payload['window_end']) - timedelta(seconds=1)
    closed = AcEvidencePolicy(policy.cutover, policy.topology_from, earlier)
    with pytest.raises(ValueError, match='topology period'):
        read(advisory_db, closed, date(2026, 9, 21), date(2026, 9, 22))
    exact_end = AcEvidencePolicy(policy.cutover, policy.topology_from,
                                 datetime.fromisoformat(payload['window_end']))
    assert len(read(advisory_db, exact_end, date(2026, 9, 21), date(2026, 9, 22))) == 1


@pytest.mark.parametrize('start,end', [
    (date(2026, 9, 22), date(2026, 9, 22)),
    (date(2026, 9, 22), date(2027, 9, 24)),
])
def test_rejects_unbounded_date_reads_before_io(start, end):
    _, policy = observation()
    with pytest.raises(ValueError, match='1 to 366'):
        read_ac_snapshots(object(), policy=policy, start_date=start,
                          end_date=end, as_of=datetime.now(timezone.utc))
