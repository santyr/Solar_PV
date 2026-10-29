from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import pytest
from earthship_energy import current_forecasts as current
NOW=datetime(2026,10,25,0,10,tzinfo=timezone.utc)
H='a'*64

def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()

def weather():
 s=dict(initialized_at='2026-10-24T12:00:00Z',first_seen_at='2026-10-24T20:41:00Z',ingestion_completed_at='2026-10-24T20:42:00Z',snapshot_sha256=H,run_id='ee:2026-10-24T12:00:00Z')
 return dict(version=3,provider='weathernext3',providerStatus='AVAILABLE',providerReason=None,generatedAt='2026-10-25T00:00:00Z',timezone='America/Denver',providerSnapshotSha256=H,issueSha256=H,releaseAuthorized=False,learningNamespace='weathernext3-selected-production-v1',solarSource=None,source=s,profiles={p:dict(status='AVAILABLE',reason=None,issueSha256=H,source=s,requiredHorizonSeconds=h) for p,h in [('extended',1209600),('nearTerm',86400)]},productionModel=dict(issueSha256='b'*64,status='MIXED_WITH_RAW_FALLBACK',localCoverageQualified=False,probabilityClaim=False,temperatureStatistic='model_point_with_declared_raw_fallback',windStatistic='native_instantaneous_with_separate_local_hour_mean'),days=[dict(date='2026-10-24',summary=dict(temperatureScope='remaining',temperatureStatistic='extrema_of_hourly_point_forecasts'),hours=[dict(at='2026-10-25T01:00:00Z',forecastProfile='nearTerm',tempF=53.,radiationWm2=0.)])])

def pv():
 return dict(schema='earthship-daily-pv-potential/v4',provider='weathernext3',generatedAt='2026-10-25T00:00:00Z',validUntil='2026-10-25T01:30:00Z',timezone='America/Denver',weatherSha256=H,geometrySha256=H,systemSha256=H,horizonSha256=H,confidence='experimental_native_component_model',automatic_actuation=False,physical_calibration_qualified=False,calibration=dict(modelSha256=H,calibrationSha256=H,procedureSha256=H,policySha256=H,trainedAt='2026-10-24T00:00:00Z',trainingThrough='2026-10-23T00:00:00Z',validUntil='2026-11-07T00:00:00Z',targets=48,localTargetDates=3,baselineRule='native_fdir_ssrd_isotropic_faiman_proxy_pvwatts_dc_v2',mode='experimental_production',physicalCalibrationQualified=False),days=[dict(date=d,status='available',reason=None,potentialKwh=n,uncalibratedPotentialKwh=n,fromAt=a,throughAt=b,scope=s,calibrationScope='native_components_only',sourceSupport=dict(native_hours=6 if s=='remaining' else 24,fallback_hours=0,fallback_reasons={}),projectionSha256=H) for d,n,a,b,s in [('2026-10-24',1.,'2026-10-25T00:00:00Z','2026-10-25T06:00:00Z','remaining'),('2026-10-25',12.,'2026-10-25T06:00:00Z','2026-10-26T06:00:00Z','full_day')]])

def household():
 v=dict(schema='earthship-household-energy-observation/v1',generated_at='2026-10-25T00:00:30Z',issued_at='2026-10-25T00:00:00Z',valid_until='2026-10-25T00:15:00Z',receipt_sha256=H,cohort_id=None,status='available',reason=None,storage_status='conditional',storage_reason=None,potential_pv_24h_kwh=24.,potential_pv_remaining_today_kwh=3.,captured_pv_24h_kwh=12.,household_ac_load_w_assumption=500.,initial_soc_pct=80.,nominal_bank_kwh=20.48,terrain_status='unvalidated_map_estimate',confidence='provisional_uncalibrated',pv_energy_accuracy='unavailable_unmatched_meter_scope',physical_calibration_qualified=False,automatic_actuation=False,trajectory=[dict(at=(NOW.replace(minute=0)+timedelta(hours=i+1)).isoformat(),potential_pv_kwh=1.,captured_pv_kwh=.5,nominal_soc_pct=80.) for i in range(24)])
 v['view_sha256']=current.identity(v);return v

