"""Exact source-only validation of the independent AC-load UI v4 section.

V4 does not repurpose the power v3 load field or assert a DC/AC balance.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta
import re
from zoneinfo import ZoneInfo

from .ac_policy import AcEvidencePolicy, POLICY
from .ac_store import encode_ac_snapshot
from .power_evidence import utc
from .ui_payload import _aware, _exact, _integer, _number, validate_energy_ui_payload


def validate_ac_load(payload):
    ac = _exact(payload['acLoad'], {'policy', 'cutover', 'topologyFrom',
               'topologyUntil', 'status', 'latest'}, 'acLoad')
    if ac['policy'] != POLICY or ac['status'] not in {'observed', 'partial', 'unavailable'}:
        raise ValueError('invalid AC UI policy or status')
    generated = _aware(payload['generatedAt'], 'generatedAt')
    cutover = _aware(ac['cutover'], 'acLoad.cutover')
    start = _aware(ac['topologyFrom'], 'acLoad.topologyFrom')
    until = (_aware(ac['topologyUntil'], 'acLoad.topologyUntil')
             if ac['topologyUntil'] is not None else None)
    if cutover > start or start > generated or until is not None and until <= start:
        raise ValueError('invalid AC topology period')
    if ac['latest'] is None:
        if ac['status'] != 'unavailable':
            raise ValueError('empty AC series must be unavailable')
        return
    latest = _exact(ac['latest'], {'coverage', 'date', 'observedKwh', 'revision',
                    'windowStart', 'windowEnd'}, 'acLoad.latest')
    if type(latest['date']) is not str:
        raise ValueError('invalid AC date')
    try:
        local_day = date.fromisoformat(latest['date'])
    except ValueError as exc:
        raise ValueError('invalid AC date') from exc
    if local_day.isoformat() != latest['date']:
        raise ValueError('noncanonical AC date')
    zone = ZoneInfo(payload['timezone'])
    window_start = _aware(latest['windowStart'], 'acLoad.windowStart')
    window_end = _aware(latest['windowEnd'], 'acLoad.windowEnd')
    expected_start = datetime.combine(local_day, datetime.min.time(), tzinfo=zone)
    expected_end = datetime.combine(local_day+timedelta(days=1), datetime.min.time(), tzinfo=zone)
    coverage = _number(latest['coverage'], 'acLoad.coverage', optional=False)
    observed = _number(latest['observedKwh'], 'acLoad.observedKwh', optional=False)
    revision = _exact(latest['revision'], {'id', 'sha256', 'computedAt'}, 'acLoad.revision')
    revision_id = _integer(revision['id'], 'acLoad.revision.id', optional=False)
    computed = _aware(revision['computedAt'], 'acLoad.revision.computedAt')
    if (not 0 < coverage <= 1 or observed < 0 or not 0 < revision_id <= 2**53-1
            or type(revision['sha256']) is not str
            or re.fullmatch('[a-f0-9]{64}', revision['sha256']) is None
            or window_start != expected_start or window_end != expected_end
            or window_start < cutover or window_start < start
            or until is not None and window_end > until
            or not window_end <= computed <= generated
            or local_day >= generated.astimezone(zone).date()
            or ac['status'] != ('observed' if coverage >= .9 else 'partial')):
        raise ValueError('invalid AC UI revision')


def build_ac_ui_payload(qualified_v3, *, policy, ac_rows):
    """Project selected immutable AC revisions without changing v3 load/balance.

    `ac_rows` comes from the bounded latest-revision reader. Revalidate the
    selected row here so direct callers cannot fabricate a UI observation.
    """
    if type(policy) is not AcEvidencePolicy or type(ac_rows) is not list or len(ac_rows) > 366:
        raise ValueError('invalid AC UI inputs')
    if qualified_v3.get('schema') != 'earthship-energy-ui/v3':
        raise ValueError('qualified v3 base required')
    validate_energy_ui_payload(qualified_v3)
    result = deepcopy(qualified_v3)
    generated = _aware(result['generatedAt'], 'generatedAt')
    if any(type(row) is not dict or type(row.get('local_date')) is not date for row in ac_rows):
        raise ValueError('invalid AC revisions')
    if any(a['local_date'] >= b['local_date'] for a, b in zip(ac_rows, ac_rows[1:])):
        raise ValueError('AC revision days must be ordered and unique')
    latest = None
    if ac_rows:
        row = _exact(ac_rows[-1], {'snapshot_id', 'local_date', 'policy', 'cutover',
                    'topology_from', 'computed_at', 'payload_sha256', 'payload'}, 'AC revision')
        snapshot = row['payload']
        stored_until = (None if snapshot['topology_until'] is None else
                        _aware(snapshot['topology_until'], 'AC stored topology end'))
        original_policy = AcEvidencePolicy(policy.cutover, policy.topology_from, stored_until)
        day, _, window_end, _, digest = encode_ac_snapshot(snapshot, original_policy)
        policy.day_window(day, as_of=generated)
        computed = utc(row['computed_at'])
        if (row['policy'] != POLICY or row['cutover'] != utc(policy.cutover)
                or row['topology_from'] != utc(policy.topology_from)
                or row['local_date'] != day or row['payload_sha256'] != digest
                or type(row['snapshot_id']) is not int or not 0 < row['snapshot_id'] <= 2**53-1
                or not window_end <= computed <= generated):
            raise ValueError('AC revision identity mismatch')
        if snapshot['observed_ac_load_kwh'] is not None:
            latest = {'date': day.isoformat(), 'windowStart': snapshot['window_start'],
                      'windowEnd': snapshot['window_end'],
                      'observedKwh': snapshot['observed_ac_load_kwh'],
                      'coverage': snapshot['ac_coverage'],
                      'revision': {'id': row['snapshot_id'], 'sha256': digest,
                                   'computedAt': computed.isoformat()}}
    result['schema'] = 'earthship-energy-ui/v4'
    result['acLoad'] = {
        'policy': POLICY, 'cutover': utc(policy.cutover).isoformat(),
        'topologyFrom': utc(policy.topology_from).isoformat(),
        'topologyUntil': (utc(policy.topology_until).isoformat()
                          if policy.topology_until is not None else None),
        'status': ('observed' if latest['coverage'] >= .9 else 'partial')
                  if latest is not None else 'unavailable',
        'latest': latest,
    }
    if latest is not None and result['status'] == 'unavailable':
        result['status'] = 'degraded'
    return validate_energy_ui_payload(result, now=generated)
