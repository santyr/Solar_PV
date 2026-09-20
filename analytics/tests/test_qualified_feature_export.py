import csv
import io
import json
from datetime import timedelta
from types import SimpleNamespace
import pytest
from earthship_energy import cli
from earthship_energy.export import export_feature_csv, FeatureExportError
from earthship_energy.power_policy import PowerEvidencePolicy
from test_export import row, AT


def qualified_row():
    return {**row(), 'load_power_w': None, 'load_power_w_lag_1h': None}


def test_csv_explicit_provenance_and_legacy_stays_v2():
    body = export_feature_csv([qualified_row()], power_cutover=AT-timedelta(days=1))
    output = list(csv.DictReader(io.StringIO(body.decode())))[0]
    assert output['schema_version'] == '3'
    assert output['pv_basis'] == 'qualified_power_evidence_v1'
    assert output['load_basis'] == 'ac_load_evidence_unqualified'
    assert output['other_fields_basis'] == 'existing_source_policies_not_power_qualified'
    assert output['load_power_w'] == ''
    assert export_feature_csv([row()]).decode().splitlines()[1].startswith('2,')


@pytest.mark.parametrize('change', [{'load_power_w': 0}, {'pv_power_w': -1},
                                  {'pv_power_w': True}, {'pv_power_w': float('nan')}])
def test_csv_refuses_invalid_qualified_values(change):
    with pytest.raises(FeatureExportError):
        export_feature_csv([{**qualified_row(), **change}], power_cutover=AT-timedelta(days=1))


def test_pre_cutover_lag_withheld():
    with pytest.raises(FeatureExportError, match='pre-cutover'):
        export_feature_csv([qualified_row()], power_cutover=AT)
    export_feature_csv([{**qualified_row(), 'pv_power_w_lag_1h': None}], power_cutover=AT)


def test_cli_policy_routes_reader_and_csv(tmp_path, monkeypatch, capsys):
    policy = PowerEvidencePolicy(AT-timedelta(days=1))
    monkeypatch.setattr(cli, 'load_power_policy', lambda _: policy)
    monkeypatch.setattr(cli, 'parse_openhab_jdbc_config', lambda _: 'settings')
    closed = []
    monkeypatch.setattr(cli, 'connect_read_only', lambda _: SimpleNamespace(close=lambda:closed.append(True)))
    monkeypatch.setattr(cli, 'fetch_inventory', lambda _: ([(647,'Power_Evidence_JSON')], {'item0647'}))
    monkeypatch.setattr(cli, 'resolve_sources', lambda *_: [])
    def fetch(*args, **kwargs):
        assert kwargs['power_settings'] == 'settings'
        assert kwargs['power_table'] == 'item0647'
        assert kwargs['power_cutover'] == policy.cutover
        assert kwargs['atomic_soc'] is True
        return [qualified_row()]
    monkeypatch.setattr(cli, 'fetch_feature_rows', fetch)
    output = tmp_path/'features.csv'
    assert cli.main(['export-features','--start',AT.isoformat(),
        '--end',(AT+timedelta(hours=1)).isoformat(),'--output',str(output),
        '--power-evidence-policy','policy.json']) == 0
    assert json.loads(capsys.readouterr().out)['schema_version'] == 3
    assert 'qualified_power_evidence_v1' in output.read_text()
    assert closed == [True]


def test_oversized_window_refused_before_database(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, 'load_power_policy', lambda _: PowerEvidencePolicy(AT))
    def unexpected(*args):
        raise AssertionError('database must not be opened')
    monkeypatch.setattr(cli, 'connect_read_only', unexpected)
    assert cli.main(['export-features','--start',AT.isoformat(),
        '--end',(AT+timedelta(hours=25)).isoformat(),'--output',str(tmp_path/'out.csv'),
        '--power-evidence-policy','policy.json']) != 0
    assert not (tmp_path/'out.csv').exists()