@pytest.mark.parametrize('family,fixture',[('weather',weather),('dailyPv',pv),('householdEnergy',household)])
def test_original_identity_and_new_namespace(family,fixture):
 rows=current.decode_product(family,raw(fixture()),now=NOW)
 assert rows and rows[0].value is None
 assert all('.' in r.metric and r.source in current.SOURCES.values() for r in rows)
 assert not {'temperature_f','daily_pv_kwh'} & {r.metric for r in rows}
 assert rows[0].payload['productSha256']==current.sha256(raw(fixture())).hexdigest()
 assert rows[0].issued_at==NOW.replace(minute=0)

@pytest.mark.parametrize('family,fixture',[('weather',weather),('dailyPv',pv),('householdEnergy',household)])
def test_future_stale_unknown_duplicate_nonfinite_refused(family,fixture):
 for bad in [b'{"x":1,"x":2}',b'{"x":NaN}']:
  with pytest.raises(ValueError):current.decode_product(family,bad,now=NOW)
 for now in [NOW-timedelta(hours=1),NOW+timedelta(days=2)]:
  with pytest.raises(ValueError):current.decode_product(family,raw(fixture()),now=now)
 v=fixture();v['version' if family=='weather' else 'schema']='unknown'
 with pytest.raises(ValueError):current.decode_product(family,raw(v),now=NOW)

@pytest.mark.parametrize('mutate',[
 lambda v:v['productionModel'].__setitem__('probabilityClaim',True),lambda v:v['productionModel'].__setitem__('temperatureStatistic','raw'),lambda v:v['source'].__setitem__('initialized_at','2026-10-25T01:00:00Z'),lambda v:v['source'].__setitem__('first_seen_at','2026-10-25T01:00:00Z'),lambda v:v['days'][0]['hours'][0].__setitem__('tempF',True),lambda v:v['days'][0]['hours'][0].__setitem__('forecastProfile','unknown')])
def test_weather_bad_provenance_refused(mutate):
 v=deepcopy(weather());mutate(v)
 with pytest.raises(ValueError):current.decode_product('weather',raw(v),now=NOW)

@pytest.mark.parametrize('mutate',[lambda v:v.__setitem__('automatic_actuation',True),lambda v:v['days'][0].__setitem__('scope','full_day'),lambda v:v['days'][1].__setitem__('potentialKwh',True),lambda v:v['calibration'].__setitem__('physicalCalibrationQualified',True),lambda v:v['days'][1]['sourceSupport'].__setitem__('fallback_hours',2)])
def test_pv_bad_scope_calibration_refused(mutate):
 v=pv();mutate(v)
 with pytest.raises(ValueError):current.decode_product('dailyPv',raw(v),now=NOW)

def test_current_set_and_independent_expiry():
 rows=[current.decode_product(f,raw(fn()),now=NOW)[0] for f,fn in [('weather',weather),('dailyPv',pv),('householdEnergy',household)]]
 f=current.forecast_from_markers(rows,now=NOW)
 assert f['status']=='current' and f['dailyPv']['today']['scope']=='remaining'
 assert f['dailyPv']['tomorrow']['scope']=='full_day'
 assert f['weather']['coreIssueSha256']==H and f['weather']['productionIssueSha256']=='b'*64
 assert f['householdEnergy']['cohortId'] is None
 later=current.forecast_from_markers(rows,now=NOW+timedelta(minutes=5))
 assert later['status']!='current' and later['householdEnergy']['potentialNext24hKwh'] is None
 assert later['dailyPv']['today']['potentialKwh']==1.

def test_owned_file_refuses_symlink_oversize_and_writable_permissions(tmp_path):
 p=tmp_path/'view';p.write_bytes(b'{}');p.chmod(0o600)
 assert current.read_owned(p,32)==b'{}'
 link=tmp_path/'link';link.symlink_to(p)
 with pytest.raises(ValueError):current.read_owned(link,32)
 p.write_bytes(b'x'*33)
 with pytest.raises(ValueError):current.read_owned(p,32)
 p.write_bytes(b'{}');p.chmod(0o666)
 with pytest.raises(ValueError):current.read_owned(p,32)

def test_dry_run_never_connects_or_publishes(monkeypatch,capsys):
 from earthship_energy import scheduled
 monkeypatch.setattr(current,'acquire_current',lambda **k:([current.decode_product('dailyPv',raw(pv()),now=NOW)[0]],{'status':'ok'}))
 monkeypatch.setattr(scheduled,'connect_write',lambda *a:pytest.fail('write connection'))
 monkeypatch.setattr(scheduled,'publish_energy_ui_state',lambda *a,**k:pytest.fail('publication'))
 assert scheduled.main(['current-forecast-snapshot','--dry-run'])==0

