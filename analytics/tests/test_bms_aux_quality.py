from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from earthship_energy import bms_aux_quality, daily
from earthship_energy import scheduled
from earthship_energy.config import load_source_config
from earthship_energy.series import local_day_bounds
from earthship_energy.ui_reader import fetch_live_subsystem_health
import bms_aux_history


def test_policy_rejects_drift_and_duplicate_keys(tmp_path):
    payload = {
        'version': 1, 'policy': 'source_bound_bms_aux_v1',
        'item_name': 'BMS_Aux_Evidence_JSON',
        'basis': 'discover_bms_190_native_aux_v1',
        'fields': ['battery.remaining_ah', 'battery.temperature_raw'],
        'cutover': '2026-09-29T05:14:00+00:00',
    }
    path = tmp_path / 'policy.json'
    path.write_text(json.dumps(payload))
    assert bms_aux_quality.load_bms_aux_policy(path).cutover.utcoffset() is not None
    for update in ({'basis': 'device_present'}, {'fields': ['battery.temperature_c']},
                   {'cutover': '2026-09-29T05:14:00'}):
        path.write_text(json.dumps({**payload, **update}))
        with pytest.raises(ValueError, match='cannot load valid'):
            bms_aux_quality.load_bms_aux_policy(path)
    path.write_text(json.dumps(payload)[:-1] + ',"version":1}')
    with pytest.raises(ValueError, match='cannot load valid'):
        bms_aux_quality.load_bms_aux_policy(path)


def test_checked_in_policy_pins_first_durable_production_receipt():
    path = Path(__file__).resolve().parents[1] / 'config/bms-aux-evidence.json'
    policy = bms_aux_quality.load_bms_aux_policy(path)
    assert policy.cutover.isoformat() == '2026-09-29T05:14:44.776000+00:00'


def test_restricted_reader_maps_both_fields_and_refuses_identity_drift(monkeypatch):
    start, end = local_day_bounds(date(2026, 9, 29), 'America/Denver')
    from earthship_energy import db
    monkeypatch.setattr(db, 'parse_openhab_jdbc_config',
                        lambda _path: SimpleNamespace(connect_kwargs={}))
    result = {
        'source_item': 'BMS_Aux_Evidence_JSON',
        'source_cutover': start.isoformat(), 'evidence_rows': 700,
        'fields': {name: {'coverage': 0.95, 'covered_seconds': 82080,
                          'window_seconds': 86400, 'gap_count': 1,
                          'unavailable_barriers': 1, 'quality': 'partial'}
                   for name in bms_aux_quality.FIELDS.values()},
    }
    monkeypatch.setattr(bms_aux_history, 'fetch_qualified_bms_aux_day',
                        lambda factory, **_kwargs: result)
    stats = {name: (5, start, end) for name in bms_aux_quality.FIELDS}
    quality = bms_aux_quality.read_bms_aux_quality(
        '/private/reader', local_date=date(2026, 9, 29), assessed_at=end,
        cutover=start, site_timezone='America/Denver', statistics=stats)
    assert quality['battery.temperature_c']['detail']['evidence_field'] == 'battery.temperature_raw'
    assert quality['battery.remaining_ah']['detail']['row_count_basis'] == 'change_only_numeric_item'
    result['source_item'] = 'BMS_DevicePresent'
    with pytest.raises(ValueError, match='identity mismatch'):
        bms_aux_quality.read_bms_aux_quality(
            '/private/reader', local_date=date(2026, 9, 29), assessed_at=end,
            cutover=start, site_timezone='America/Denver', statistics=stats)


def test_daily_bms_aux_path_is_explicit_and_elapsed_only(monkeypatch):
    config = load_source_config()
    config = replace(config, sources=tuple(
        replace(source, stale_policy='status_must_equal_OK', freshness_item='BMS_Comms_Status')
        if source.canonical_name == 'battery.soc_pct' else source for source in config.sources))
    names = daily.REQUIRED_DAILY | set(bms_aux_quality.FIELDS)
    resolved = [SimpleNamespace(canonical_name=name, table_name=f'item{i:04d}')
                for i, name in enumerate(sorted(names), 1)]
    day = date(2026, 9, 29)
    start, end = local_day_bounds(day, config.timezone)
    options = dict(bms_aux_evidence_db_config='/private/reader',
                   bms_aux_evidence_cutover=start - timedelta(days=1),
                   bms_aux_evidence_assessed_at=end)
    with pytest.raises(ValueError, match='complete BMS auxiliary'):
        daily.build_daily_snapshot(object(), config, resolved, day,
                                   bms_aux_evidence_db_config='/private/reader')
    with pytest.raises(ValueError, match='elapsed local day'):
        daily.build_daily_snapshot(object(), config, resolved, day,
            **{**options, 'bms_aux_evidence_assessed_at': start})

    seen = []
    def read(*_args, **kwargs):
        seen.append(kwargs)
        return {name: {'canonical_name': name, 'row_count': 5,
                       'first_at': start, 'last_at': end,
                       'coverage': 0.8, 'stale_intervals': 2,
                       'quality': 'partial', 'detail': {'policy': 'source_bound_bms_aux_v1'}}
                for name in bms_aux_quality.FIELDS}
    monkeypatch.setattr(daily, 'read_bms_aux_quality', read)
    monkeypatch.setattr(daily, 'fetch_numeric_series', lambda *_args: [])
    monkeypatch.setattr(daily, 'fetch_text_series', lambda *_args: [])
    monkeypatch.setattr(daily, 'fetch_observation_stats', lambda *_args: (5, start, end))
    monkeypatch.setattr(daily, 'fetch_snow_state_as_of', lambda *_args: None)
    snapshot = daily.build_daily_snapshot(object(), config, resolved, day, **options)
    assert len(seen) == 1
    assert set(seen[0]['statistics']) == set(bms_aux_quality.FIELDS)
    for name in bms_aux_quality.FIELDS:
        assert next(row for row in snapshot['source_quality']
                    if row['canonical_name'] == name)['quality'] == 'partial'


