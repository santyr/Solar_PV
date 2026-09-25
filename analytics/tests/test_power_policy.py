import json
from datetime import datetime, timezone

import pytest

from earthship_energy import cli, scheduled
from earthship_energy.inventory import SourceResolutionError
from earthship_energy.power_policy import load_power_policy


def write_policy(tmp_path, **changes):
    payload={'version':1,'policy':'qualified_power_evidence_v1',
             'item_name':'Power_Evidence_JSON','cutover':'2026-09-20T15:18:58.261099Z'}
    payload.update(changes)
    path=tmp_path/'power-policy.json';path.write_text(json.dumps(payload))
    return path


def test_policy_resolves_inventory_not_assumed_numeric_id(tmp_path):
    policy=load_power_policy(write_policy(tmp_path))
    assert policy.cutover==datetime(2026,9,20,15,18,58,261099,tzinfo=timezone.utc)
    assert policy.resolve_table([(799,'Power_Evidence_JSON')],{'item0799'})=='item0799'


@pytest.mark.parametrize('changes',[{'version':True},{'version':2},{'extra':1},
    {'policy':'legacy'},{'item_name':'BMS_SOC'}, {'cutover':'2026-09-20T15:00:00'}])
def test_malformed_policy_is_not_silently_disabled(tmp_path,changes):
    with pytest.raises(ValueError,match='valid power evidence policy'):
        load_power_policy(write_policy(tmp_path,**changes))


@pytest.mark.parametrize('items,tables', [([],set()), ([(1,'Power_Evidence_JSON')],set()),
    ([(1,'Power_Evidence_JSON'),(2,'Power_Evidence_JSON')],{'item0001','item0002'})])
def test_missing_or_ambiguous_inventory_refuses_fallback(tmp_path,items,tables):
    with pytest.raises(SourceResolutionError):
        load_power_policy(write_policy(tmp_path)).resolve_table(items,tables)


def test_cli_passes_explicit_policy_to_daily_reader(tmp_path,monkeypatch,capsys):
    settings=object();captured={}
    monkeypatch.setattr(cli,'parse_openhab_jdbc_config',lambda _:settings)
    monkeypatch.setattr(cli,'connect_read_only',lambda _:object())
    monkeypatch.setattr(cli,'fetch_inventory',lambda _:([(648,'Power_Evidence_JSON')],{'item0648'}))
    monkeypatch.setattr(cli,'resolve_sources',lambda *_:[])
    def daily(*args,**kwargs):
        captured.update(kwargs)
        return {'status':'ok','power_accounting':{'policy':'qualified_power_evidence_v1'}}
    monkeypatch.setattr(cli,'build_daily_snapshot',daily)
    monkeypatch.setattr(cli,'verify_reference_data',lambda *args:captured.update(reference_checked=True))
    assert cli.main(['aggregate','--date','2026-09-21','--dry-run',
                     '--power-evidence-policy',str(write_policy(tmp_path))])==0
    assert captured['power_evidence_settings'] is settings
    assert captured['power_evidence_table']=='item0648'
    assert captured['power_evidence_cutover'].tzinfo is not None
    assert captured['reference_checked'] is True


def test_bad_policy_refused_before_any_connection(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(cli,'parse_openhab_jdbc_config',lambda _:pytest.fail('unexpected credential read'))
    assert cli.main(['aggregate','--date','2026-09-21','--dry-run',
                     '--power-evidence-policy',str(write_policy(tmp_path,version=True))])==2


def test_scheduler_only_forwards_policy_when_explicitly_requested(monkeypatch):
    commands=[]
    monkeypatch.setattr(scheduled.energy_cli,'main',lambda argv:commands.append(argv) or 0)
    assert scheduled.main(['daily-aggregate','--power-evidence-policy','/reviewed/policy.json'])==0
    assert commands[0][-2:]==['--power-evidence-policy','/reviewed/policy.json']


@pytest.mark.parametrize('raw',['{"version":1,"version":1}', ' '*4097])
def test_duplicate_keys_and_oversized_policy_are_rejected(tmp_path,raw):
    path=tmp_path/'bad.json';path.write_text(raw)
    with pytest.raises(ValueError,match='valid power evidence policy'):
        load_power_policy(path)
