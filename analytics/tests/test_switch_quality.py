from dataclasses import replace
from datetime import date, timedelta
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from earthship_energy import daily, switch_quality
from earthship_energy.config import load_source_config
from earthship_energy.series import local_day_bounds
import tplink_switch_history


def test_exact_switch_policy_cutover_and_identity(tmp_path):
    path = Path(__file__).resolve().parents[1] / 'config/switch-evidence.json'
    policy = switch_quality.load_switch_policy(path)
    assert policy.cutover.isoformat() == '2026-09-28T16:36:40.989000+00:00'
    payload = json.loads(path.read_text())
    for change in [dict(item_name='Dish_Washer_Power'), dict(basis='item_state_only'),
                   dict(fields=['load.dishwasher_state']), dict(cutover='2026-09-28T16:36:40')]:
        invalid = tmp_path / 'invalid.json'
        invalid.write_text(json.dumps({**payload, **change}))
        with pytest.raises(ValueError, match='cannot load valid'):
            switch_quality.load_switch_policy(invalid)


def test_switch_adapter_uses_restricted_source_receipts_not_numeric_stats(monkeypatch):
    start, end = local_day_bounds(date(2026, 9, 29), 'America/Denver')
    calls = []
    from earthship_energy import db
    monkeypatch.setattr(db, 'parse_openhab_jdbc_config',
                        lambda _path: SimpleNamespace(connect_kwargs={}))
    def read(factory, **kwargs):
        calls.append(kwargs)
        assert callable(factory)
        return {
            'source_item': 'TPLink_Switch_Evidence_JSON',
            'source_cutover': start.isoformat(), 'evidence_rows': 1440,
            'fields': {name: {'coverage': 1.0, 'covered_seconds': 86400,
                              'window_seconds': 86400, 'observed_on_seconds': 7200,
                              'gap_count': 0, 'unavailable_barriers': 0,
                              'quality': 'ok'}
                       for name in switch_quality.SWITCH_SOURCES},
        }
    monkeypatch.setattr(tplink_switch_history, 'fetch_qualified_switch_day', read)
    stats = {name: (1, start, end) for name in switch_quality.SWITCH_SOURCES}
    result = switch_quality.read_switch_quality('/private/reader',
        local_date=date(2026, 9, 29), assessed_at=end, cutover=start,
        site_timezone='America/Denver', statistics=stats)
    assert len(calls) == 1
    assert result['load.dishwasher_state']['quality'] == 'ok'
    assert result['load.dishwasher_state']['row_count'] == 1
    assert result['load.dishwasher_state']['detail']['evidence_rows'] == 1440
    assert result['load.dishwasher_state']['detail']['row_count_basis'] == 'change_only_switch_item'


def test_daily_switch_opt_in_uses_receipt_on_hours_and_rows(monkeypatch):
    config = load_source_config()
    config = replace(config, sources=tuple(
        replace(source, stale_policy='status_must_equal_OK', freshness_item='BMS_Comms_Status')
        if source.canonical_name == 'battery.soc_pct' else source for source in config.sources))
    tables = {name: f'item{i:04d}' for i, name in enumerate(sorted(daily.REQUIRED_DAILY), 1)}
    tables.update({'load.dishwasher_state': 'item0098',
                   'load.shurflo_pump_state': 'item0099'})
    resolved = [SimpleNamespace(canonical_name=name, table_name=table)
                for name, table in tables.items()]
    day = date(2026, 9, 29)
    start, end = local_day_bounds(day, config.timezone)
    options = dict(switch_evidence_db_config='/private/reader',
                   switch_evidence_cutover=start - timedelta(days=1),
                   switch_evidence_assessed_at=end)
    with pytest.raises(ValueError, match='complete switch evidence'):
        daily.build_daily_snapshot(object(), config, resolved, day,
                                   switch_evidence_db_config='/private/reader')
    with pytest.raises(ValueError, match='elapsed local day'):
        daily.build_daily_snapshot(object(), config, resolved, day,
            **{**options, 'switch_evidence_assessed_at': start})

    calls = []
    quality_by_name = {name: 'ok' for name in switch_quality.SWITCH_SOURCES}
    def read(*_args, **kwargs):
        calls.append(kwargs)
        return {name: {'canonical_name': name, 'row_count': 1,
                       'first_at': start, 'last_at': end,
                       'coverage': 1.0, 'stale_intervals': 0,
                       'quality': quality_by_name[name],
                       'detail': {'observed_on_seconds': 7200 if name == 'load.dishwasher_state' else 0}}
                for name in switch_quality.SWITCH_SOURCES}
    monkeypatch.setattr(daily, 'read_switch_quality', read)
    monkeypatch.setattr(daily, 'fetch_numeric_series', lambda *_args: [])
    monkeypatch.setattr(daily, 'fetch_text_series', lambda *_args: [])
    monkeypatch.setattr(daily, 'fetch_observation_stats', lambda *_args: (1, start, end))
    monkeypatch.setattr(daily, 'fetch_snow_state_as_of', lambda *_args: None)
    result = daily.build_daily_snapshot(object(), config, resolved, day, **options)
    assert len(calls) == 1
    assert calls[0]['statistics']['load.dishwasher_state'] == (1, start, end)
    assert result['load']['active_loads']['dishwasher'] == {
        'state_on_hours': 2.0, 'measurement': 'source_bound_switch_observed',
        'energy_kwh': None}
    assert next(row for row in result['source_quality']
                if row['canonical_name'] == 'load.dishwasher_state')['quality'] == 'ok'
    quality_by_name['load.dishwasher_state'] = 'partial'
    partial = daily.build_daily_snapshot(object(), config, resolved, day, **options)
    assert partial['load']['active_loads']['dishwasher'] == {
        'state_on_hours': None, 'measurement': 'withheld_incomplete_switch_evidence',
        'energy_kwh': None}


def test_unavailable_switch_evidence_fails_closed(monkeypatch):
    from earthship_energy import db
    monkeypatch.setattr(db, 'parse_openhab_jdbc_config',
                        lambda _path: SimpleNamespace(connect_kwargs={}))
    monkeypatch.setattr(tplink_switch_history, 'fetch_qualified_switch_day',
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            RuntimeError('history unavailable')))
    day = date(2026, 9, 29)
    start, end = local_day_bounds(day, 'America/Denver')
    with pytest.raises(RuntimeError, match='history unavailable'):
        switch_quality.read_switch_quality('/private/reader', local_date=day,
            assessed_at=end, cutover=start, site_timezone='America/Denver',
            statistics={name: (0, None, None) for name in switch_quality.SWITCH_SOURCES})
