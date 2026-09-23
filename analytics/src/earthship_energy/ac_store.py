"""Append-only revisions of completed, topology-qualified AC observations."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
import hashlib
import json
from math import isfinite

from .ac_policy import AcEvidencePolicy, ITEM, POLICY
from .power_evidence import utc

FIELDS = {'local_date', 'window_start', 'window_end', 'ac_item', 'ac_cutover',
          'topology_from', 'topology_until', 'basis', 'observed_ac_load_kwh',
          'ac_coverage', 'common_pv_dc_kwh', 'common_ac_load_kwh',
          'common_coverage', 'balance_kwh', 'balance_reason'}


def _timestamp(value):
    if type(value) is not str:
        raise ValueError('AC snapshot timestamp must be a string')
    return utc(datetime.fromisoformat(value.replace('Z', '+00:00')))


def _quantity(value, label, *, nullable=False, max_value=None):
    if value is None and nullable:
        return None
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError(f'invalid {label}')
    if max_value is not None and value > max_value:
        raise ValueError(f'invalid {label}')
    return value


def encode_ac_snapshot(snapshot, policy):
    """Validate an exact complete-day observation and return immutable identity."""
    if type(policy) is not AcEvidencePolicy or type(snapshot) is not dict or set(snapshot) != FIELDS:
        raise ValueError('invalid AC snapshot or policy')
    local_day = date.fromisoformat(snapshot['local_date'])
    if local_day.isoformat() != snapshot['local_date']:
        raise ValueError('noncanonical AC day')
    start, end = _timestamp(snapshot['window_start']), _timestamp(snapshot['window_end'])
    zone = ZoneInfo('America/Denver')
    expected_start = datetime.combine(local_day, time.min, tzinfo=zone)
    expected_end = datetime.combine(local_day + timedelta(days=1), time.min, tzinfo=zone)
    if start != expected_start or end != expected_end:
        raise ValueError('AC snapshot must cover a complete site-local day')
    policy.day_window(local_day, as_of=end)
    if (snapshot['ac_item'] != ITEM or snapshot['basis'] != 'inverter_output_observed_with_attested_topology'
            or _timestamp(snapshot['ac_cutover']) != utc(policy.cutover)
            or _timestamp(snapshot['topology_from']) != utc(policy.topology_from)
            or (None if snapshot['topology_until'] is None else _timestamp(snapshot['topology_until']))
            != (None if policy.topology_until is None else utc(policy.topology_until))):
        raise ValueError('AC snapshot provenance mismatch')
    ac_coverage = _quantity(snapshot['ac_coverage'], 'AC coverage', max_value=1)
    common_coverage = _quantity(snapshot['common_coverage'], 'common coverage', max_value=1)
    observed = _quantity(snapshot['observed_ac_load_kwh'], 'AC load', nullable=True)
    common_ac = _quantity(snapshot['common_ac_load_kwh'], 'common AC', nullable=True)
    common_pv = _quantity(snapshot['common_pv_dc_kwh'], 'common PV DC', nullable=True)
    if (common_coverage > ac_coverage + 1e-9
            or (observed is None) != (ac_coverage == 0)
            or (common_ac is None) != (common_coverage == 0)
            or (common_pv is None) != (common_coverage == 0)
            or snapshot['balance_kwh'] is not None
            or snapshot['balance_reason'] != ('dc_pv_and_ac_load_cross_domain'
                if common_coverage else 'no_common_qualified_intervals')):
        raise ValueError('AC snapshot coverage or balance conflict')
    encoded = json.dumps(snapshot, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if len(encoded.encode()) > 48000:
        raise ValueError('AC snapshot exceeds size budget')
    return local_day, start, end, encoded, hashlib.sha256(encoded.encode()).hexdigest()


def store_ac_snapshot(connection, snapshot, policy):
    local_day, start, end, encoded, digest = encode_ac_snapshot(snapshot, policy)
    if end > datetime.now(timezone.utc):
        raise ValueError('cannot persist unfinished AC day')
    if connection.autocommit:
        raise ValueError('AC snapshot writes require a transaction')
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                           (json.dumps([POLICY, policy.cutover.isoformat(),
                                        policy.topology_from.isoformat()]),))
            cursor.execute('''INSERT INTO energy_analytics.daily_ac_snapshots
                (local_date, policy, cutover_at, topology_from, payload_sha256, payload)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (local_date, policy, cutover_at, topology_from, payload_sha256)
                DO NOTHING RETURNING snapshot_id''',
                (local_day, POLICY, policy.cutover, policy.topology_from, digest, encoded))
            inserted = cursor.fetchone()
            cursor.execute('''SELECT snapshot_id, payload FROM energy_analytics.daily_ac_snapshots
                WHERE local_date=%s AND policy=%s AND cutover_at=%s AND topology_from=%s
                  AND payload_sha256=%s''',
                (local_day, POLICY, policy.cutover, policy.topology_from, digest))
            stored = cursor.fetchone()
            if stored is None or stored[1] != json.loads(encoded):
                raise ValueError('AC snapshot readback mismatch')
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {'local_date': local_day.isoformat(), 'snapshot_id': stored[0],
            'inserted': inserted is not None, 'policy': POLICY,
            'cutover': utc(policy.cutover).isoformat(), 'payload_sha256': digest}
