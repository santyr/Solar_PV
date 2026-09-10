"""Atomic BMS evidence, preserving persistence time, expiry and coverage gaps.

These intervals authorize only their own SoC value, never another Item's carry.
No I/O, cache, bank accounting or notification policy belongs in this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from uuid import UUID

UTC = timezone.utc
UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
FIELDS = frozenset(('version', 'streamEpoch', 'recordedAt', 'status', 'reason',
                    'observedAt', 'scaleObservedAt', 'validUntil', 'soc'))
UNAVAILABLE_REASONS = frozenset(('source_unavailable', 'input_unavailable',
                                 'input_stale', 'invalid_scaled_soc'))


class EvidenceSequenceError(ValueError):
    """Ambiguous evidence order; consumers must not authorize this window."""


def _utc(at: datetime) -> datetime:
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError('evidence timestamps must be timezone-aware')
    return at.astimezone(UTC)


def _milliseconds(value: object) -> datetime:
    if type(value) is not int or not 0 < value <= 2**53 - 1:
        raise ValueError('invalid UTC millisecond timestamp')
    return UNIX_EPOCH + timedelta(milliseconds=value)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


@dataclass(frozen=True)
class EvidenceRecord:
    stream_epoch: str
    recorded_at: datetime
    status: str
    reason: str
    observed_at: datetime | None
    scale_observed_at: datetime | None
    valid_until: datetime | None
    soc: float | None


@dataclass(frozen=True)
class SocInterval:
    start: datetime
    end: datetime
    persisted_at: datetime
    record: EvidenceRecord

    @property
    def soc(self) -> float:
        assert self.record.soc is not None
        return self.record.soc


def parse_evidence(raw: str, persisted_at: datetime) -> EvidenceRecord | None:
    """Return None for malformed/unqualified records; callers must retain the barrier."""
    persisted_at = _utc(persisted_at)
    try:
        if not isinstance(raw, str) or len(raw) > 4096:
            return None
        value = json.loads(raw, object_pairs_hook=_unique_object)
        if not isinstance(value, dict) or set(value) != FIELDS:
            return None
        if type(value['version']) is not int or value['version'] != 1:
            return None
        epoch = value['streamEpoch']
        if not isinstance(epoch, str) or str(UUID(epoch)) != epoch:
            return None
        recorded = _milliseconds(value['recordedAt'])
        if recorded > persisted_at:
            return None
        if value['status'] == 'unavailable':
            if value['reason'] not in UNAVAILABLE_REASONS or any(
                value[key] is not None for key in ('observedAt', 'scaleObservedAt', 'validUntil', 'soc')
            ):
                return None
            return EvidenceRecord(epoch, recorded, 'unavailable', value['reason'], None, None, None, None)
        if value['status'] != 'valid' or value['reason'] != 'ok':
            return None
        observed = _milliseconds(value['observedAt'])
        scale = _milliseconds(value['scaleObservedAt'])
        until = _milliseconds(value['validUntil'])
        soc = value['soc']
        if (max(observed, scale) > recorded
            or until != min(observed, scale) + timedelta(seconds=120)
            or recorded > until or type(soc) not in (int, float)
            or not math.isfinite(soc) or not 0 <= soc <= 100):
            return None
        return EvidenceRecord(epoch, recorded, 'valid', 'ok', observed, scale, until, float(soc))
    except (ValueError, TypeError, OverflowError, RecursionError):
        return None


def build_soc_intervals(
    observations: list[tuple[datetime, str]],
    window_start: datetime,
    window_end: datetime,
    *,
    epoch_start: datetime,
    epoch_end: datetime | None = None,
) -> list[SocInterval]:
    """Build half-open qualified segments within a physical-bank/window intersection.

    Input must be persistence-ordered, including original carry-in if present.
    Ambiguous sequence order raises ValueError: callers must mark it unqualified,
    not retry with sorted/deduplicated data or fall back to legacy numeric history.
    Malformed rows are explicit barriers at persistence time. Well-formed records
    bound the preceding segment at recordedAt, leaving publication-delay gaps.
    """
    start, end = _utc(window_start), _utc(window_end)
    bank_start = _utc(epoch_start)
    bank_end = _utc(epoch_end) if epoch_end is not None else end
    if end <= start or (epoch_end is not None and bank_end <= bank_start):
        raise ValueError('windows and bank epochs must be positive')
    left, right = max(start, bank_start), min(end, bank_end)
    if right <= left:
        return []
    result: list[SocInterval] = []
    pending: tuple[datetime, EvidenceRecord] | None = None
    last_persisted = None
    last_record = None
    last_boundary = None
    retired_epochs: set[str] = set()

    def finish(boundary):
        if pending is None:
            return
        persisted, record = pending
        begin = max(left, persisted, record.recorded_at)
        stop = min(right, record.valid_until, boundary)
        if stop > begin:
            result.append(SocInterval(begin, stop, persisted, record))

    for persisted, raw in observations:
        persisted = _utc(persisted)
        if last_persisted is not None and persisted <= last_persisted:
            raise EvidenceSequenceError('duplicate or out-of-order persistence timestamps')
        last_persisted = persisted
        # A post-window record must not rewrite knowledge inside the window.
        if persisted >= right:
            continue
        record = parse_evidence(raw, persisted)
        if record is not None and last_record is not None:
            if record == last_record:
                # Restoring/re-persisting a record never renews its coverage.
                continue
            if record.recorded_at <= last_record.recorded_at:
                raise EvidenceSequenceError('conflicting or out-of-order record timestamps')
            if record.stream_epoch != last_record.stream_epoch:
                retired_epochs.add(last_record.stream_epoch)
                if record.stream_epoch in retired_epochs:
                    raise EvidenceSequenceError('retired observer epoch reappeared')
        boundary = record.recorded_at if record is not None else persisted
        if last_boundary is not None and boundary < last_boundary:
            raise EvidenceSequenceError('record predates a known coverage barrier')
        finish(boundary)
        last_boundary = boundary
        belongs_to_bank = (record is not None and record.status == 'valid'
                           and min(record.observed_at, record.scale_observed_at) >= bank_start)
        pending = (persisted, record) if belongs_to_bank else None
        if record is not None:
            last_record = record
    finish(right)
    return result


def soc_at(intervals: list[SocInterval], at: datetime) -> float | None:
    at = _utc(at)
    return next((interval.soc for interval in intervals if interval.start <= at < interval.end), None)
