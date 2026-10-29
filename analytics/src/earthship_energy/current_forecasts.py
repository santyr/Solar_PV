"""Read-only acquisition of issued products; append-only, isolated metric families.

This module deliberately does not import any producer, run a model, or publish.
Publication freshness is a consumer policy, never an upstream issue rewrite.
"""
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from zoneinfo import ZoneInfo

from .forecasts import ForecastSnapshot

ADAPTER = 'earthship-current-forecast-acquisition/v1'
ZONE = ZoneInfo('America/Denver')
SOURCES = dict(weather='weathernext3_selected_weather_v3', dailyPv='weathernext3_component_daily_pv_v4', householdEnergy='household_energy_potential_v1')
MARKERS = dict(weather='weathernext3.weather.publication', dailyPv='weathernext3.daily_pv.publication', householdEnergy='household.energy.publication')
PRODUCT_SCHEMAS = dict(weather='weathernext-weather/v3', dailyPv='earthship-daily-pv-potential/v4', householdEnergy='earthship-household-energy-observation/v1')
CACHE = Path('/home/sat/.local/state/household-intel')
PV_ARCHIVE = Path('/home/sat/.local/state/earthship-weather/daily-pv')
WEATHER_URL = 'http://127.0.0.1:8080/rest/items/Forecast_10Day_JSON/state'


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def identity(v):
    return sha256(canonical(v)).hexdigest()


def require(ok, message='invalid current forecast contract'):
    if not ok:
        raise ValueError(message)


def exact(v, fields):
    require(type(v) is dict and set(v) == set(fields.split() if isinstance(fields, str) else fields))
    return v


