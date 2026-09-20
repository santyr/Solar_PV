import pytest
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
