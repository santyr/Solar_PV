from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from earthship_energy import cli
from earthship_energy.power_report import build_power_report
from earthship_energy.power_store import POLICY, encode_snapshot
from test_power_store import snapshot

CUTOVER = datetime.fromisoformat('2026-09-20T15:18:58.261099+00:00')
ASOF = datetime(2030,1,1,tzinfo=timezone.utc)


def revision(day=21, efc=.1):
    payload=snapshot(day=day,efc=efc)
    day,cutover,_,digest=encode_snapshot(payload)
    return dict(local_date=day,cutover=cutover,payload=payload,payload_sha256=digest,
                epoch_id='bank',policy=POLICY,snapshot_id=1,computed_at=ASOF)


def report(rows, **kwargs):
    args=dict(epoch_id='bank',cutover=CUTOVER,start_date=date(2026,9,21),
              end_date=date(2026,9,24),as_of=ASOF)
    args.update(kwargs)
    return build_power_report(rows,**args)


def test_missing_days_and_partial_observed_throughput_are_not_filled():
    row=revision();row['payload']['battery']['coverage']=.1
    row['payload_sha256']=encode_snapshot(row['payload'])[3]
    result=report([row,revision(day=23,efc=.2)])
    assert result['missing_dates']==['2026-09-22']
    assert result['totals']['daily_efc']==pytest.approx(.3)
    assert result['daily'][0]['battery_daily_coverage']==.1
    assert result['daily'][0]['payload_sha256']==row['payload_sha256']
    assert result['legacy_included'] is False
    assert result['balance']['load_kwh'] is None
    assert 'requested_window' in result['basis']


def test_empty_history_has_unknown_totals_not_zero():
    result=report([])
    assert len(result['missing_dates'])==3
    assert all(value is None for value in result['totals'].values())


@pytest.mark.parametrize('change',[
    {'epoch_id':'other'}, {'policy':'legacy_numeric_estimate'},
    {'payload_sha256':'0'*64}, {'local_date':date(2026,9,22)},
])
def test_identity_mismatch_refused(change):
    row=revision();row.update(change)
    with pytest.raises(ValueError,match='identity'):
        report([row])


def test_duplicate_or_reverse_days_refused():
    for rows in ([revision(),revision()],[revision(day=23),revision()]):
        with pytest.raises(ValueError,match='identity'):
            report(rows)


def test_unfinished_day_refused_even_if_computed_before_asof():
    row=revision();row['computed_at']=CUTOVER
    with pytest.raises(ValueError,match='completed'):
        report([row],as_of=datetime(2026,9,21,12,tzinfo=timezone.utc))


def test_cli_power_routes_only_to_qualified_reader(monkeypatch,tmp_path,capsys):
    policy=tmp_path/'policy.json'
    import json
    policy.write_text(json.dumps(dict(version=1,policy=POLICY,
        item_name='Power_Evidence_JSON',cutover=CUTOVER.isoformat())))
    epoch=SimpleNamespace(epoch_id='bank',current_analytics=True,
                          start_local_date=date(2026,9,21))
    monkeypatch.setattr(cli,'load_epoch_config',lambda _: [epoch])
    monkeypatch.setattr(cli,'parse_openhab_jdbc_config',lambda _: 'settings')
    def forbidden(*args,**kwargs):
        pytest.fail('legacy reader must not be invoked')
    monkeypatch.setattr(cli,'connect_read_only',forbidden)
    calls=[]
    def read(settings,**kwargs):
        calls.append((settings,kwargs));return report([])
    monkeypatch.setattr(cli,'read_power_report',read)
    assert cli.main(['report','power','--start','2026-09-21','--end','2026-09-24',
                     '--power-evidence-policy',str(policy)])==0
    assert json.loads(capsys.readouterr().out)['legacy_included'] is False
    assert calls[0][1]['cutover']==CUTOVER
    assert calls[0][1]['as_of'].tzinfo is not None


def test_cli_requires_explicit_power_policy(capsys):
    assert cli.main(['report','power','--start','2026-09-21','--end','2026-09-24'])!=0
