from dataclasses import asdict
from datetime import date, datetime, timezone
import json
from types import SimpleNamespace

import pytest

from earthship_energy import cli, scheduled
from earthship_energy.config import load_source_config
from earthship_energy.materialize import load_epoch_config, verify_reference_data
from test_power_policy import write_policy

NOW=datetime(2026,9,24,18,tzinfo=timezone.utc)


def test_reference_verifier_selects_only_and_refuses_drift():
    config=load_source_config();epochs=load_epoch_config()
    sources={s.canonical_name:(s.item_name,json.loads(json.dumps(asdict(s))),True) for s in config.sources}
    banks={e.epoch_id:(e.start_local_date,e.end_local_date_exclusive,e.current_analytics,
        e.nominal_capacity_ah,e.nominal_usable_kwh,e.metadata) for e in epochs}
    class Connection:
        drift=False
        def cursor(self):return self
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,sql,params):
            assert sql.strip().startswith('SELECT')
            self.row=(sources if 'metric_sources' in sql else banks)[params[0]]
        def fetchone(self):return None if self.drift else self.row
    c=Connection()
    assert verify_reference_data(c,config,epochs)=={'metric_sources':21,'system_epochs':3}
    c.drift=True
    with pytest.raises(ValueError,match='reference drift'):verify_reference_data(c,config,epochs)


@pytest.mark.parametrize('first,latest,complete,severity,reason',[
    (date(2026,9,24),None,False,'Routine','awaiting_first_completed_day'),
    (date(2026,9,20),date(2026,9,23),False,'Interesting',None),
    (date(2026,9,20),date(2026,9,23),True,'Routine',None),
    (date(2026,9,20),None,False,'Actionable',None),
])
def test_monitor_distinguishes_not_due_missing_and_partial(first,latest,complete,severity,reason):
    result=scheduled.build_quality_report(now=NOW,timezone_name='America/Denver',
        sources_ok=True,live_sources_ok=True,latest_aggregate=latest,latest_forecast_issued=NOW,
        qualified_daily={'first_date':first,'coverage_ok':complete})
    assert result['severity']==severity
    daily=next(c for c in result['checks'] if c['name']=='daily_aggregate')
    assert daily['basis']=='qualified_power_evidence_v1'
    assert daily['reason']==reason
    assert daily['latest']==(latest.isoformat() if latest else None)


def test_qualified_monitor_never_queries_legacy_tables(monkeypatch):
    class Connection:
        closed=False
        def cursor(self):return self
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,sql,params):
            assert 'daily_battery' not in sql
            assert 'forecast_snapshots' in sql and params==(NOW,)
        def fetchone(self):return (NOW,)
        def close(self):self.closed=True
    c=Connection();calls=[]
    monkeypatch.setattr(scheduled,'parse_openhab_jdbc_config',lambda _:object())
    monkeypatch.setattr(scheduled,'connect_read_only',lambda _:c)
    monkeypatch.setattr(scheduled,'fetch_inventory',lambda _: ([],set()))
    monkeypatch.setattr(scheduled,'resolve_sources',lambda *a:[])
    monkeypatch.setattr(scheduled,'_live_sources_ok',lambda *a:True)
    def read(*a,**k):calls.append(k);return []
    monkeypatch.setattr('earthship_energy.power_snapshot_reader.read_power_snapshots',read)
    values,quality=scheduled.read_qualified_quality_state('unused',NOW,
        SimpleNamespace(cutover=datetime(2026,9,20,tzinfo=timezone.utc)),'America/Denver')
    assert values==(True,True,None,NOW)
    assert quality['coverage_ok'] is False and c.closed
    assert (calls[0]['end_date']-calls[0]['start_date']).days==7


def test_qualified_apply_verifies_references_without_seed_writes(tmp_path,monkeypatch,capsys):
    calls=[]
    monkeypatch.setattr(cli,'parse_openhab_jdbc_config',lambda _:object())
    monkeypatch.setattr(cli,'connect_write',lambda _:object())
    monkeypatch.setattr(cli,'get_applied_migrations',lambda _:[])
    monkeypatch.setattr(cli,'plan_migrations',lambda *a:[])
    monkeypatch.setattr(cli,'fetch_inventory',lambda _:([(648,'Power_Evidence_JSON')],{'item0648'}))
    monkeypatch.setattr(cli,'resolve_sources',lambda *a:[])
    monkeypatch.setattr(cli,'build_daily_snapshot',lambda *a,**k:{'power_accounting':{'policy':'qualified_power_evidence_v1'}})
    monkeypatch.setattr(cli,'seed_reference_data',lambda *a:pytest.fail('seed write'))
    monkeypatch.setattr(cli,'verify_reference_data',lambda *a:calls.append('verify'))
    monkeypatch.setattr(cli,'materialize_daily_snapshot',lambda *a:calls.append('store') or {})
    assert cli.main(['aggregate','--date','2026-09-21','--apply',
        '--power-evidence-policy',str(write_policy(tmp_path))])==0
    assert calls==['verify','store']


@pytest.mark.parametrize('minute,severity,expected',[(20,'Routine','2026-09-19'),(30,'Actionable','2026-09-20')])
def test_monitor_deadline_follows_existing_0021_writer(minute,severity,expected):
    now=datetime(2026,9,21,6,minute,tzinfo=timezone.utc)
    report=scheduled.build_quality_report(now=now,timezone_name='America/Denver',
        sources_ok=True,live_sources_ok=True,latest_aggregate=None,latest_forecast_issued=now,
        qualified_daily={'first_date':date(2026,9,20),'coverage_ok':False})
    assert report['severity']==severity
    daily=next(c for c in report['checks'] if c['name']=='daily_aggregate')
    assert daily['expected_through']==expected
    if minute==20:assert daily['reason']=='awaiting_scheduled_daily_aggregation'
