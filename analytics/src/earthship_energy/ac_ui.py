"""Exact source-only validation of the independent AC-load UI v4 section.

V4 does not repurpose the power v3 load field or assert a DC/AC balance.
"""
from datetime import date, datetime, timedelta
import re
from zoneinfo import ZoneInfo

from .ac_policy import POLICY
from .ui_payload import _aware, _exact, _integer, _number


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
