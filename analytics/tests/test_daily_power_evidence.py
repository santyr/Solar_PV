from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from earthship_energy import daily
from earthship_energy.config import load_source_config
from earthship_energy.power_intervals import PowerInterval
from earthship_energy.series import local_day_bounds


@pytest.fixture
def setup_daily(monkeypatch):
    config = load_source_config()
    config = replace(config, sources=tuple(
        replace(s, stale_policy='status_must_equal_OK', freshness_item='BMS_Comms_Status')
        if s.canonical_name == 'battery.soc_pct' else s for s in config.sources))
    resolved = [SimpleNamespace(canonical_name=n, table_name='item'+str(i+1).zfill(4))
                for i, n in enumerate(sorted(daily.REQUIRED_DAILY))]
    start, end = local_day_bounds(date(2026, 9, 21), config.timezone)
    tables = {s.table_name: s.canonical_name for s in resolved}
    reads = []
    def numeric(_, table, left, right):
        reads.append(tables[table])
        value = 75 if tables[table] == 'battery.soc_pct' else 1000
        return [(left, value), (right, value)]
    monkeypatch.setattr(daily, 'fetch_numeric_series', numeric)
    monkeypatch.setattr(daily, 'fetch_observation_stats', lambda *_: (5, start, end))
    monkeypatch.setattr(daily, 'fetch_snow_state_as_of', lambda *_: None)
    fields = {name: [PowerInterval(start, start+timedelta(seconds=120), 1000)]
              for name in ('battery.dc_power_w','pv.input_power_w','pv.output_power_w')}
    calls = []
    def reader(*args, **kwargs):
        calls.append((args, kwargs))
        return fields
    monkeypatch.setattr(daily, 'read_power_history', reader)
    kwargs = dict(power_evidence_settings=object(), power_evidence_table='item0648',
                  power_evidence_cutover=start)
    return config, resolved, start, end, reads, fields, calls, kwargs


def run(parts):
    config, resolved, *_, kwargs = parts
    return daily.build_daily_snapshot(object(), config, resolved, date(2026,9,21), **kwargs)


def test_daily_energy_and_quality_share_intervals_not_held_numeric_history(setup_daily):
    result = run(setup_daily)
    _, _, start, end, reads, fields, calls, _ = setup_daily
    assert len(calls) == 1
    assert not set(fields).intersection(reads)
    assert result['pv']['energy_kwh'] == pytest.approx(1/30)
    assert result['pv']['output_energy_kwh'] == pytest.approx(1/30)
    assert result['battery']['charge_kwh']+result['battery']['discharge_kwh'] == pytest.approx(1/30)
    assert result['battery']['daily_efc'] == pytest.approx((1/30)/(2*20.48))
    quality = {r['canonical_name']:r for r in result['source_quality']}
    for name in fields:
        assert quality[name]['coverage'] == pytest.approx(120/(end-start).total_seconds())
        assert quality[name]['detail']['policy'] == 'qualified_power_evidence_v1'
    assert result['power_accounting']['policy'] == 'qualified_power_evidence_v1'
    assert result['balance']['pv_load_ratio'] is None
    assert result['balance']['surplus_deficit_kwh'] is None


def test_empty_evidence_cannot_recover_from_numeric_history(setup_daily):
    for name in setup_daily[5]: setup_daily[5][name] = []
    result = run(setup_daily)
    assert result['pv']['energy_kwh'] == result['battery']['daily_efc'] == 0
    assert result['pv']['coverage'] == 0
    assert result['pv']['quality'] == 'insufficient_data'


def test_pre_cutover_day_is_explicit_legacy_and_does_not_read_evidence(setup_daily):
    setup_daily[-1]['power_evidence_cutover'] = setup_daily[3]
    result = run(setup_daily)
    assert not setup_daily[6]
    assert result['pv']['energy_kwh'] == 24
    assert result['power_accounting']['policy'] == 'legacy_numeric_estimate'


@pytest.mark.parametrize('missing', ['power_evidence_settings','power_evidence_table','power_evidence_cutover'])
def test_partial_configuration_refuses_silent_legacy_fallback(setup_daily, missing):
    setup_daily[-1].pop(missing)
    with pytest.raises(ValueError, match='complete power evidence configuration'):
        run(setup_daily)


def test_reader_failure_propagates_without_publishing_a_fallback(setup_daily, monkeypatch):
    def broken(*args, **kwargs): raise RuntimeError('reader unavailable')
    monkeypatch.setattr(daily, 'read_power_history', broken)
    with pytest.raises(RuntimeError, match='reader unavailable'):
        run(setup_daily)


def test_solar_noon_energy_uses_qualified_segments_on_each_side(setup_daily, monkeypatch):
    _, resolved, start, _, reads, fields, _, _ = setup_daily
    resolved.extend([
        SimpleNamespace(canonical_name='solar.sunrise_at', table_name='item0901'),
        SimpleNamespace(canonical_name='solar.sunset_at', table_name='item0902'),
    ])
    def times(_, table, left, right):
        hour = '07' if table == 'item0901' else '19'
        return [(left, '2026-09-21T'+hour+':00:00-06:00')]
    monkeypatch.setattr(daily, 'fetch_text_series', times)
    fields['pv.input_power_w'] = [
        PowerInterval(start+timedelta(hours=11), start+timedelta(hours=12), 1000),
        PowerInterval(start+timedelta(hours=13), start+timedelta(hours=14), 2000),
    ]
    result = run(setup_daily)
    assert result['pv']['before_solar_noon_kwh'] == 1
    assert result['pv']['after_solar_noon_kwh'] == 2
    assert 'pv.input_power_w' not in reads


def test_partial_reader_field_map_is_rejected(setup_daily):
    setup_daily[5].pop('pv.output_power_w')
    with pytest.raises(ValueError, match='incomplete qualified power history'):
        run(setup_daily)


def test_efficiency_uses_common_support_not_separate_daily_totals(setup_daily):
    start = setup_daily[2]
    setup_daily[5]['pv.input_power_w'] = [PowerInterval(start,start+timedelta(hours=2),1000)]
    setup_daily[5]['pv.output_power_w'] = [
        PowerInterval(start+timedelta(hours=1),start+timedelta(hours=2),900)]
    result=run(setup_daily)
    assert result['pv']['energy_kwh'] == 2
    assert result['pv']['output_energy_kwh'] == .9
    assert result['pv']['mppt_efficiency'] == .9  # not .45
    assert result['power_accounting']['efficiency_coverage'] == pytest.approx(1/24)