def test_quality_uses_whole_current_set_and_negative_age_is_not_routine():
 from earthship_energy.scheduled import build_quality_report
 f=current.forecast_from_markers([],now=NOW)
 report=build_quality_report(now=NOW,timezone_name='America/Denver',sources_ok=True,latest_aggregate=NOW.date(),latest_forecast_issued=f)
 assert next(c for c in report['checks'] if c['name']=='forecast_snapshot')['severity']=='Actionable'
 report=build_quality_report(now=NOW,timezone_name='America/Denver',sources_ok=True,latest_aggregate=NOW.date(),latest_forecast_issued=NOW+timedelta(minutes=1))
 assert next(c for c in report['checks'] if c['name']=='forecast_snapshot')['severity']=='Actionable'

def test_marker_reader_queries_only_exact_sources_with_both_asof_clocks():
 statements=[]
 class Cursor:
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def execute(self,sql,params):statements.append((sql,params))
  def fetchone(self):return None
 class Connection:
  def cursor(self):return Cursor()
 assert current.read_current_forecast(Connection(),now=NOW)['status']=='unavailable'
 assert len(statements)==3
 for sql,params in statements:
  assert 'source = %s AND metric = %s' in sql
  assert 'issued_at <= %s AND captured_at <= %s' in sql
  assert 'snapshot_id DESC LIMIT 1' in sql
  assert params[0] in current.SOURCES.values()

def test_latest_unavailable_preserves_issue_without_old_available_fallback():
 old=current.decode_product('householdEnergy',raw(household()),now=NOW)[0]
 v=household();v.update(status='unavailable',reason='weather_unavailable',storage_status='unavailable',storage_reason='weather_unavailable',trajectory=[],issued_at='2026-10-25T00:01:00Z',generated_at='2026-10-25T00:01:30Z',valid_until='2026-10-25T00:16:00Z')
 for k in ['potential_pv_24h_kwh','potential_pv_remaining_today_kwh','captured_pv_24h_kwh','household_ac_load_w_assumption','initial_soc_pct','nominal_bank_kwh']:v[k]=None
 v['view_sha256']=current.identity({k:x for k,x in v.items() if k!='view_sha256'})
 new=current.decode_product('householdEnergy',raw(v),now=NOW)[0]
 f=current.forecast_from_markers([old,new],now=NOW)
 assert f['householdEnergy']['issuedAt']==v['issued_at'] and f['householdEnergy']['status']=='unavailable'


def test_weather_omitted_hour_profile_means_original_extended_profile():
 v=weather();del v['days'][0]['hours'][0]['forecastProfile']
 rows=current.decode_product('weather',raw(v),now=NOW)
 assert rows[1].payload['forecastProfile']=='extended'

def test_owned_cache_ancestors_may_have_owner_group_modes(tmp_path):
 parent=tmp_path/'group';parent.mkdir(mode=0o775);parent.chmod(0o775)
 private=parent/'private';private.mkdir(mode=0o700)
 p=private/'view';p.write_bytes(b'{}');p.chmod(0o600)
 assert current.read_owned(p,32)==b'{}'

def original_confirmation():
 view=pv();r=dict(schema='earthship-daily-pv-potential-receipt/v2',issued=False,automatic_actuation=False,view=view,native_forecast=dict(origin=view['generatedAt'],issued_at='2026-10-24T12:00:00Z',forecast_sha256=H))
 r['receipt_sha256']=current.identity(r)
 e=dict(schema='earthship-confirmed-component-daily-emission/v1',receipt_sha256=r['receipt_sha256'],view_bytes_sha256=current.sha256(raw(view)).hexdigest(),published_at='2026-10-25T00:00:10Z',calibration_sha256=H,issued=True,score_days=['2026-10-25'],source_population='actual_published_daily_totals_and_original_constituent_power',score_basis='constituent_five_minute_power_of_published_daily_totals',score_from_at='2026-10-25T00:00:10Z',automatic_actuation=False)
 e['emission_sha256']=current.identity(e);return r,e

