"""Append-only qualified daily revisions, isolated from legacy daily estimates."""
from datetime import date, datetime
import hashlib
import json
from math import isfinite

from .power_evidence import BOUNDS, utc

POLICY = 'qualified_power_evidence_v1'


def _json_date(value):
    if isinstance(value, datetime):
        return utc(value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError('unsupported snapshot value')


def encode_snapshot(snapshot):
    if snapshot.get('status') != 'ok' or snapshot.get('mode') != 'read_only_dry_run':
        raise ValueError('successful read-only snapshot required')
    basis = snapshot.get('power_accounting', {})
    if (type(basis.get('version')) is not int or basis['version'] != 1
            or basis.get('policy') != POLICY or basis.get('qualified_fields') != sorted(BOUNDS)):
        raise ValueError('qualified accounting provenance required')
    local_date = date.fromisoformat(snapshot['local_date'])
    if local_date.isoformat() != snapshot['local_date']:
        raise ValueError('canonical local date required')
    cutover = utc(datetime.fromisoformat(basis['cutover']))
    start, end = (utc(datetime.fromisoformat(snapshot[key])) for key in ('window_start','window_end'))
    if end <= start or end <= cutover:
        raise ValueError('invalid qualified accounting window')
    for group, fields in (
        ('battery', ('daily_efc','charge_kwh','discharge_kwh','coverage')),
        ('pv', ('energy_kwh','output_energy_kwh','coverage')),
    ):
        for field in fields:
            value = snapshot[group][field]
            if type(value) not in (int,float) or not isfinite(value) or value < 0:
                raise ValueError('invalid qualified accounting value')
        if snapshot[group]['coverage'] > 1:
            raise ValueError('invalid qualified coverage')
    if snapshot['balance'] != {'pv_load_ratio': None, 'surplus_deficit_kwh': None}:
        raise ValueError('unqualified AC balance cannot be published as qualified')
    encoded = json.dumps(snapshot, sort_keys=True, separators=(',', ':'),
                         allow_nan=False, default=_json_date)
    # Leave room for PostgreSQL jsonb text spacing in its independent size guard.
    if len(encoded.encode()) > 48000:
        raise ValueError('qualified snapshot exceeds size budget')
    return local_date, cutover, encoded, hashlib.sha256(encoded.encode()).hexdigest()


def store_power_snapshot(connection, snapshot, epoch_id):
    local_date, cutover, encoded, digest = encode_snapshot(snapshot)
    if connection.autocommit:
        raise ValueError('qualified snapshot writes require a transaction')
    try:
        with connection.cursor() as cursor:
            # Serialize revision insert + cumulative read within one accounting
            # series. Hash collisions only cause unnecessary serialization.
            cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                           (json.dumps([epoch_id, POLICY, cutover.isoformat()]),))
            cursor.execute('''INSERT INTO energy_analytics.daily_power_snapshots
                (local_date, epoch_id, policy, cutover_at, payload_sha256, payload)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (epoch_id, local_date, policy, cutover_at, payload_sha256)
                DO NOTHING RETURNING snapshot_id''',
                (local_date, epoch_id, POLICY, cutover, digest, encoded))
            inserted = cursor.fetchone()
            cursor.execute('''SELECT snapshot_id, payload FROM energy_analytics.daily_power_snapshots
                WHERE epoch_id=%s AND local_date=%s AND policy=%s AND cutover_at=%s
                  AND payload_sha256=%s''', (epoch_id, local_date, POLICY, cutover, digest))
            stored = cursor.fetchone()
            if stored is None or stored[1] != json.loads(encoded):
                raise ValueError('qualified snapshot readback mismatch')
            cursor.execute('''SELECT COALESCE(sum((payload->'battery'->>'daily_efc')::numeric),0)
                FROM (SELECT DISTINCT ON (local_date) local_date, payload
                      FROM energy_analytics.daily_power_snapshots
                      WHERE epoch_id=%s AND policy=%s AND cutover_at=%s AND local_date<=%s
                      ORDER BY local_date, snapshot_id DESC) AS latest''',
                (epoch_id, POLICY, cutover, local_date))
            cumulative = float(cursor.fetchone()[0])
            if not isfinite(cumulative) or cumulative < 0:
                raise ValueError('invalid qualified cumulative EFC')
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {'local_date': local_date.isoformat(), 'epoch_id': epoch_id,
            'tables_written': 1, 'snapshot_id': stored[0], 'inserted': inserted is not None,
            'accounting_policy': POLICY, 'cutover': cutover.isoformat(),
            'cumulative_efc': cumulative, 'cumulative_basis': 'observed_qualified_throughput',
            'source_quality_rows': len(snapshot.get('source_quality', []))}
