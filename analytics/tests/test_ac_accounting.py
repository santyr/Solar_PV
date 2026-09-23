from datetime import date, datetime, timedelta, timezone

import pytest

from earthship_energy import ac_accounting
from earthship_energy.ac_policy import AcEvidencePolicy
from earthship_energy.power_policy import PowerEvidencePolicy
from earthship_energy.inventory import SourceResolutionError
from earthship_energy.power_intervals import PowerInterval

BASE = datetime(2026, 9, 24, 6, tzinfo=timezone.utc)


def at(seconds):
    return BASE + timedelta(seconds=seconds)


def interval(left, right, watts):
    return PowerInterval(at(left), at(right), watts)


def test_observed_ac_energy_and_simultaneous_dc_pv_remain_separate():
    result = ac_accounting.summarize_ac_day(
        [interval(0, 3600, 1000)], [interval(1800, 3600, 2000)],
        window_start=at(0), window_end=at(3600))
    assert result.observed_ac_load_kwh == 1
    assert result.ac_coverage == 1
    assert result.common_ac_load_kwh == .5
    assert result.common_pv_dc_kwh == 1
    assert result.common_coverage == .5
    assert result.balance_kwh is None
    assert result.balance_reason == 'dc_pv_and_ac_load_cross_domain'


def test_missing_time_never_becomes_zero_load_or_balance():
    result = ac_accounting.summarize_ac_day([], [interval(0, 3600, 2000)],
        window_start=at(0), window_end=at(3600))
    assert result.observed_ac_load_kwh is None
    assert result.common_ac_load_kwh is None
    assert result.balance_reason == 'no_common_qualified_intervals'
    zero = ac_accounting.summarize_ac_day([interval(0, 3600, 0)], [],
        window_start=at(0), window_end=at(3600))
    assert zero.observed_ac_load_kwh == 0
    assert zero.common_ac_load_kwh is None


@pytest.mark.parametrize('ac,pv', [
    ([interval(0, 3600, -1)], []),
    ([interval(0, 3600, 1000)], [interval(3600, 7200, -1)]),
    ([interval(0, 3600, 1000), interval(1800, 3600, 1000)], []),
])
def test_bad_intervals_fail_instead_of_being_ignored(ac, pv):
    with pytest.raises(ValueError):
        ac_accounting.summarize_ac_day(ac, pv, window_start=at(0), window_end=at(7200))


def test_reader_integrates_only_two_strict_streams_after_policy_gate(monkeypatch):
    calls = []
    policy = AcEvidencePolicy(cutover=at(-3600), topology_from=at(-3600),
                              topology_until=at(86400))
    def ac_read(*args, **kwargs):
        calls.append(('ac', args, kwargs))
        return [interval(0, 3600, 1000)]
    def pv_read(*args, **kwargs):
        calls.append(('pv', args, kwargs))
        return {'pv.output_power_w': [interval(0, 3600, 2000)]}
    monkeypatch.setattr(ac_accounting, 'read_ac_history', ac_read)
    monkeypatch.setattr(ac_accounting, 'read_power_history', pv_read)
    result = ac_accounting.read_ac_day_accounting(object(), ac_policy=policy,
        power_policy=PowerEvidencePolicy(at(-7200)),
        items=[(653,'Inverter_AC_Evidence_JSON'),(648,'Power_Evidence_JSON')],
        tables={'item0653','item0648'},
        local_date=date(2026, 9, 24), as_of=at(90000))
    assert [call[0] for call in calls] == ['ac', 'pv']
    assert calls[0][1][1] == 'item0653'
    assert calls[1][1][1] == 'item0648'
    assert calls[0][2]['topology_end'] == at(86400)
    assert calls[1][2]['cutover'] == at(-7200)
    assert result['observed_ac_load_kwh'] == 1
    assert result['balance_kwh'] is None
    assert result['topology_from'] == at(-3600).isoformat()


def test_partial_first_day_and_late_pv_cutover_refuse_before_read(monkeypatch):
    monkeypatch.setattr(ac_accounting, 'read_ac_history',
                        lambda *a, **k: pytest.fail('reader called before policy gate'))
    policy = AcEvidencePolicy(cutover=at(1), topology_from=at(1),
                              topology_until=None)
    with pytest.raises(ValueError):
        ac_accounting.read_ac_day_accounting(object(), ac_policy=policy,
            power_policy=PowerEvidencePolicy(at(-1)),items=[],tables=set(),
            local_date=date(2026, 9, 24), as_of=at(90000))
    policy = AcEvidencePolicy(cutover=at(-1), topology_from=at(-1),
                              topology_until=None)
    with pytest.raises(ValueError):
        ac_accounting.read_ac_day_accounting(object(), ac_policy=policy,
            power_policy=PowerEvidencePolicy(at(1)),items=[],tables=set(),
            local_date=date(2026, 9, 24), as_of=at(90000))


def test_missing_or_ambiguous_item_identity_refuses_before_db_read(monkeypatch):
    monkeypatch.setattr(ac_accounting, 'read_ac_history',
                        lambda *a, **k: pytest.fail('reader called with unresolved identity'))
    policy = AcEvidencePolicy(cutover=at(-1), topology_from=at(-1),
                              topology_until=None)
    for items, tables in (([(648,'Power_Evidence_JSON')], {'item0648'}),
                          ([(653,'Inverter_AC_Evidence_JSON'),
                            (654,'Inverter_AC_Evidence_JSON'),
                            (648,'Power_Evidence_JSON')],
                           {'item0653','item0654','item0648'})):
        with pytest.raises(SourceResolutionError):
            ac_accounting.read_ac_day_accounting(object(), ac_policy=policy,
                power_policy=PowerEvidencePolicy(at(-7200)), items=items,
                tables=tables, local_date=date(2026, 9, 24), as_of=at(90000))