def test_genuine_emission_binds_exact_view_original_receipt_and_native_issue():
 r,e=original_confirmation();original=raw(r)
 p=current.decode_product('dailyPv',raw(pv()),now=NOW,confirmation=(raw(r),raw(e)))[0].payload['provenance']
 assert p['publicationConfirmation']=='confirmed_original_emission' and p['upstreamIssuedAt']=='2026-10-24T12:00:00Z'
 assert raw(r)==original and r['issued'] is False
 for key in ('receipt_sha256','view_bytes_sha256'):
  bad=deepcopy(e);bad[key]='b'*64;bad['emission_sha256']=current.identity({k:v for k,v in bad.items() if k!='emission_sha256'})
  with pytest.raises(ValueError):current.confirm_pv(raw(pv()),raw(r),raw(bad),now=NOW)

@pytest.mark.parametrize('family,fixture,minutes',[('weather',weather,240),('dailyPv',pv,90),('householdEnergy',household,15)])
def test_exact_expiration_boundary(family,fixture,minutes):
 now=NOW.replace(minute=0)+timedelta(minutes=minutes)
 with pytest.raises(ValueError):current.decode_product(family,raw(fixture()),now=now)

@pytest.mark.parametrize('day,start,end,hours',[('2026-11-01','2026-11-01T06:00:00Z','2026-11-02T07:00:00Z',25),('2026-03-08','2026-03-08T07:00:00Z','2026-03-09T06:00:00Z',23)])
def test_denver_dst_exact_day_is_not_24_hour_assumption(day,start,end,hours):
 v=pv();v['generatedAt']=(current.stamp(start)-timedelta(hours=1)).isoformat();v['validUntil']=(current.stamp(v['generatedAt'])+timedelta(minutes=90)).isoformat()
 trained=current.stamp(v['generatedAt'])-timedelta(days=1);v['calibration'].update(trainedAt=trained.isoformat(),trainingThrough=(trained-timedelta(days=1)).isoformat(),validUntil=(trained+timedelta(days=14)).isoformat())
 d=v['days'][1];d.update(date=day,fromAt=start,throughAt=end);d['sourceSupport']['native_hours']=hours;v['days']=[d]
 rows=current.decode_product('dailyPv',raw(v),now=current.stamp(v['generatedAt']))
 assert (rows[1].valid_for-current.stamp(start)).total_seconds()==hours*3600

def test_http_no_redirect_oversize_and_sanitized_failures():
 class Response:
  status=200
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def read(self,n):assert n==262145;return b'x'*262145
 def opener(request,timeout):
  assert request.full_url==current.WEATHER_URL and request.method=='GET' and timeout==15
  return Response()
 with pytest.raises(ValueError,match='weather acquisition failed'):current.fetch_weather('secret',opener=opener)
 def failure(*a,**k):raise OSError('do not print secret')
 with pytest.raises(ValueError,match='^weather acquisition failed$'):current.fetch_weather('secret',opener=failure)
 assert current.NoRedirect().redirect_request(None,None,None,None,None,None) is None

def test_v5_python_encoder_retains_v4_safety_validation():
 from test_ac_ui import v4
 from earthship_energy.ui_payload import validate_energy_ui_payload,encode_energy_ui_payload
 base=v4();f=current.forecast_from_markers([],now=current.stamp(base['generatedAt']))
 v=current.build_current_ui_payload(base,f)
 assert v['schema']=='earthship-energy-ui/v5' and len(encode_energy_ui_payload(v))<16384
 for path,field,value in [('accounting','policy','legacy'),('acLoad','policy','legacy')]:
  bad=deepcopy(v);bad[path][field]=value
  with pytest.raises(ValueError):validate_energy_ui_payload(bad)
 assert v['energy']==base['energy'] and v['battery']==base['battery'] and v['acLoad']==base['acLoad']

def test_capture_detects_conflicting_same_issue_and_rolls_back():
 rows=current.decode_product('dailyPv',raw(pv()),now=NOW)
 class DB:
  def __init__(self):self.rollbacks=0;self.commits=0;self.row=None
  def cursor(self):return self
  def __enter__(self):return self
  def __exit__(self,*a):pass
  rowcount=0
  def execute(self,sql,params):
   if sql.startswith('SELECT value'):self.row=(999.,None,{})
  def fetchone(self):return self.row
  def commit(self):self.commits+=1
  def rollback(self):self.rollbacks+=1
 db=DB()
 with pytest.raises(ValueError):current.persist_current_forecasts(db,rows,now=NOW)
 assert db.rollbacks==1 and db.commits==0

