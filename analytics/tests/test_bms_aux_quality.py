from dataclasses import replace
from datetime import date, timedelta
import json
from types import SimpleNamespace

import pytest

from earthship_energy import bms_aux_quality, daily
from earthship_energy.config import load_source_config
from earthship_energy.series import local_day_bounds
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
