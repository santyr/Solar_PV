from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from earthship_energy.qualified_ui import build_qualified_ui_payload, qualified_full_streak
from earthship_energy.ui_payload import encode_energy_ui_payload, validate_energy_ui_payload
from earthship_energy.ui_reader import build_energy_ui_snapshot, fetch_ui_health_and_forecast
from earthship_energy.power_store import encode_snapshot
from test_power_report import revision, CUTOVER
from test_ui_reader import LIVE_OK

NOW=datetime(2026,8,24,18,tzinfo=timezone.utc)


def rows():
    result=[revision(day=21,efc=.1),revision(day=23,efc=.02)]
    for row in result:
        row['computed_at']=NOW
        row['payload']['battery'].update(quality='partial',coverage=.1,min_soc_pct=60,
            depth_of_discharge_pct=20,reached_99=False)
        row['payload']['source_quality']=[{'canonical_name':'battery.dc_power_w','quality':'partial'}]
        row['payload_sha256']=encode_snapshot(row['payload'])[3]
    return result


def build(records=None):
    return build_qualified_ui_payload(rows() if records is None else records,
        epoch_id='bank',cutover=CUTOVER,start_date=date(2026,8,21),end_date=date(2026,8,24),
        generated_at=NOW,timezone_name='America/Denver',forecast=None,health=None,module_health=None)


def test_projection_retains_latest_partial_day_and_never_lifetime_or_load():
    result=build()
    assert result['schema']=='earthship-energy-ui/v3'
    assert result['throughDate']=='2026-08-23'
    assert result['battery']['latestEfc']==.02
    assert result['battery']['latestMinSocPct'] is None
    assert result['battery']['status']=='degraded'
    assert result['lifecycle']['periodEfc']==pytest.approx(.12)
    assert result['lifecycle']['endingCumulativeEfc'] is None
    assert result['energy']['latest']['loadKwh'] is None
    assert result['accounting']['missingDays']==1
    assert result['accounting']['latestBatteryCoverage']==.1
    assert len(encode_energy_ui_payload(result))<16384


def test_empty_projection_does_not_fabricate_zeros():
    result=build([])
    assert result['status']=='unavailable'
    assert result['throughDate'] is None
    assert result['lifecycle']['periodEfc'] is None
    assert result['accounting']['daysPresent']==0
    assert result['accounting']['missingDays']==3
    encode_energy_ui_payload(result)


def full_rows(days=(21,22,23), reached=(True,False,False), partial_days=()):
    result=[]
    for day, full in zip(days,reached):
        row=revision(day=day)
        row['computed_at']=NOW
        row['payload']['battery'].update(quality='partial' if day in partial_days else 'ok',
            coverage=.8 if day in partial_days else .99,min_soc_pct=60,
            depth_of_discharge_pct=20,reached_99=full)
        row['payload_sha256']=encode_snapshot(row['payload'])[3]
        result.append(row)
    return result


def test_qualified_full_streak_counts_only_contiguous_healthy_days():
    result=build(full_rows())
    assert result['battery']['daysSinceFull']==2
    assert result['battery']['currentNoFullDays']==2
    assert result['battery']['status']=='ok'
    assert build(full_rows(reached=(False,False,True)))['battery']['daysSinceFull']==0
    assert build(full_rows(reached=(False,False,True)))['battery']['currentNoFullDays']==0


@pytest.mark.parametrize('records',[
    full_rows(days=(21,23),reached=(True,False)),
    full_rows(reached=(True,False,False),partial_days=(22,)),
    full_rows(reached=(False,False,False)),
    full_rows(days=(21,22),reached=(True,False)),
])
def test_qualified_full_streak_withholds_gaps_partial_days_and_unwitnessed_full(records):
    result=build(records)
    assert result['battery']['daysSinceFull'] is None


def test_qualified_no_full_run_stops_at_evidence_gap():
    assert build(full_rows(days=(21,23),reached=(True,False)))['battery']['currentNoFullDays']==1
    assert build(full_rows(reached=(True,False,False),partial_days=(22,)))['battery']['currentNoFullDays']==1
    assert build(full_rows(reached=(False,False,False)))['battery']['currentNoFullDays']==3
    assert build(full_rows(days=(21,22),reached=(True,False)))['battery']['currentNoFullDays'] is None


def test_qualified_full_streak_rejects_partial_full_day_as_anchor():
    records=full_rows(reached=(True,False,False),partial_days=(21,))
    assert qualified_full_streak(records,date(2026,8,24)) == (2, None)