@pytest.mark.parametrize('grants,accepted',[(tuple([True,True,False,True,False,False,True,False]),True),(tuple([True,True,True,True,False,False,True,False]),False),(tuple([True,False,False,True,False,False,True,False]),False),(tuple([True,True,False,True,True,False,True,False]),False)])
def test_writer_role_requires_narrow_forecast_grants(grants,accepted):
 class DB:
  def cursor(self):return self
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def execute(self,sql):assert 'has_table_privilege' in sql and 'pg_get_serial_sequence' in sql
  def fetchone(self):return grants
 if accepted:current.verify_current_writer(DB())
 else:
  with pytest.raises(ValueError):current.verify_current_writer(DB())

def test_idempotent_current_capture_and_legacy_rows_remain_untouched():
 rows=current.decode_product('householdEnergy',raw(household()),now=NOW)
 class DB:
  def __init__(self):self.store={('legacy',):('preserved',)};self.commits=0;self.result=None
  def cursor(self):return self
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def execute(self,sql,params):
   if sql.lstrip().startswith('INSERT'):
    key=params[:4];self.rowcount=0 if key in self.store else 1
    self.store.setdefault(key,(params[4],params[5],params[6].adapted))
   else:self.result=self.store.get(params)
  def fetchone(self):return self.result
  def commit(self):self.commits+=1
  def rollback(self):pytest.fail('unexpected rollback')
 db=DB();assert current.persist_current_forecasts(db,rows,now=NOW)==len(rows)
 assert current.persist_current_forecasts(db,rows,now=NOW)==0
 assert db.store[('legacy',)]==('preserved',) and db.commits==2


def test_service_is_bounded_and_does_not_restore_retired_provider():
 from pathlib import Path
 root=Path(__file__).resolve().parents[2]
 unit=(root/'deploy/systemd/user/energy-current-forecast-snapshot.service').read_text()
 timer=(root/'deploy/systemd/user/energy-current-forecast-snapshot.timer').read_text()
 for required in ['PYTHONDONTWRITEBYTECODE=1','/usr/bin/python3 -B','--tasks 64','/usr/bin/taskset -c 4,5','python3.12 -B','UMask=0077','TasksMax=128','energy-current-forecast-writer.jdbc']:
  assert required in unit
 assert 'forecast-json' not in unit and 'OnCalendar=*-*-* *:02/5:00' in timer

def test_stored_marker_schema_and_unknown_fields_fail_closed():
 row=current.decode_product('weather',raw(weather()),now=NOW)[0]
 payload=deepcopy(row.payload);payload['schema']='unknown'
 bad=current.ForecastSnapshot(row.source,row.issued_at,row.valid_for,row.metric,row.value,row.unit,payload)
 assert current.forecast_from_markers([bad],now=NOW)['weather']['status']=='unavailable'

def test_reader_does_not_fallback_from_invalid_newer_marker():
 old=current.decode_product('weather',raw(weather()),now=NOW)[0]
 p=deepcopy(old.payload);p['section']['issuedAt']='2026-10-25T00:01:00Z';p['section']['productSha256']='invalid'
 new=current.ForecastSnapshot(old.source,old.issued_at+timedelta(minutes=1),old.valid_for,old.metric,None,None,p)
 assert current.forecast_from_markers([old,new],now=NOW)['weather']['status']=='unavailable'

def test_overflow_json_number_is_rejected_even_in_unprojected_field():
 with pytest.raises(ValueError):current.loads(b'{"ignored":1e9999}',32768)

