"""Strict, separate inverter-output evidence contract; not household-load authority."""
from datetime import timedelta
import json
from uuid import UUID

from .power_evidence import FieldReading, PowerRecord, build_power_intervals, millis, unique, utc

FIELD = 'inverter.ac_output_w'
BOUNDS = {FIELD: (0, 20000)}
UNAVAILABLE = {'source_unavailable', 'input_unavailable', 'invalid_input', 'input_stale'}


def parse_ac_evidence(raw, persisted_at):
    persisted_at = utc(persisted_at)
    try:
        if not isinstance(raw, str) or len(raw) > 4096:
            return None
        data = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(data, dict) or set(data) != {
            'version', 'basis', 'streamEpoch', 'sequence', 'recordedAt', 'fields'
        } or type(data['version']) is not int or data['version'] != 1 or data['basis'] != 'inverter_output':
            return None
        epoch, seq = data['streamEpoch'], data['sequence']
        if not isinstance(epoch, str) or str(UUID(epoch)) != epoch:
            return None
        if type(seq) is not int or not 0 < seq <= 2**53 - 1:
            return None
        recorded = millis(data['recordedAt'])
        if recorded > persisted_at or not isinstance(data['fields'], dict) or set(data['fields']) != {FIELD}:
            return None
        field = data['fields'][FIELD]
        if not isinstance(field, dict) or set(field) != {
            'status', 'reason', 'observedAt', 'validUntil', 'watts'
        }:
            return None
        if field['status'] == 'unavailable':
            if field['reason'] not in UNAVAILABLE or any(
                field[key] is not None for key in ('observedAt', 'validUntil', 'watts')
            ):
                return None
            reading = None
        elif field['status'] == 'valid' and field['reason'] == 'ok':
            observed, until = millis(field['observedAt']), millis(field['validUntil'])
            watts = field['watts']
            if (not observed <= recorded < until
                    or until != observed + timedelta(seconds=30)
                    or type(watts) is not int or not 0 <= watts <= 20000):
                return None
            reading = FieldReading(observed, until, watts)
        else:
            return None
        return PowerRecord(epoch, seq, recorded, {FIELD: reading})
    except (ValueError, TypeError, OverflowError, RecursionError):
        return None


def build_ac_intervals(observations, window_start, window_end, *, cutover,
                       topology_start, topology_end):
    """Qualify only the overlap with an explicitly finite inverter-only period.

    Caller must independently verify the period; this module does not infer
    household topology from an AC value or apply it to prior history.
    """
    start, end = utc(window_start), utc(window_end)
    floor, topology_floor, topology_ceiling = map(utc, (cutover, topology_start, topology_end))
    if end <= start or topology_ceiling <= topology_floor:
        raise ValueError('invalid window or inverter-only topology period')
    left, right = max(start, floor, topology_floor), min(end, topology_ceiling)
    if left >= right:
        return []
    return build_power_intervals(observations, FIELD, left, right,
                                 cutover=max(floor, topology_floor),
                                 parser=parse_ac_evidence, bounds=BOUNDS)