def test_unavailable_history_fails_closed(monkeypatch):
    from earthship_energy import db
    monkeypatch.setattr(db, 'parse_openhab_jdbc_config',
                        lambda _path: SimpleNamespace(connect_kwargs={}))
    monkeypatch.setattr(bms_aux_history, 'fetch_qualified_bms_aux_day',
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            RuntimeError('history unavailable')))
    start, end = local_day_bounds(date(2026, 9, 29), 'America/Denver')
    with pytest.raises(RuntimeError, match='history unavailable'):
        bms_aux_quality.read_bms_aux_quality(
            '/private/reader', local_date=date(2026, 9, 29), assessed_at=end,
            cutover=start, site_timezone='America/Denver',
            statistics={name: (0, None, None) for name in bms_aux_quality.FIELDS})


def test_current_aux_receipt_replaces_held_device_present_health():
    now = datetime(2026, 9, 29, 6, 0, tzinfo=timezone.utc)
    ms = lambda at: int(at.timestamp() * 1000)
    epoch = '00000000-0000-0000-0000-000000000001'
    def receipt(sequence, recorded, *, valid):
        fields = {}
        for name, value in (('battery.remaining_ah', 320),
                            ('battery.temperature_raw', 29300)):
            fields[name] = ({'status': 'valid', 'reason': 'ok',
                             'observedAt': ms(recorded),
                             'validUntil': ms(recorded + timedelta(seconds=120)),
                             'value': value}
                            if valid else {'status': 'unavailable',
                                           'reason': 'source_unavailable',
                                           'observedAt': None, 'validUntil': None,
                                           'value': None})
        return json.dumps({'version': 1, 'basis': 'discover_bms_190_native_aux_v1',
                           'streamEpoch': epoch, 'sequence': sequence,
                           'recordedAt': ms(recorded), 'fields': fields})
    previous = (now - timedelta(seconds=30),
                receipt(1, now - timedelta(seconds=31), valid=False))
    latest = (now - timedelta(seconds=1),
              receipt(2, now - timedelta(seconds=2), valid=True))

    class Connection:
        def __init__(self, rows):
            self.rows = rows
            self.queries = []
        def cursor(self):
            outer = self
            class Cursor:
                def __enter__(self): return self
                def __exit__(self, *_): return False
                def execute(self, sql, params): outer.queries.append((sql, params))
                def fetchall(self):
                    return [(658,)] if len(outer.queries) % 2 else outer.rows
            return Cursor()

    cutover = now - timedelta(hours=1)
    connection = Connection([latest, previous])
    health = bms_aux_quality.read_current_bms_aux_health(
        connection, generated_at=now, cutover=cutover)
    assert health == {name: True for name in bms_aux_quality.FIELDS}
    assert all('BMS_DevicePresent' not in sql for sql, _ in connection.queries)

    config = load_source_config()
    config = SimpleNamespace(sources=tuple(source for source in config.sources
        if source.canonical_name in bms_aux_quality.FIELDS))
    resolved = tuple(SimpleNamespace(canonical_name=name, required=True,
        status='ok', freshness_table_name='item0001') for name in bms_aux_quality.FIELDS)
    assert fetch_live_subsystem_health(Connection([latest, previous]), config, resolved,
        generated_at=now, bms_aux_cutover=cutover)['bms'] == 'ok'
    assert scheduled._live_sources_ok(Connection([latest, previous]), config, resolved,
                                      now, bms_aux_cutover=cutover)

    for rows in ([latest], [(latest[0], receipt(4, now - timedelta(seconds=2), valid=True)), previous],
                 [(latest[0], '{bad JSON'), previous]):
        assert not all(bms_aux_quality.read_current_bms_aux_health(
            Connection(rows), generated_at=now, cutover=cutover).values())
        assert fetch_live_subsystem_health(Connection(rows), config, resolved,
            generated_at=now, bms_aux_cutover=cutover)['bms'] == 'fault'
        assert not scheduled._live_sources_ok(Connection(rows), config, resolved,
                                              now, bms_aux_cutover=cutover)
    assert not all(bms_aux_quality.read_current_bms_aux_health(
        Connection([latest, previous]), generated_at=now + timedelta(seconds=119),
        cutover=cutover).values())


def test_current_aux_missing_grant_does_not_fall_back_to_device_present():
    now = datetime(2026, 9, 29, 6, 0, tzinfo=timezone.utc)
    class Connection:
        def cursor(self):
            class Cursor:
                def __enter__(self): return self
                def __exit__(self, *_): return False
                def execute(self, sql, _params):
                    if 'FROM public.item0658' in sql:
                        raise PermissionError('SELECT on item0658 denied')
                def fetchall(self): return [(658,)]
            return Cursor()
    with pytest.raises(PermissionError, match='item0658 denied'):
        bms_aux_quality.read_current_bms_aux_health(
            Connection(), generated_at=now, cutover=now - timedelta(hours=1))
