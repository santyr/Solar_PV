"""Strict historical reader for the observational power-evidence v1 stream.

No I/O or numeric-history fallback. Rows must retain original persistence times.
Malformed rows are barriers, not records to drop before interval construction.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from uuid import UUID

from .power_intervals import PowerInterval

BOUNDS = {'battery.dc_power_w': (-32767, 32767),
          'pv.input_power_w': (0, 4294967294),
          'pv.output_power_w': (0, 4294967294)}
UTC = timezone.utc
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class PowerSequenceError(ValueError):
    """Ambiguous stream; caller must withhold this window, not repair ordering."""


def utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('timestamps must be timezone-aware')
    return value.astimezone(UTC)


def millis(value):
    if type(value) is not int or not 0 < value <= 2**53 - 1:
        raise ValueError('invalid millisecond timestamp')
    return EPOCH + timedelta(milliseconds=value)


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


@dataclass(frozen=True)
class FieldReading:
    observed_at: datetime
    valid_until: datetime
    watts: int


@dataclass(frozen=True)
class PowerRecord:
    stream_epoch: str
    sequence: int
    recorded_at: datetime
    fields: dict[str, FieldReading | None]


def parse_power_evidence(raw: str, persisted_at: datetime) -> PowerRecord | None:
    persisted_at = utc(persisted_at)
    try:
        if not isinstance(raw, str) or len(raw) > 4096:
            return None
        data = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(data, dict) or set(data) != {'version', 'streamEpoch', 'sequence', 'recordedAt', 'fields'}:
            return None
        if type(data['version']) is not int or data['version'] != 1:
            return None
        epoch = data['streamEpoch']
        if not isinstance(epoch, str) or str(UUID(epoch)) != epoch:
            return None
        seq = data['sequence']
        if type(seq) is not int or not 0 < seq <= 2**53 - 1:
            return None
        recorded = millis(data['recordedAt'])
        if recorded > persisted_at or not isinstance(data['fields'], dict) or set(data['fields']) != set(BOUNDS):
            return None
        fields = {}
        for name, (minimum, maximum) in BOUNDS.items():
            field = data['fields'][name]
            if not isinstance(field, dict) or set(field) != {'status', 'reason', 'observedAt', 'validUntil', 'watts'}:
                return None
            if field['status'] == 'unavailable':
                if field['reason'] not in ('input_unavailable', 'input_stale') or any(
                    field[key] is not None for key in ('observedAt', 'validUntil', 'watts')
                ):
                    return None
                fields[name] = None
                continue
            if field['status'] != 'valid' or field['reason'] != 'ok':
                return None
            observed, until = millis(field['observedAt']), millis(field['validUntil'])
            watts = field['watts']
            if (not observed <= recorded < until or until != observed + timedelta(seconds=120)
                    or type(watts) is not int or not minimum <= watts <= maximum):
                return None
            fields[name] = FieldReading(observed, until, watts)
        return PowerRecord(epoch, seq, recorded, fields)
    except (ValueError, TypeError, OverflowError, RecursionError):
        return None


def build_power_intervals(observations, field, window_start, window_end, *, cutover):
    """Return only qualified half-open intervals; publication delays remain gaps.

    Other fields changing do not interrupt an unchanged field. Restored records
    cannot renew coverage. Stream ordering is explicit, including equal-clock
    publications, retired epochs and invalid-row barriers. Cutover is actual
    activation time, never a retrospectively inferred start of historical data.
    """
    if field not in BOUNDS:
        raise ValueError('unknown power field')
    start, end, floor = utc(window_start), utc(window_end), utc(cutover)
    if end <= start:
        raise ValueError('window must be positive')
    left = max(start, floor)
    if left >= end:
        return []
    result = []
    pending = None
    previous = None
    last_persisted = None
    barrier = floor
    last_boundary = None
    retired = set()

    def finish(boundary):
        if pending is None:
            return
        persisted, reading = pending
        begin, stop = max(left, persisted), min(end, reading.valid_until, boundary)
        if stop > begin:
            result.append(PowerInterval(begin, stop, reading.watts))

    for persisted, raw in observations:
        persisted = utc(persisted)
        if last_persisted is not None and persisted <= last_persisted:
            raise PowerSequenceError('duplicate or unordered persistence times')
        last_persisted = persisted
        if persisted >= end:
            continue
        record = parse_power_evidence(raw, persisted)
        if record is None:
            finish(persisted)
            pending = None
            barrier = max(barrier, persisted)
            last_boundary = persisted
            continue
        if previous is not None:
            if record == previous:
                continue
            if record.recorded_at < previous.recorded_at:
                raise PowerSequenceError('record clock regressed')
            if record.stream_epoch == previous.stream_epoch:
                if record.sequence <= previous.sequence:
                    raise PowerSequenceError('record sequence regressed or conflicted')
                if record.sequence > previous.sequence + 1:
                    # Missing publications may contain an invalidation. Retain
                    # earlier proven intervals, but never bridge this gap with
                    # a repeated field carried in the next complete snapshot.
                    finish(previous.recorded_at)
                    pending = None
                    barrier = max(barrier, previous.recorded_at)
            else:
                retired.add(previous.stream_epoch)
                if record.stream_epoch in retired:
                    raise PowerSequenceError('retired epoch reappeared')
                finish(record.recorded_at)
                pending = None
                barrier = max(barrier, previous.recorded_at)
        if last_boundary is not None and record.recorded_at < last_boundary:
            raise PowerSequenceError('record predates known barrier')
        reading = record.fields[field]
        if pending is not None and pending[1] == reading:
            previous = record
            last_boundary = record.recorded_at
            continue
        if pending is not None and reading is not None:
            if reading.observed_at <= pending[1].observed_at:
                raise PowerSequenceError('field acquisition regressed or conflicted')
        finish(record.recorded_at)
        pending = None
        if reading is None:
            barrier = max(barrier, record.recorded_at)
        elif reading.observed_at >= floor and reading.observed_at > barrier:
            pending = (persisted, reading)
        previous = record
        last_boundary = record.recorded_at
    finish(end)
    return result
