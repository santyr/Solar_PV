from datetime import date
import json
import pytest
from earthship_energy import cli
from earthship_energy.power_report import build_qualified_lifecycle_report
from earthship_energy.power_policy import PowerEvidencePolicy
from earthship_energy.power_store import encode_snapshot
from test_power_report import revision, CUTOVER, ASOF


def report(rows):
    return build_qualified_lifecycle_report(rows, epoch_id='bank', cutover=CUTOVER,
        start_date=date(2026,8,21), end_date=date(2026,8,24), as_of=ASOF)


def test_period_efc_is_not_lifetime_and_missing_days_remain():
    result = report([revision(21,.1), revision(23,.2)])
    assert result['period_efc'] == pytest.approx(.3)
    assert result['missing_dates'] == ['2026-08-22']
    assert result['lifetime_efc'] is result['ending_cumulative_efc'] is None
    assert result['legacy_included'] is False
    assert result['report'] == 'qualified_lifecycle'
    assert len(result['daily']) == 2
    assert 'temperature_exposure' in result['unavailable']


def test_empty_is_unknown_not_zero():
    result = report([])
    assert result['status'] == 'unavailable'
    assert result['period_efc'] is result['charge_kwh'] is result['discharge_kwh'] is None


def test_partial_coverage_is_not_normalized_or_filtered():
    row=revision();row['payload']['battery']['coverage']=.1
    row['payload_sha256']=encode_snapshot(row['payload'])[3]
    result=report([row])
    assert result['period_efc'] == .1
    assert result['daily'][0]['battery_daily_coverage'] == .1
    assert result['status'] == 'partial_observations'


def test_bad_revision_refused():
    row=revision();row['payload_sha256']='0'*64
    with pytest.raises(ValueError,match='identity'):
        report([row])


def test_cli_routes_lifecycle_to_qualified_reader(monkeypatch,capsys):
    monkeypatch.setattr(cli,'load_power_policy',lambda _:PowerEvidencePolicy(CUTOVER))
    monkeypatch.setattr(cli,'parse_openhab_jdbc_config',lambda _:'settings')
    def forbidden(*args,**kwargs):
        pytest.fail('legacy database reader must not run')
    monkeypatch.setattr(cli,'connect_read_only',forbidden)
    def read(settings,**kwargs):
        assert settings=='settings' and kwargs['cutover']==CUTOVER
        return report([])
    monkeypatch.setattr(cli,'read_qualified_lifecycle_report',read)
    assert cli.main(['report','lifecycle','--start','2026-08-21','--end','2026-08-24',
                     '--power-evidence-policy','policy.json'])==0
    assert json.loads(capsys.readouterr().out)['report']=='qualified_lifecycle'
