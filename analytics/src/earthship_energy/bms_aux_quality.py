"""Opt-in daily quality for source-bound Discover BMS auxiliary receipts.

This module does not enable collection or publication. The restricted reader
must be supplied explicitly after its table grant and day-level review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


FIELDS = {'battery.remaining_ah': 'battery.remaining_ah',
          'battery.temperature_c': 'battery.temperature_raw'}
POLICY = 'source_bound_bms_aux_v1'


@dataclass(frozen=True)
class BmsAuxPolicy:
    cutover: datetime


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate BMS auxiliary policy key')
        result[key] = value
    return result


def load_bms_aux_policy(path) -> BmsAuxPolicy:
    """Load an exact, secret-free source identity and activation cutover."""
    try:
        with Path(path).open('rb') as handle:
            raw = handle.read(4097)
        if len(raw) > 4096:
            raise ValueError('oversized BMS auxiliary policy')
        payload = json.loads(raw, object_pairs_hook=_unique)
        if (not isinstance(payload, dict) or set(payload) != {
                'version', 'policy', 'item_name', 'basis', 'fields', 'cutover'}
                or type(payload['version']) is not int or payload['version'] != 1
                or payload['policy'] != POLICY
                or payload['item_name'] != 'BMS_Aux_Evidence_JSON'
                or payload['basis'] != 'discover_bms_190_native_aux_v1'
                or payload['fields'] != list(FIELDS.values())
                or not isinstance(payload['cutover'], str)):
            raise ValueError('invalid BMS auxiliary policy schema')
        cutover = datetime.fromisoformat(payload['cutover'])
        if cutover.utcoffset() is None:
            raise ValueError('BMS auxiliary cutover must be aware')
        return BmsAuxPolicy(cutover=cutover)
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        raise ValueError('cannot load valid BMS auxiliary evidence policy') from exc


def read_bms_aux_quality(
    db_config_path, *, local_date, assessed_at: datetime, cutover: datetime,
    site_timezone: str, statistics: dict[str, tuple[int, datetime | None, datetime | None]],
) -> dict[str, dict[str, object]]:
    """Fail closed on unavailable history or a changed field/source identity."""
    import psycopg2
    from bms_aux_history import fetch_qualified_bms_aux_day

    from .db import parse_openhab_jdbc_config

    settings = parse_openhab_jdbc_config(db_config_path)
    result = fetch_qualified_bms_aux_day(
        lambda: psycopg2.connect(**settings.connect_kwargs, connect_timeout=3),
        local_date=local_date, as_of=assessed_at, cutover=cutover,
        site_timezone=site_timezone,
    )
    if (result['source_item'] != 'BMS_Aux_Evidence_JSON'
            or set(result['fields']) != set(FIELDS.values())):
        raise ValueError('BMS auxiliary source or field identity mismatch')
    output = {}
    for canonical, evidence_field in FIELDS.items():
        field = result['fields'][evidence_field]
        row_count, first_at, last_at = statistics[canonical]
        output[canonical] = {
            'canonical_name': canonical,
            'row_count': row_count,
            'first_at': first_at,
            'last_at': last_at,
            'coverage': field['coverage'],
            'stale_intervals': field['gap_count'],
            'quality': field['quality'],
            'detail': {
                'policy': POLICY,
                'freshness_basis': result['source_item'],
                'evidence_field': evidence_field,
                'valid_seconds': field['covered_seconds'],
                'window_seconds': field['window_seconds'],
                'unavailable_barriers': field['unavailable_barriers'],
                'evidence_rows': result['evidence_rows'],
                'source_cutover': result['source_cutover'],
                'row_count_basis': 'change_only_numeric_item',
            },
        }
    return output


def read_current_bms_aux_health(connection, *, generated_at: datetime,
                                cutover: datetime) -> dict[str, bool]:
    """Assess two latest durable receipts, never a held numeric/status Item.

    A missing table grant or mapping raises, so an opted-in publisher cannot
    silently fall back to `BMS_DevicePresent`. Malformed evidence fails closed.
    """
    from bms_aux_evidence import BmsAuxEvidenceRefused, parse_bms_aux_receipt

    from .power_evidence import utc

    now, since = utc(generated_at), utc(cutover)
    if now < since:
        raise ValueError('BMS auxiliary cutover is in the future')
    with connection.cursor() as cursor:
        cursor.execute('SELECT itemid FROM public.items WHERE itemname=%s LIMIT 2',
                       ('BMS_Aux_Evidence_JSON',))
        matches = cursor.fetchall()
        if (len(matches) != 1 or type(matches[0][0]) is not int
                or not 0 <= matches[0][0] <= 2147483647):
            raise ValueError('unique BMS auxiliary Item mapping required')
        table = f'public.item{matches[0][0]:04d}'
        cursor.execute(
            f'SELECT time, CASE WHEN octet_length(value::text) <= 4096 '
            f'THEN value::text ELSE NULL END FROM {table} '
            'WHERE time >= %s AND time <= %s ORDER BY time DESC LIMIT 2',
            (since, now),
        )
        rows = cursor.fetchall()
    unavailable = {name: False for name in FIELDS}
    if len(rows) != 2:
        return unavailable
    try:
        previous, latest = [parse_bms_aux_receipt(raw, persisted)
                            for persisted, raw in reversed(rows)]
    except BmsAuxEvidenceRefused:
        return unavailable
    if (previous.persisted_at >= latest.persisted_at
            or previous.recorded_at >= latest.recorded_at
            or previous.epoch != latest.epoch
            or previous.sequence + 1 != latest.sequence
            or latest.sequence <= 1):
        return unavailable
    return {canonical: (latest.fields[field].status == 'valid'
                        and latest.persisted_at <= now < latest.fields[field].valid_until)
            for canonical, field in FIELDS.items()}
