import pytest
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from earthship_energy.power_report import build_qualified_lifecycle_report
from earthship_energy.power_store import encode_snapshot
from test_power_report import revision
from test_qualified_lifecycle import report


def observed(valid=3600, above90=.5, above95=.25):
    row=revision()
    row['payload']['battery'].update(hours_above_90=above90,hours_above_95=above95)
    row['payload']['source_quality']=[{'canonical_name':'battery.soc_pct',
        'coverage':valid/86400,'detail':{'policy':'atomic_bms_evidence',
        'freshness_basis':'BMS_SOC_Evidence_JSON','valid_seconds':valid,
        'window_seconds':86400,'reason':None}}]
    return row


def result(row):
    row['payload_sha256']=encode_snapshot(row['payload'])[3]
    return report([row])['high_soc_exposure']


def test_atomic_exposure_has_own_coverage_not_combined_battery():
    row=observed();row['payload']['battery']['coverage']=0
    out=result(row)
    assert out['above_90_hours']==.5 and out['above_95_hours']==.25
    assert out['daily'][0]['coverage']==pytest.approx(1/24)
    assert out['valid_seconds']==3600


def test_empty_and_zero_coverage_are_unknown_but_measured_zero_is_zero():
    assert report([])['high_soc_exposure']['above_90_hours'] is None
    assert result(observed(0,0,0))['above_90_hours'] is None
    assert result(observed(3600,0,0))['above_90_hours']==0


@pytest.mark.parametrize('change', ['legacy','wrong_source','ambiguous'])
def test_unqualified_exposure_is_not_counted(change):
    row=observed();detail=row['payload']['source_quality'][0]['detail']
    if change=='legacy':detail['policy']='timestamp_threshold'
    elif change=='wrong_source':detail['freshness_basis']='BMS_SOC'
    else:detail['reason']='ambiguous_evidence_sequence'
    out=result(row)
    assert out['above_90_hours'] is None
    assert out['unavailable_present_dates']==['2026-08-21']


@pytest.mark.parametrize('change', ['duration','coverage','excess','inverted','duplicate'])
def test_inconsistent_evidence_fails_closed(change):
    row=observed();quality=row['payload']['source_quality'][0]
    if change=='duration':quality['detail']['window_seconds']=82800
    elif change=='coverage':quality['coverage']=1
    elif change=='excess':row['payload']['battery']['hours_above_90']=2
    elif change=='inverted':row['payload']['battery']['hours_above_95']=.75
    else:row['payload']['source_quality'].append(dict(quality))
    with pytest.raises(ValueError,match='SoC exposure'):
        result(row)


@pytest.mark.parametrize('day,hours', [(date(2026,3,8),23),(date(2026,11,1),25)])
def test_denver_dst_days_use_elapsed_hours_and_reject_24_hour_denominator(day,hours):
    row=observed(valid=hours*3600,above90=hours,above95=hours/2)
    zone=ZoneInfo('America/Denver')
    start=datetime.combine(day,time.min,tzinfo=zone)
    end=datetime.combine(day+timedelta(days=1),time.min,tzinfo=zone)
    cutover=datetime(2026,1,1,tzinfo=timezone.utc)
    payload=row['payload']
    payload.update(local_date=day.isoformat(),window_start=start.isoformat(),window_end=end.isoformat())
    payload['power_accounting']['cutover']=cutover.isoformat()
    quality=payload['source_quality'][0]
    quality['coverage']=1
    quality['detail']['window_seconds']=hours*3600
    row.update(local_date=day,cutover=cutover,payload_sha256=encode_snapshot(payload)[3])
    args=dict(epoch_id='bank',cutover=cutover,start_date=day,
              end_date=day+timedelta(days=1),as_of=row['computed_at'])
    out=build_qualified_lifecycle_report([row],**args)['high_soc_exposure']
    assert out['above_90_hours']==hours
    assert out['daily'][0]['window_seconds']==hours*3600
    assert out['daily'][0]['coverage']==1
    quality['detail']['window_seconds']=86400
    row['payload_sha256']=encode_snapshot(payload)[3]
    with pytest.raises(ValueError,match='coverage'):
        build_qualified_lifecycle_report([row],**args)
