"""Optional supporting load-switch quality from source-bound TP-Link receipts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


SWITCH_SOURCES = ('load.dishwasher_state', 'load.shurflo_pump_state')
POLICY = 'source_bound_tplink_switch_v1'


@dataclass(frozen=True)
class SwitchEvidencePolicy:
    cutover: datetime


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate switch policy key')
        result[key] = value
    return result


def load_switch_policy(path) -> SwitchEvidencePolicy:
    """Load an exact, secret-free source identity and activation cutover."""
    try:
        with Path(path).open('rb') as handle:
            raw = handle.read(4097)
        if len(raw) > 4096:
            raise ValueError('oversized switch policy')
        payload = json.loads(raw, object_pairs_hook=_unique)
        if (not isinstance(payload, dict) or set(payload) != {
                'version', 'policy', 'item_name', 'basis', 'fields', 'cutover'}
                or type(payload['version']) is not int or payload['version'] != 1
                or payload['policy'] != POLICY
                or payload['item_name'] != 'TPLink_Switch_Evidence_JSON'
                or payload['basis'] != 'tplink_hs103_switch_report_v1'
                or payload['fields'] != list(SWITCH_SOURCES)
                or not isinstance(payload['cutover'], str)):
            raise ValueError('invalid switch policy schema')
        cutover = datetime.fromisoformat(payload['cutover'])
        if cutover.utcoffset() is None:
            raise ValueError('switch cutover must be aware')
        return SwitchEvidencePolicy(cutover=cutover)
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        raise ValueError('cannot load valid switch evidence policy') from exc


def read_switch_quality(
    db_config_path, *, local_date, assessed_at: datetime, cutover: datetime,
    site_timezone: str, statistics: dict[str, tuple[int, datetime | None, datetime | None]],
) -> dict[str, dict[str, object]]:
    """Fail closed on missing rights, incomplete days, or receipt drift."""
    import psycopg2
    from tplink_switch_history import fetch_qualified_switch_day

    from .db import parse_openhab_jdbc_config

    settings = parse_openhab_jdbc_config(db_config_path)
    result = fetch_qualified_switch_day(
        lambda: psycopg2.connect(**settings.connect_kwargs, connect_timeout=3),
        local_date=local_date, as_of=assessed_at, cutover=cutover,
        site_timezone=site_timezone,
    )
    if set(result['fields']) != set(SWITCH_SOURCES):
        raise ValueError('switch evidence field identity mismatch')
    output = {}
    for name in SWITCH_SOURCES:
        field = result['fields'][name]
        row_count, first_at, last_at = statistics[name]
        output[name] = {
            'canonical_name': name,
            'row_count': row_count,
            'first_at': first_at,
            'last_at': last_at,
            'coverage': field['coverage'],
            'stale_intervals': field['gap_count'],
            'quality': field['quality'],
            'detail': {
                'policy': 'source_bound_tplink_switch_v1',
                'freshness_basis': result['source_item'],
                'valid_seconds': field['covered_seconds'],
                'window_seconds': field['window_seconds'],
                'observed_on_seconds': field['observed_on_seconds'],
                'unavailable_barriers': field['unavailable_barriers'],
                'evidence_rows': result['evidence_rows'],
                'source_cutover': result['source_cutover'],
                'row_count_basis': 'change_only_switch_item',
            },
        }
    return output