def atomic_exposure_rows(*, coverage=.99, missing_day=False, missing_source=False):
    records=full_rows(days=(21,23) if missing_day else (21,22,23),
        reached=(True,False) if missing_day else (True,False,False))
    for row in records:
        window_start=datetime.fromisoformat(row['payload']['window_start'])
        window_end=datetime.fromisoformat(row['payload']['window_end'])
        seconds=(window_end-window_start).total_seconds()
        row['payload']['battery'].update(hours_above_90=2.0,hours_above_95=1.0)
        row['payload']['source_quality']=[{'canonical_name':'battery.soc_pct',
            'coverage':coverage,'detail':{'policy':'atomic_bms_evidence',
            'freshness_basis':'BMS_SOC_Evidence_JSON',
            'valid_seconds':seconds*coverage,'window_seconds':seconds,
            'reason':'source_unavailable' if missing_source else None}}]
        row['payload_sha256']=encode_snapshot(row['payload'])[3]
    return records


def test_qualified_ui_exposes_observed_high_soc_hours_for_complete_atomic_window():
    result=build(atomic_exposure_rows())
    assert result['lifecycle']['highSocHoursAbove90']==6.0
    assert result['lifecycle']['highSocHoursAbove95']==3.0
    encode_energy_ui_payload(result)


@pytest.mark.parametrize('options',[{'coverage':.89},{'missing_day':True},
                                    {'missing_source':True}])
def test_qualified_ui_withholds_high_soc_hours_when_window_is_not_qualified(options):
    result=build(atomic_exposure_rows(**options))
    assert result['lifecycle']['highSocHoursAbove90'] is None
    assert result['lifecycle']['highSocHoursAbove95'] is None


@pytest.mark.parametrize('mutate',[
    lambda p:p['accounting'].update(policy='legacy'),
    lambda p:p['accounting'].update(latestBatteryCoverage=2),
    lambda p:p['accounting'].update(daysPresent=3),
    lambda p:p['accounting']['latestRevision'].update(id=2**54),
    lambda p:p['accounting']['latestRevision'].update(sha256='x'),
    lambda p:p['accounting']['latestRevision'].update(computedAt='2026-08-23T18:00:00Z'),
    lambda p:p['accounting']['latestRevision'].update(computedAt='2030-01-01T00:00:00Z'),
    lambda p:p['lifecycle'].update(endingCumulativeEfc=99),
    lambda p:p['energy']['latest'].update(loadKwh=9),
    lambda p:p['battery'].update(status='ok'),
    lambda p:p.update(status='ok'),
])
def test_validator_refuses_conflicting_provenance(mutate):
    payload=build();mutate(payload)
    with pytest.raises(ValueError):validate_energy_ui_payload(payload)


class ForecastOnly:
    def cursor(self):return self
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def execute(self,sql,params):
        assert 'daily_source_quality' not in sql
        assert 'forecast_snapshots' in sql
    def fetchone(self):return None


def test_qualified_health_bypasses_legacy_quality_table():
    _,health=fetch_ui_health_and_forecast(ForecastOnly(),through_date=date(2026,8,23),
        generated_at=NOW,timezone_name='America/Denver',live_health=LIVE_OK,
        qualified_source_quality=[{'canonical_name':'battery.dc_power_w','quality':'partial'}])
    assert health['analytics']=='degraded'


def test_qualified_snapshot_never_reads_legacy_daily_tables(monkeypatch):
    monkeypatch.setattr('earthship_energy.power_snapshot_reader.read_power_snapshots',lambda *a,**k:rows())
    def forbidden(*a,**k):pytest.fail('legacy daily fallback')
    monkeypatch.setattr('earthship_energy.ui_reader.fetch_daily_report_rows',forbidden)
    monkeypatch.setattr('earthship_energy.ui_reader.fetch_module_report_rows',lambda *a,**k:[])
    result=build_energy_ui_snapshot(ForecastOnly(),[
        SimpleNamespace(epoch_id='bank',current_analytics=True,start_local_date=date(2026,7,18))],
        generated_at=NOW,live_health=LIVE_OK,power_settings=object(),
        power_policy=SimpleNamespace(cutover=CUTOVER))
    assert result['schema']=='earthship-energy-ui/v3'
    assert result['health']['analytics']=='degraded'
    assert result['throughDate']=='2026-08-23'