def stamp(v):
    require(type(v) is str and len(v) <= 64)
    try:
        t = datetime.fromisoformat(v.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('invalid product clock') from None
    require(t.tzinfo is not None and t.utcoffset() is not None)
    return t.astimezone(timezone.utc)


def digest(v):
    require(type(v) is str and re.fullmatch('[a-f0-9]{64}', v) is not None)
    return v


def num(v, low=0, high=100000):
    require(type(v) in (int, float) and low <= v <= high and math.isfinite(v))
    return v


def count(v, low, high):
    require(type(v) is int and low <= v <= high)


def reason(v):
    require(v is None or type(v) is str and re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,95}', v) is not None)


def loads(raw, maximum):
    require(type(raw) is bytes and len(raw) <= maximum, 'product exceeds byte limit')
    def unique(pairs):
        out = {}
        for k, v in pairs:
            require(k not in out, 'duplicate JSON key')
            out[k] = v
        return out
    def refuse(_):
        raise ValueError('nonfinite JSON')
    def finite_float(text):
        value = float(text)
        require(math.isfinite(value), 'nonfinite JSON')
        return value
    try:
        v = json.loads(raw, object_pairs_hook=unique, parse_constant=refuse, parse_float=finite_float)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError('invalid product JSON') from None
    require(type(v) is dict)
    return v


def read_owned(path, maximum):
    """Walk each directory by descriptor; reject links, races and foreign writes."""
    p = Path(path)
    require(p.is_absolute() and '..' not in p.parts and str(p) == os.path.normpath(p))
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in p.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
            s = os.fstat(parent)
            require(stat.S_ISDIR(s.st_mode))
        parent_stat = os.fstat(parent)
        require(parent_stat.st_uid == os.getuid() and not parent_stat.st_mode & 0o077)
        fd = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as f:
            before = os.fstat(f.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid() and not before.st_mode & 0o022 and before.st_size <= maximum)
            raw = f.read(maximum + 1)
            after = os.fstat(f.fileno())
            current = os.stat(p.name, dir_fd=parent, follow_symlinks=False)
            require(len(raw) <= maximum and all(getattr(before, k) == getattr(after, k) == getattr(current, k) for k in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')))
        # Re-walk verifies that a parent path wasn't replaced during the read.
        require(p.resolve() == p and os.stat(p).st_ino == before.st_ino)
        return raw
    except OSError:
        raise ValueError('owned product read refused') from None
    finally:
        os.close(parent)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch_weather(token, *, opener=None):
    require(type(token) is str and bool(token.strip()), 'weather authentication unavailable')
    send = opener or build_opener(ProxyHandler({}), NoRedirect()).open
    req = Request(WEATHER_URL, headers={'Authorization': 'Bearer ' + token.strip(), 'Accept': 'text/plain'}, method='GET')
    try:
        with send(req, timeout=15) as response:
            require(response.status == 200, 'weather GET refused')
            raw = response.read(262145)
            require(len(raw) <= 262144, 'weather response exceeds limit')
            return raw
    except Exception:
        raise ValueError('weather acquisition failed') from None


def source_profile(v, generated, now):
    exact(v, 'status reason issueSha256 source requiredHorizonSeconds')
    reason(v['reason'])
    require(v['status'] in ('AVAILABLE', 'UNAVAILABLE'))
    if v['status'] == 'UNAVAILABLE':
        require(v['source'] is None and v['issueSha256'] is None and v['reason'] is not None)
        return dict(status=v['status'], issueSha256=None, initializedAt=None, firstSeenAt=None, ingestionCompletedAt=None, snapshotSha256=None)
    digest(v['issueSha256'])
    s = exact(v['source'], 'initialized_at first_seen_at ingestion_completed_at run_id snapshot_sha256')
    digest(s['snapshot_sha256'])
    initialized, seen, ingested = (stamp(s[k]) for k in ('initialized_at', 'first_seen_at', 'ingestion_completed_at'))
    require(initialized <= seen <= ingested <= generated <= now and now - initialized <= timedelta(hours=24))
    require(type(s['run_id']) is str and len(s['run_id']) <= 128 and v['reason'] is None)
    return dict(status='AVAILABLE', issueSha256=v['issueSha256'], initializedAt=s['initialized_at'], firstSeenAt=s['first_seen_at'], ingestionCompletedAt=s['ingestion_completed_at'], snapshotSha256=s['snapshot_sha256'])


def weather_product(v, now):
    exact(v, 'version provider providerStatus providerReason generatedAt timezone providerSnapshotSha256 issueSha256 releaseAuthorized learningNamespace solarSource source profiles productionModel days')
    require(type(v['version']) is int and v['version'] == 3 and v['provider'] == 'weathernext3' and v['timezone'] == 'America/Denver')
    generated = stamp(v['generatedAt'])
    require(generated <= now < generated + timedelta(hours=4))
    require(type(v['releaseAuthorized']) is bool and v['learningNamespace'] == 'weathernext3-selected-production-v1')
    require(v['providerStatus'] in ('AVAILABLE', 'UNAVAILABLE'))
    reason(v['providerReason'])
    digest(v['providerSnapshotSha256'])
    require(type(v['days']) is list and len(v['days']) <= 10)
    profiles = {}
    exact(v['profiles'], 'extended nearTerm')
    for name, horizon in [('extended', 1209600), ('nearTerm', 86400)]:
        require(v['profiles'][name]['requiredHorizonSeconds'] == horizon)
        profiles[name] = source_profile(v['profiles'][name], generated, now)
    model = exact(v['productionModel'], 'issueSha256 status localCoverageQualified probabilityClaim temperatureStatistic windStatistic')
    require(model['localCoverageQualified'] is False and model['probabilityClaim'] is False)
    require(model['temperatureStatistic'] == 'model_point_with_declared_raw_fallback' and model['windStatistic'] == 'native_instantaneous_with_separate_local_hour_mean')
    digest(model['issueSha256'])
    require(model['status'] in ('ACTIVE', 'MIXED_WITH_RAW_FALLBACK', 'RAW_FALLBACK'))
    available = v['providerStatus'] == 'AVAILABLE'
    if available:
        digest(v['issueSha256'])
        require(v['providerReason'] is None and len(v['days']) > 0 and profiles['extended']['status'] == 'AVAILABLE')
        require(v['issueSha256'] == profiles['extended']['issueSha256'] and v['source'] == v['profiles']['extended']['source'])
    else:
        require(v['source'] is None and v['issueSha256'] is None and not v['days'] and v['providerReason'] is not None)
    deadline = generated + timedelta(hours=4)
    for profile in profiles.values():
        if profile['status'] == 'AVAILABLE':
            deadline = min(deadline, stamp(profile['initializedAt']) + timedelta(hours=24))
    require(now < deadline)
    section = dict(status='current' if available else 'unavailable', issuedAt=v['generatedAt'], validUntil=deadline.isoformat(), provider='weathernext3', productSha256=None, providerSnapshotSha256=v['providerSnapshotSha256'], coreIssueSha256=v['issueSha256'], productionIssueSha256=model['issueSha256'], productionStatus=model['status'], sourceProfiles=profiles, localCoverageQualified=False, probabilityClaim=False, reason=v['providerReason'])
    numeric = []
    previous_day = ''
    previous = None
    for day in v['days']:
        local_day = date.fromisoformat(day['date'])
        require(day['date'] > previous_day and day['date'] == local_day.isoformat())
        previous_day = day['date']
        require(day['summary']['temperatureScope'] in ('remaining', 'full_day') and day['summary']['temperatureStatistic'] == 'extrema_of_hourly_point_forecasts')
        require(type(day['hours']) is list and len(day['hours']) <= 25)
        for hour in day['hours']:
            target = stamp(hour['at'])
            require(target.astimezone(ZONE).date() == local_day and (previous is None or target > previous))
            previous = target
            profile = hour.get('forecastProfile', 'extended')
            require(profile in profiles and profiles[profile]['status'] == 'AVAILABLE')
            for field, metric, unit, low, high in [('tempF', 'temperature_f', 'degF', -150, 180), ('radiationWm2', 'radiation_wm2', 'W/m2', 0, 2000)]:
                value = hour.get(field)
                if value is not None:
                    num(value, low, high)
                    if target >= generated:
                        numeric.append((target, 'weathernext3.weather.' + metric, value, unit, {'forecastProfile': profile, 'sourceProfile': profiles[profile]}))
    return section, dict(releaseAuthorized=v['releaseAuthorized'], temperatureStatistic=model['temperatureStatistic'], windStatistic=model['windStatistic'], freshnessPolicy='consumer_publication_4h_and_source_24h_v1', timezone=v['timezone']), numeric


def pv_product(v, now):
    exact(v, 'schema provider generatedAt validUntil timezone weatherSha256 geometrySha256 systemSha256 horizonSha256 confidence automatic_actuation physical_calibration_qualified days calibration')
    require(v['schema'] == 'earthship-daily-pv-potential/v4' and v['provider'] == 'weathernext3' and v['timezone'] == 'America/Denver' and v['confidence'] == 'experimental_native_component_model')
    require(v['automatic_actuation'] is False and v['physical_calibration_qualified'] is False)
    for key in ('weatherSha256', 'geometrySha256', 'systemSha256', 'horizonSha256'):
        digest(v[key])
    generated, until = stamp(v['generatedAt']), stamp(v['validUntil'])
    require(generated <= now < until <= generated + timedelta(minutes=90))
    c = exact(v['calibration'], 'modelSha256 calibrationSha256 procedureSha256 policySha256 trainedAt trainingThrough validUntil targets localTargetDates baselineRule mode physicalCalibrationQualified')
    for key in ('modelSha256', 'calibrationSha256', 'procedureSha256', 'policySha256'):
        digest(c[key])
    require(c['physicalCalibrationQualified'] is False and c['baselineRule'] == 'native_fdir_ssrd_isotropic_faiman_proxy_pvwatts_dc_v2' and c['mode'] in ('experimental_production', 'raw_component_fallback'))
    count(c['targets'], 24, 10000)
    count(c['localTargetDates'], 3, c['targets'])
    trained, cutoff, expiry = stamp(c['trainedAt']), stamp(c['trainingThrough']), stamp(c['validUntil'])
    require(cutoff <= trained <= now and expiry == trained + timedelta(days=14))
    if c['mode'] == 'experimental_production':
        require(trained <= generated < expiry)
    require(type(v['days']) is list and 1 <= len(v['days']) <= 10)
    days, numeric, previous, active = [], [], '', False
    for d in v['days']:
        exact(d, 'date status reason potentialKwh uncalibratedPotentialKwh fromAt throughAt scope calibrationScope sourceSupport projectionSha256')
        local_day = date.fromisoformat(d['date'])
        require(local_day.isoformat() == d['date'] and d['date'] > previous and local_day >= generated.astimezone(ZONE).date())
        start, end = stamp(d['fromAt']), stamp(d['throughAt'])
        midnight = datetime.combine(local_day, time.min, ZONE).astimezone(timezone.utc)
        next_midnight = datetime.combine(local_day + timedelta(days=1), time.min, ZONE).astimezone(timezone.utc)
        require(generated <= start < end and midnight <= start < next_midnight and end == next_midnight and d['scope'] in ('remaining', 'full_day'))
        require(d['scope'] != 'full_day' or start == midnight)
        if d['status'] == 'unavailable':
            require(all(d[k] is None for k in ('potentialKwh', 'uncalibratedPotentialKwh', 'sourceSupport', 'projectionSha256')) and d['calibrationScope'] == 'none' and d['reason'] == 'incomplete_weather_or_geometry')
        else:
            require(d['status'] == 'available')
            for key in ('potentialKwh', 'uncalibratedPotentialKwh'):
                num(d[key], 0, 1000)
            digest(d['projectionSha256'])
            require(d['calibrationScope'] in ('none', 'native_components_only', 'mixed_native_and_raw_fallback', 'raw_total_only_fallback') and d['reason'] in (None, 'registered_model_expired', 'registered_model_not_yet_available', 'registered_solar_grid_unavailable'))
            s = exact(d['sourceSupport'], 'native_hours fallback_hours fallback_reasons')
            for key in ('native_hours', 'fallback_hours'):
                count(s[key], 0, 26)
            require(type(s['fallback_reasons']) is dict and len(s['fallback_reasons']) <= 26)
            for key, value in s['fallback_reasons'].items():
                require(re.fullmatch('[a-z_]{1,95}', key) is not None)
                count(value, 1, 26)
            require(sum(s['fallback_reasons'].values()) == s['fallback_hours'] and s['native_hours'] + s['fallback_hours'] <= 26)
            adjusted = d['calibrationScope'] in ('native_components_only', 'mixed_native_and_raw_fallback')
            require((c['mode'] == 'experimental_production' and d['reason'] is None) if adjusted else d['potentialKwh'] == d['uncalibratedPotentialKwh'])
            require(d['calibrationScope'] != 'native_components_only' or s['fallback_hours'] == 0)
            require(d['calibrationScope'] != 'raw_total_only_fallback' or s['native_hours'] == 0)
            active = active or adjusted
            metric = 'weathernext3.pv.remaining_today_kwh' if d['scope'] == 'remaining' else 'weathernext3.pv.full_day_kwh'
            numeric.append((end, metric, d['potentialKwh'], 'kWh', deepcopy(d)))
        days.append({k: d[k] for k in ('date', 'fromAt', 'throughAt', 'scope', 'potentialKwh', 'status', 'reason')})
        previous = d['date']
    require(active == (c['mode'] == 'experimental_production'))
    today, tomorrow = select_days(days, generated)
    section = dict(status='current' if any(d['status'] == 'available' for d in days) else 'unavailable', issuedAt=v['generatedAt'], validUntil=v['validUntil'], provider='weathernext3', productSha256=None, weatherSha256=v['weatherSha256'], today=today, tomorrow=tomorrow, confidence=v['confidence'], calibrationMode=c['mode'], physicalCalibrationQualified=False, automaticActuation=False, reason=None if any(d['status'] == 'available' for d in days) else 'incomplete_weather_or_geometry')
    provenance = {k: deepcopy(v[k]) for k in ('timezone', 'weatherSha256', 'geometrySha256', 'systemSha256', 'horizonSha256', 'calibration')}
    if section['status'] == 'current' and any(d['calibrationScope'] in ('mixed_native_and_raw_fallback', 'raw_total_only_fallback') for d in v['days']):
        section['reason'] = 'contains_declared_raw_component_fallback'
    provenance.update(days=days, daySupport=[{k: deepcopy(d[k]) for k in ('date', 'calibrationScope', 'sourceSupport', 'projectionSha256')} for d in v['days']], publicationConfirmation='unconfirmed', receiptSha256=None, emissionSha256=None, publishedAt=None)
    return section, provenance, numeric


def select_days(days, now):
    today = now.astimezone(ZONE).date()
    pick = lambda day, scope: next((deepcopy(d) for d in days if d['date'] == day.isoformat() and d['scope'] == scope), None)
    return pick(today, 'remaining'), pick(today + timedelta(days=1), 'full_day')


def household_product(v, now):
    exact(v, 'schema generated_at issued_at valid_until receipt_sha256 cohort_id status reason storage_status storage_reason potential_pv_24h_kwh potential_pv_remaining_today_kwh captured_pv_24h_kwh household_ac_load_w_assumption initial_soc_pct nominal_bank_kwh trajectory terrain_status confidence pv_energy_accuracy physical_calibration_qualified automatic_actuation view_sha256')
    require(v['schema'] == 'earthship-household-energy-observation/v1' and v['confidence'] == 'provisional_uncalibrated' and v['pv_energy_accuracy'] == 'unavailable_unmatched_meter_scope' and v['physical_calibration_qualified'] is False and v['automatic_actuation'] is False)
    require(v['terrain_status'] in ('unvalidated_map_estimate', 'unavailable'))
    digest(v['receipt_sha256']);digest(v['view_sha256'])
    require(v['view_sha256'] == identity({k: value for k, value in v.items() if k != 'view_sha256'}), 'household view digest differs')
    if v['cohort_id'] is not None:
        digest(v['cohort_id'])
    issued, generated, until = (stamp(v[k]) for k in ('issued_at', 'generated_at', 'valid_until'))
    require(issued <= generated <= now < until and until - issued == timedelta(minutes=15))
    require(v['status'] in ('available', 'unavailable') and v['storage_status'] in ('conditional', 'unavailable'))
    reason(v['reason']);reason(v['storage_reason'])
    available, conditional = v['status'] == 'available', v['storage_status'] == 'conditional'
    require(type(v['trajectory']) is list and len(v['trajectory']) == (24 if available else 0))
    if available:
        require(v['reason'] is None)
        num(v['potential_pv_24h_kwh']);num(v['potential_pv_remaining_today_kwh'], 0, v['potential_pv_24h_kwh'] + 1e-7)
    else:
        require(v['reason'] is not None and not conditional and v['potential_pv_24h_kwh'] is None and v['potential_pv_remaining_today_kwh'] is None)
    if conditional:
        require(v['storage_reason'] is None)
        num(v['captured_pv_24h_kwh'], 0, v['potential_pv_24h_kwh'] + 1e-7)
        num(v['household_ac_load_w_assumption']);num(v['initial_soc_pct'], 0, 100);num(v['nominal_bank_kwh'], .001, 10000)
    else:
        require(v['storage_reason'] is not None and all(v[k] is None for k in ('captured_pv_24h_kwh', 'household_ac_load_w_assumption', 'initial_soc_pct', 'nominal_bank_kwh')))
    potential, captured = 0, 0
    for i, row in enumerate(v['trajectory']):
        exact(row, 'at potential_pv_kwh captured_pv_kwh nominal_soc_pct')
        require(stamp(row['at']) == issued + timedelta(hours=i + 1))
        potential += num(row['potential_pv_kwh'])
        if conditional:
            captured += num(row['captured_pv_kwh'], -1e-9, row['potential_pv_kwh'] + 1e-7)
            num(row['nominal_soc_pct'], 0, 100)
        else:
            require(row['captured_pv_kwh'] is None and row['nominal_soc_pct'] is None)
    require(not available or math.isclose(potential, v['potential_pv_24h_kwh'], rel_tol=1e-7, abs_tol=1e-7))
    require(not conditional or math.isclose(captured, v['captured_pv_24h_kwh'], rel_tol=1e-7, abs_tol=1e-7))
    section = dict(status='current' if available else 'unavailable', issuedAt=v['issued_at'], generatedAt=v['generated_at'], validUntil=v['valid_until'], productSha256=None, receiptSha256=v['receipt_sha256'], cohortId=v['cohort_id'], potentialRemainingTodayKwh=v['potential_pv_remaining_today_kwh'], potentialNext24hKwh=v['potential_pv_24h_kwh'], capturedNext24hKwh=v['captured_pv_24h_kwh'], storageStatus=v['storage_status'], confidence=v['confidence'], physicalCalibrationQualified=False, automaticActuation=False, reason=v['reason'])
    numeric = []
    if available:
        numeric.extend([(issued + timedelta(hours=24), 'household.pv.potential_next_24h_kwh', v['potential_pv_24h_kwh'], 'kWh', {}), (until, 'household.pv.potential_remaining_today_kwh', v['potential_pv_remaining_today_kwh'], 'kWh', {})])
    if conditional:
        numeric.append((issued + timedelta(hours=24), 'household.pv.conditional_captured_next_24h_kwh', v['captured_pv_24h_kwh'], 'kWh', {}))
    return section, dict(viewSha256=v['view_sha256'], pvEnergyAccuracy=v['pv_energy_accuracy'], terrainStatus=v['terrain_status'], storageReason=v['storage_reason'], timezone='America/Denver'), numeric


def decode_product(family, raw, *, now, confirmation=None):
    require(family in SOURCES)
    stamp(now.isoformat())
    v = loads(raw, 262144 if family == 'weather' else 32768)
    section, provenance, numeric = {'weather': weather_product, 'dailyPv': pv_product, 'householdEnergy': household_product}[family](v, now)
    section['productSha256'] = sha256(raw).hexdigest()
    if confirmation is not None:
        require(family == 'dailyPv')
        provenance.update(confirm_pv(raw, *confirmation, now=now))
    payload = dict(adapter=ADAPTER, family=family, schema=v.get('schema', 'weathernext-weather/v3'), productSha256=section['productSha256'], section=section, provenance=provenance)
    issued, until = stamp(section['issuedAt']), stamp(section['validUntil'])
    rows = [ForecastSnapshot(SOURCES[family], issued, until, MARKERS[family], None, None, deepcopy(payload))]
    for target, metric, value, unit, extra in numeric:
        rows.append(ForecastSnapshot(SOURCES[family], issued, target, metric, value, unit, {**deepcopy(payload), **extra}))
    return rows


def confirm_pv(raw, receipt_raw, emission_raw, *, now):
    """Validate original retained preparation + genuine emission without promoting it."""
    view = loads(raw, 32768)
    r, e = loads(receipt_raw, 8 * 1024**2), loads(emission_raw, 32768)
    require(r.get('schema') == 'earthship-daily-pv-potential-receipt/v2' and r.get('issued') is False and r.get('automatic_actuation') is False)
    require(r.get('receipt_sha256') == identity({k: v for k, v in r.items() if k != 'receipt_sha256'}) and r.get('view') == view)
    exact(e, 'schema receipt_sha256 view_bytes_sha256 published_at calibration_sha256 issued score_days source_population score_basis score_from_at automatic_actuation emission_sha256')
    require(e['schema'] == 'earthship-confirmed-component-daily-emission/v1' and e['issued'] is True and e['automatic_actuation'] is False and e['emission_sha256'] == identity({k: v for k, v in e.items() if k != 'emission_sha256'}))
    require(e['receipt_sha256'] == r['receipt_sha256'] and e['view_bytes_sha256'] == sha256(raw).hexdigest() and e['calibration_sha256'] == view['calibration']['calibrationSha256'])
    origin, published = stamp(view['generatedAt']), stamp(e['published_at'])
    require(origin <= published <= min(now, origin + timedelta(seconds=85)) and e['score_from_at'] == e['published_at'])
    n = r['native_forecast']
    require(stamp(n['origin']) == origin and stamp(n['issued_at']) <= origin and n['forecast_sha256'] == view['weatherSha256'])
    require(e['source_population'] == 'actual_published_daily_totals_and_original_constituent_power' and e['score_basis'] == 'constituent_five_minute_power_of_published_daily_totals')
    require(e['score_days'] == [d['date'] for d in view['days'] if d['status'] == 'available' and stamp(d['fromAt']) >= published])
    return dict(publicationConfirmation='confirmed_original_emission', receiptSha256=r['receipt_sha256'], emissionSha256=e['emission_sha256'], publishedAt=e['published_at'], upstreamIssuedAt=n['issued_at'], projectionOrigin=n['origin'])


def discover_confirmation(raw, *, now, root=PV_ARCHIVE):
    """Bound enumeration, receipt reads and total bytes. No unbounded archive scan."""
    try:
        root_stat = os.lstat(root)
        require(stat.S_ISDIR(root_stat.st_mode) and root_stat.st_uid == os.getuid() and not root_stat.st_mode & 0o077 and root.resolve() == root)
        candidates = []
        with os.scandir(root) as entries:
            for index, entry in enumerate(entries):
                if index >= 4096:
                    return None
                if re.fullmatch('[a-f0-9]{64}\\.emission\\.json', entry.name) and not entry.is_symlink():
                    candidates.append((entry.stat(follow_symlinks=False).st_mtime_ns, entry.name))
        for _, name in sorted(candidates, reverse=True)[:32]:
            eraw = read_owned(root / name, 32768)
            e = loads(eraw, 32768)
            if e.get('view_bytes_sha256') != sha256(raw).hexdigest():
                continue
            digest(e.get('receipt_sha256'))
            rraw = read_owned(root / (e['receipt_sha256'] + '.receipt.json'), 8 * 1024**2)
            confirm_pv(raw, rraw, eraw, now=now)
            return rraw, eraw
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return None


def acquire_current(*, now, token):
    rows, products = [], {}
    for family in SOURCES:
        try:
            raw = fetch_weather(token) if family == 'weather' else read_owned(CACHE / ('daily-pv-potential.json' if family == 'dailyPv' else 'energy-observation.json'), 32768)
            confirmation = discover_confirmation(raw, now=now) if family == 'dailyPv' else None
            captured = decode_product(family, raw, now=now, confirmation=confirmation)
            rows.extend(captured)
            section = captured[0].payload['section']
            products[family] = dict(status=section['status'], issuedAt=section['issuedAt'], validUntil=section['validUntil'], productSha256=section['productSha256'], rows=len(captured), publicationConfirmation=captured[0].payload['provenance'].get('publicationConfirmation'))
        except (ValueError, KeyError, TypeError, OSError, OverflowError):
            products[family] = dict(status='acquisition_failed', reason='product_missing_invalid_or_expired')
    return rows, dict(schema=ADAPTER, acquiredAt=now.isoformat(), status='ok' if len(rows) and all(p['status'] == 'current' for p in products.values()) else 'degraded', products=products)

SECTION_FIELDS = {
    'weather': 'status issuedAt validUntil provider productSha256 providerSnapshotSha256 coreIssueSha256 productionIssueSha256 productionStatus sourceProfiles localCoverageQualified probabilityClaim reason',
    'dailyPv': 'status issuedAt validUntil provider productSha256 weatherSha256 today tomorrow confidence calibrationMode physicalCalibrationQualified automaticActuation reason',
    'householdEnergy': 'status issuedAt generatedAt validUntil productSha256 receiptSha256 cohortId potentialRemainingTodayKwh potentialNext24hKwh capturedNext24hKwh storageStatus confidence physicalCalibrationQualified automaticActuation reason',
}
PROFILE_FIELDS = 'status issueSha256 initializedAt firstSeenAt ingestionCompletedAt snapshotSha256'


def empty_section(family):
    s = dict.fromkeys(SECTION_FIELDS[family].split())
    s.update(status='unavailable', reason='no_current_product_snapshot')
    if family == 'weather':
        s.update(sourceProfiles={p: dict.fromkeys(PROFILE_FIELDS.split()) for p in ('extended', 'nearTerm')}, localCoverageQualified=False, probabilityClaim=False)
    else:
        s.update(physicalCalibrationQualified=False, automaticActuation=False)
    return s


def validate_section(family, s, *, generated):
    """Closed v5 contract, independent of upstream transport and accounting."""
    exact(s, SECTION_FIELDS[family])
    require(s['status'] in ('current', 'stale', 'degraded', 'unavailable'))
    reason(s['reason'])
    issued = stamp(s['issuedAt']) if s['issuedAt'] is not None else None
    until = stamp(s['validUntil']) if s['validUntil'] is not None else None
    require((issued is None) == (until is None))
    if issued is not None:
        require(issued <= generated and until > issued)
        digest(s['productSha256'])
    else:
        require(s == empty_section(family))
        return
    current = s['status'] == 'current'
    require(not current or issued <= generated < until)
    if family == 'weather':
        require(s['provider'] == 'weathernext3' and s['localCoverageQualified'] is False and s['probabilityClaim'] is False)
        digest(s['providerSnapshotSha256']);digest(s['productionIssueSha256'])
        if s['coreIssueSha256'] is not None:
            digest(s['coreIssueSha256'])
        require(not current or s['coreIssueSha256'] is not None)
        require(s['productionStatus'] in ('ACTIVE', 'MIXED_WITH_RAW_FALLBACK', 'RAW_FALLBACK'))
        require(not current or s['reason'] is None)
        require(until <= issued + timedelta(hours=4))
        exact(s['sourceProfiles'], 'extended nearTerm')
        require(not current or s['sourceProfiles']['extended']['status'] == 'AVAILABLE' and s['coreIssueSha256'] == s['sourceProfiles']['extended']['issueSha256'])
        for p in s['sourceProfiles'].values():
            exact(p, PROFILE_FIELDS)
            require(p['status'] in ('AVAILABLE', 'UNAVAILABLE'))
            if p['status'] == 'AVAILABLE':
                digest(p['issueSha256']);digest(p['snapshotSha256'])
                initialized, seen, ingested = (stamp(p[k]) for k in ('initializedAt', 'firstSeenAt', 'ingestionCompletedAt'))
                require(initialized <= seen <= ingested <= issued and until <= initialized + timedelta(hours=24))
            else:
                require(all(p[k] is None for k in p if k != 'status'))
    else:
        require(s['physicalCalibrationQualified'] is False and s['automaticActuation'] is False)
        if family == 'dailyPv':
            require(s['provider'] == 'weathernext3' and s['confidence'] == 'experimental_native_component_model' and s['calibrationMode'] in ('experimental_production', 'raw_component_fallback'))
            digest(s['weatherSha256'])
            require(until <= issued + timedelta(minutes=90))
            today = generated.astimezone(ZONE).date()
            for name, expected, scope in [('today', today, 'remaining'), ('tomorrow', today + timedelta(days=1), 'full_day')]:
                d = s[name]
                if d is None:
                    continue
                exact(d, 'date fromAt throughAt scope potentialKwh status reason')
                require(d['date'] == expected.isoformat() and d['scope'] == scope and d['status'] in ('available', 'unavailable'))
                start, end = stamp(d['fromAt']), stamp(d['throughAt'])
                midnight = datetime.combine(expected, time.min, ZONE).astimezone(timezone.utc)
                next_midnight = datetime.combine(expected + timedelta(days=1), time.min, ZONE).astimezone(timezone.utc)
                require(issued <= start < end == next_midnight and start >= midnight and (scope != 'full_day' or start == midnight))
                reason(d['reason'])
                if current and d['status'] == 'available':
                    num(d['potentialKwh'], 0, 1000)
                else:
                    require(d['potentialKwh'] is None)
        else:
            digest(s['receiptSha256'])
            if s['cohortId'] is not None:
                digest(s['cohortId'])
            require(issued <= stamp(s['generatedAt']) <= generated and until == issued + timedelta(minutes=15) and s['confidence'] == 'provisional_uncalibrated' and s['storageStatus'] in ('conditional', 'unavailable'))
            if current:
                require(s['reason'] is None)
                num(s['potentialNext24hKwh'])
                num(s['potentialRemainingTodayKwh'], 0, s['potentialNext24hKwh'] + 1e-7)
                if s['storageStatus'] == 'conditional':
                    num(s['capturedNext24hKwh'], 0, s['potentialNext24hKwh'] + 1e-7)
                else:
                    require(s['capturedNext24hKwh'] is None)
            else:
                require(all(s[k] is None for k in ('potentialNext24hKwh', 'potentialRemainingTodayKwh', 'capturedNext24hKwh')))


def validate_forecast(v, *, generated):
    exact(v, 'status weather dailyPv householdEnergy reason')
    require(v['status'] in ('current', 'stale', 'degraded', 'unavailable'))
    reason(v['reason'])
    for family in SOURCES:
        validate_section(family, v[family], generated=generated)
    require(v['status'] == aggregate_status(v))
    return v


def aggregate_status(v):
    statuses = [v[k]['status'] for k in SOURCES]
    return ('current' if all(s == 'current' for s in statuses) else 'unavailable' if all(s == 'unavailable' for s in statuses) else 'stale' if all(s in ('stale', 'unavailable') for s in statuses) and 'stale' in statuses else 'degraded')


def expire_section(family, s, *, now):
    s = deepcopy(s)
    if s['issuedAt'] is not None and not stamp(s['issuedAt']) <= now < stamp(s['validUntil']):
        s.update(status='stale', reason='product_validity_expired')
    if s['status'] != 'current':
        if family == 'dailyPv':
            for name in ('today', 'tomorrow'):
                if s[name] is not None:
                    s[name]['potentialKwh'] = None
        elif family == 'householdEnergy':
            for name in ('potentialRemainingTodayKwh', 'potentialNext24hKwh', 'capturedNext24hKwh'):
                s[name] = None
    return s


def forecast_from_markers(markers, *, now):
    result = {family: empty_section(family) for family in SOURCES}
    for family in SOURCES:
        candidates = [r for r in markers if r.source == SOURCES[family] and r.metric == MARKERS[family] and r.issued_at <= now]
        # Do not filter by status or expiry before selecting the latest real issue.
        row = max(candidates, key=lambda r: r.issued_at, default=None)
        if row is None:
            continue
        try:
            p = exact(row.payload, 'adapter family schema productSha256 section provenance')
            require(p['schema'] == PRODUCT_SCHEMAS[family] and p['adapter'] == ADAPTER and p['family'] == family and p['productSha256'] == p['section']['productSha256'] and row.value is None and row.unit is None)
            require(stamp(p['section']['issuedAt']) == row.issued_at and stamp(p['section']['validUntil']) == row.valid_for)
            # Validate as issued before re-evaluating freshness. Invalid latest rows
            # never cause fallback to older evidence.
            at_issue = stamp(p['section'].get('generatedAt') or p['section']['issuedAt'])
            validate_section(family, p['section'], generated=at_issue)
            s = deepcopy(p['section'])
            if family == 'dailyPv':
                s['today'], s['tomorrow'] = select_days(p['provenance']['days'], now)
            result[family] = expire_section(family, s, now=now)
            validate_section(family, result[family], generated=now)
        except (ValueError, KeyError, TypeError):
            result[family] = empty_section(family)
    result.update(status=aggregate_status(result), reason=None if all(result[k]['status'] == 'current' for k in SOURCES) else 'current_forecast_set_incomplete')
    return validate_forecast(result, generated=now)


def read_current_forecast(connection, *, now):
    rows = []
    for family in SOURCES:
        with connection.cursor() as cursor:
            cursor.execute('''SELECT source, issued_at, valid_for, metric, value, unit, payload
                FROM energy_analytics.forecast_snapshots
                WHERE source = %s AND metric = %s AND issued_at <= %s AND captured_at <= %s
                ORDER BY issued_at DESC, captured_at DESC, snapshot_id DESC LIMIT 1''',
                (SOURCES[family], MARKERS[family], now, now))
            row = cursor.fetchone()
            if row is not None:
                try:
                    rows.append(ForecastSnapshot(*row))
                except ValueError:
                    pass
    return forecast_from_markers(rows, now=now)


def forecast_health(forecast):
    return ('ok' if forecast['status'] == 'current' else forecast['status'],
            [family + '_' + (forecast[family]['reason'] or forecast[family]['status']) for family in SOURCES if forecast[family]['status'] != 'current'])


def build_current_ui_payload(v4, forecast):
    from .ui_payload import validate_energy_ui_payload
    require(v4.get('schema') == 'earthship-energy-ui/v4', 'v5 requires qualified v4 accounting and AC')
    validate_energy_ui_payload(v4)
    result = deepcopy(v4)
    result.update(schema='earthship-energy-ui/v5', forecast=forecast)
    health, reasons = forecast_health(forecast)
    result['health']['forecast'] = health
    result['health']['reasons'] = sorted(set([r for r in result['health']['reasons'] if r not in ('no_forecast_snapshot', 'forecast_issue_older_than_6h')] + reasons))[:16]
    result['health']['status'] = ('ok' if all(result['health'][name] == 'ok'
        for name in ('analytics', 'forecast', 'bms', 'schneider', 'weather', 'collector', 'publisher')) else 'degraded')
    if result['health']['status'] != 'ok' and result['status'] == 'ok':
        result['status'] = 'degraded'
    return validate_energy_ui_payload(result, now=stamp(result['generatedAt']))


def verify_current_writer(connection):
    """Admit a dedicated role, never the raw-history owner or a superuser."""
    with connection.cursor() as cursor:
        cursor.execute("""SELECT
          has_table_privilege(current_user, 'energy_analytics.forecast_snapshots', 'SELECT'),
          has_table_privilege(current_user, 'energy_analytics.forecast_snapshots', 'INSERT'),
          has_table_privilege(current_user, 'energy_analytics.forecast_snapshots', 'UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'),
          has_schema_privilege(current_user, 'energy_analytics', 'USAGE'),
          has_schema_privilege(current_user, 'energy_analytics', 'CREATE'),
          (SELECT rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls FROM pg_roles WHERE rolname=current_user),
          COALESCE(has_sequence_privilege(current_user,
            pg_get_serial_sequence('energy_analytics.forecast_snapshots','snapshot_id'), 'USAGE'), true),
          EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%'
              AND n.nspname NOT LIKE 'pg_temp_%' AND c.relkind IN ('r','p','v','f')
              AND c.oid <> 'energy_analytics.forecast_snapshots'::regclass
              AND has_table_privilege(current_user,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE'))""")
        require(cursor.fetchone() == (True, True, False, True, False, False, True, False),
                'dedicated append-only forecast writer privileges required')


def persist_current_forecasts(connection, rows, *, now):
    """Append real validated evidence; conflicting duplicate identities abort atomically."""
    from psycopg2.extras import Json
    allowed = {
        'weather': {'weathernext3.weather.temperature_f', 'weathernext3.weather.radiation_wm2'},
        'dailyPv': {'weathernext3.pv.remaining_today_kwh', 'weathernext3.pv.full_day_kwh'},
        'householdEnergy': {'household.pv.potential_next_24h_kwh', 'household.pv.potential_remaining_today_kwh', 'household.pv.conditional_captured_next_24h_kwh'},
    }
    inserted = 0
    try:
        require(type(rows) is list and len(rows) <= 600)
        markers = {r.payload['family']: r for r in rows if r.metric in MARKERS.values()}
        for r in rows:
            family = r.payload.get('family')
            require(family in SOURCES and family in markers and r.source == SOURCES[family] and r.metric in allowed[family] | {MARKERS[family]} and r.issued_at <= now)
            m = markers[family]
            require(m.metric == MARKERS[family] and m.value is None and m.unit is None)
            base = {k: r.payload[k] for k in ('adapter', 'family', 'schema', 'productSha256', 'section', 'provenance')}
            require(base == m.payload and r.issued_at == m.issued_at)
            # Stored day labels belong to the original publication, including a
            # still-valid prior-day product captured after local midnight.
            as_issued = stamp(base['section'].get('generatedAt') or base['section']['issuedAt'])
            validate_section(family, base['section'], generated=as_issued)
            require(m.issued_at <= as_issued <= now < m.valid_for)
            require(base['schema'] == PRODUCT_SCHEMAS[family] and base['adapter'] == ADAPTER and stamp(base['section']['issuedAt']) == m.issued_at and stamp(base['section']['validUntil']) == m.valid_for and base['section']['productSha256'] == base['productSha256'])
        with connection.cursor() as cursor:
            for r in rows:
                key = (r.source, r.issued_at, r.valid_for, r.metric)
                cursor.execute('''INSERT INTO energy_analytics.forecast_snapshots
                    (source, issued_at, valid_for, metric, value, unit, payload)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (source, issued_at, valid_for, metric) DO NOTHING''',
                    (*key, r.value, r.unit, Json(r.payload)))
                inserted += max(0, cursor.rowcount)
                cursor.execute('SELECT value, unit, payload FROM energy_analytics.forecast_snapshots WHERE source=%s AND issued_at=%s AND valid_for=%s AND metric=%s', key)
                require(cursor.fetchone() == (r.value, r.unit, r.payload), 'conflicting immutable forecast identity')
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return inserted