@pytest.mark.parametrize('local_day',['2026-10-24','2026-03-07','2026-10-31'])
def test_capture_retains_prior_day_issue_across_denver_midnight_for_all_families(local_day):
 from datetime import date,time
 day=date.fromisoformat(local_day)
 issue=datetime.combine(day,time(23,46),current.ZONE).astimezone(timezone.utc)
 before=issue+timedelta(minutes=9)
 after=issue+timedelta(minutes=16)
 value=pv();value['generatedAt']=issue.isoformat();value['validUntil']=(issue+timedelta(minutes=90)).isoformat()
 trained=issue-timedelta(days=1)
 value['calibration'].update(trainedAt=trained.isoformat(),trainingThrough=(trained-timedelta(days=1)).isoformat(),validUntil=(trained+timedelta(days=14)).isoformat())
 for i,d in enumerate(value['days']):
  target_day=day+timedelta(days=i)
  start=issue if i==0 else datetime.combine(target_day,time.min,current.ZONE).astimezone(timezone.utc)
  end=datetime.combine(target_day+timedelta(days=1),time.min,current.ZONE).astimezone(timezone.utc)
  d.update(date=target_day.isoformat(),fromAt=start.isoformat(),throughAt=end.isoformat())
  d['sourceSupport']['native_hours']=1 if i==0 else int((end-start).total_seconds()/3600)
 weather_value=weather();delta=before-current.stamp(weather_value['generatedAt'])
 weather_value['generatedAt']=before.isoformat()
 for source in [weather_value['source']]:
  for k in ['initialized_at','first_seen_at','ingestion_completed_at']:source[k]=(current.stamp(source[k])+delta).isoformat()
 target=before+timedelta(hours=1);weather_value['days'][0]['date']=target.astimezone(current.ZONE).date().isoformat();weather_value['days'][0]['hours'][0]['at']=target.isoformat()
 energy=household();delta=(before-timedelta(minutes=1))-current.stamp(energy['issued_at'])
 for k in ['issued_at','generated_at','valid_until']:energy[k]=(current.stamp(energy[k])+delta).isoformat()
 for target in energy['trajectory']:target['at']=(current.stamp(target['at'])+delta).isoformat()
 energy['view_sha256']=current.identity({k:v for k,v in energy.items() if k!='view_sha256'})
 rows=[r for family,v in [('weather',weather_value),('dailyPv',value),('householdEnergy',energy)] for r in current.decode_product(family,raw(v),now=after)]
 original=deepcopy(rows)
 class DB:
  def __init__(self):self.store={};self.commits=0;self.rollbacks=0;self.result=None
  def cursor(self):return self
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def execute(self,sql,params):
   if sql.lstrip().startswith('INSERT'):
    key=params[:4];self.rowcount=0 if key in self.store else 1
    self.store.setdefault(key,(params[4],params[5],deepcopy(params[6].adapted)))
   else:self.result=self.store.get(params)
  def fetchone(self):return self.result
  def commit(self):self.commits+=1
  def rollback(self):self.rollbacks+=1
 db=DB()
 assert current.persist_current_forecasts(db,rows,now=before)==len(rows)
 assert current.persist_current_forecasts(db,rows,now=after)==0
 assert db.commits==2 and db.rollbacks==0
 assert {k[0] for k in db.store}==set(current.SOURCES.values()) and rows==original
 marker=next(r for r in rows if r.metric==current.MARKERS['dailyPv'])
 assert marker.issued_at==issue and marker.payload['section']['today']['date']==local_day
 projected=current.forecast_from_markers([r for r in rows if r.metric in current.MARKERS.values()],now=after)
 assert projected['status']=='current' and projected['dailyPv']['today'] is None and projected['dailyPv']['tomorrow'] is None
 with pytest.raises(ValueError):current.persist_current_forecasts(db,rows,now=issue+timedelta(minutes=90))
 assert db.commits==2 and db.rollbacks==1


@pytest.mark.parametrize('component', [None, 'analytics', 'bms', 'schneider', 'weather', 'collector', 'publisher'])
def test_current_forecast_recomputes_health_without_erasing_independent_failure(component):
 from test_ac_ui import v4
 base=v4();base['generatedAt']=NOW.isoformat()
 base['health']={name:'ok' for name in ('analytics','forecast','bms','schneider','weather','collector','publisher')}
 base['health'].update(status='degraded',forecast='unavailable',reasons=['no_forecast_snapshot','forecast_issue_older_than_6h'])
 if component:
  base['health'][component]='degraded'
  base['health']['reasons'].append('daily_source_quality_not_ok' if component=='analytics' else component+'_observational_failure')
 original=deepcopy(base)
 rows=[current.decode_product(f,raw(fn()),now=NOW)[0] for f,fn in [('weather',weather),('dailyPv',pv),('householdEnergy',household)]]
 result=current.build_current_ui_payload(base,current.forecast_from_markers(rows,now=NOW))
 assert result['health']['forecast']=='ok'
 assert result['health']['status']==('degraded' if component else 'ok')
 assert result['health']['reasons']==([] if component is None else ['daily_source_quality_not_ok' if component=='analytics' else component+'_observational_failure'])
 for independent in ('analytics','bms','schneider','weather','collector','publisher'):
  assert result['health'][independent]==original['health'][independent]
 assert result['battery']==original['battery'] and result['energy']==original['energy']
 assert result['status']=='degraded'  # independent incomplete observed accounting remains
 assert base==original
