"""Qualified UI v3 projection; no reads or legacy daily fallback."""
from datetime import date, timedelta
import re
from zoneinfo import ZoneInfo

from .power_evidence import utc
from .power_report import build_power_report
from .power_store import POLICY
from .soc_exposure import lifecycle_soc_exposure
from .ui_payload import _aware, _exact, _integer, _number

ACCOUNTING = {'basis','cutover','daysPresent','latestBatteryCoverage',
    'latestPvCoverage','latestRevision','loadStatus','missingDays','policy',
    'windowEndExclusive','windowStart'}


def qualified_full_streak(rows, end_date):
    """Return the observed no-full run and days since a witnessed 99% day.

    The selected revisions must be ordered and identity-validated by the
    caller. Never bridge a missing/partial day or invent a full-charge anchor.
    """
    expected = end_date - timedelta(days=1)
    no_full_days = 0
    for row in reversed(rows):
        battery = row['payload']['battery']
        if (row['local_date'] != expected or battery.get('quality') != 'ok'
                or battery.get('coverage', 0) < .9):
            break
        if battery.get('reached_99') is True:
            return no_full_days, no_full_days
        no_full_days += 1
        expected -= timedelta(days=1)
    return no_full_days, None


def validate_accounting(payload):
    if payload['timezone'] != 'America/Denver':
        raise ValueError('qualified UI requires site timezone America/Denver')
    a = _exact(payload['accounting'], ACCOUNTING, 'accounting')
    if (a['policy'] != POLICY or a['basis'] != 'observed_qualified_throughput_in_requested_window'
            or a['loadStatus'] != 'ac_load_evidence_unqualified'):
        raise ValueError('invalid qualified policy')
    zone = ZoneInfo(payload['timezone'])
    generated = _aware(payload['generatedAt'], 'generatedAt')
    cutover = _aware(a['cutover'], 'cutover')
    start, end = (date.fromisoformat(a[key]) for key in ('windowStart','windowEndExclusive'))
    if (start.isoformat() != a['windowStart'] or end.isoformat() != a['windowEndExclusive']
            or not 1 <= (end-start).days <= 366 or end > generated.astimezone(zone).date()
            or cutover > generated):
        raise ValueError('invalid qualified window')
    present = _integer(a['daysPresent'], 'daysPresent', optional=False)
    missing = _integer(a['missingDays'], 'missingDays', optional=False)
    if present + missing != (end-start).days:
        raise ValueError('invalid qualified day counts')
    for key in ('latestBatteryCoverage','latestPvCoverage'):
        value = _number(a[key], key)
        if value is not None and not 0 <= value <= 1:
            raise ValueError('invalid qualified coverage')
    battery, energy, lifecycle = payload['battery'], payload['energy'], payload['lifecycle']
    if present == 0:
        if any(v is not None for v in (a['latestRevision'],payload['throughDate'],energy['latest'],
                a['latestBatteryCoverage'],a['latestPvCoverage'],battery['latestEfc'],
                lifecycle['periodEfc'],lifecycle['chargeKwh'],lifecycle['dischargeKwh'])):
            raise ValueError('empty qualified series has values')
    else:
        r = _exact(a['latestRevision'], {'computedAt','id','sha256'}, 'revision')
        revision_id = _integer(r['id'], 'revision.id', optional=False)
        computed = _aware(r['computedAt'], 'revision.computedAt')
        through = date.fromisoformat(payload['throughDate']) if payload['throughDate'] else None
        if (not 0 < revision_id <= 2**53-1 or not isinstance(r['sha256'],str)
                or re.fullmatch('[a-f0-9]{64}',r['sha256']) is None
                or not cutover <= computed <= generated or through is None
                or not max(start,cutover.astimezone(zone).date()) <= through < end
                or computed.astimezone(zone).date() <= through or energy['latest'] is None
                or a['latestBatteryCoverage'] is None or a['latestPvCoverage'] is None):
            raise ValueError('invalid qualified revision')
    if (battery['endingCumulativeEfc'] is not None or lifecycle['endingCumulativeEfc'] is not None
            or (energy['latest'] or {}).get('loadKwh') is not None
            or payload['winter']['worstDeficitPeriod'] is not None):
        raise ValueError('unqualified lifetime or load total')
    latest = energy['latest'] or {}
    for value in (lifecycle['periodEfc'],lifecycle['chargeKwh'],lifecycle['dischargeKwh'],
                  latest.get('pvKwh'),latest.get('chargeKwh'),latest.get('dischargeKwh')):
        if value is not None and value < 0:
            raise ValueError('negative qualified throughput')
    if missing and payload['status'] == 'ok':
        raise ValueError('missing days claimed complete')
    if ((a['latestBatteryCoverage'] is not None and a['latestBatteryCoverage'] < .9 and battery['status']=='ok')
            or (a['latestPvCoverage'] is not None and a['latestPvCoverage'] < .9 and energy['status']=='ok')):
        raise ValueError('partial coverage claimed complete')


def build_qualified_ui_payload(rows, *, epoch_id, cutover, start_date, end_date,
                               generated_at, timezone_name, forecast, health, module_health):
    from .ui_payload import build_energy_ui_payload, validate_energy_ui_payload
    report = build_power_report(rows, epoch_id=epoch_id, cutover=cutover,
        start_date=start_date,end_date=end_date,as_of=generated_at)
    # Reuse empty v2 sections, never legacy daily values. Projection below fills
    # only evidence represented by the selected qualified revisions.
    result = build_energy_ui_payload(generated_at=generated_at, timezone_name=timezone_name,
        epoch_id=epoch_id,daily_rows=[],winter=None,lifecycle=None,
        module_health=module_health,forecast=forecast,health=health)
    result['schema'] = 'earthship-energy-ui/v3'
    latest = rows[-1] if rows else None
    raw = latest['payload'] if latest else None
    battery = raw['battery'] if raw else None
    pv = raw['pv'] if raw else None
    result['accounting'] = {
        'policy':POLICY,'basis':report['basis'],'cutover':utc(cutover).isoformat(),
        'windowStart':start_date.isoformat(),'windowEndExclusive':end_date.isoformat(),
        'daysPresent':len(rows),'missingDays':len(report['missing_dates']),
        'latestBatteryCoverage':battery['coverage'] if battery else None,
        'latestPvCoverage':pv['coverage'] if pv else None,
        'latestRevision':({'id':latest['snapshot_id'],'sha256':latest['payload_sha256'],
                           'computedAt':utc(latest['computed_at']).isoformat()} if latest else None),
        'loadStatus':'ac_load_evidence_unqualified',
    }
    result['status'] = 'degraded' if latest else 'unavailable'
    result['throughDate'] = latest['local_date'].isoformat() if latest else None
    if latest:
        battery_ok = battery.get('quality') == 'ok' and battery['coverage'] >= .9
        current_no_full, days_since_full = qualified_full_streak(rows, end_date) if battery_ok else (None, None)
        if latest['local_date'] != end_date - timedelta(days=1):
            current_no_full = days_since_full = None
        result['battery'].update(status='ok' if battery_ok else 'degraded',
            latestMinSocPct=battery.get('min_soc_pct') if battery_ok else None,
            latestDepthOfDischargePct=battery.get('depth_of_discharge_pct') if battery_ok else None,
            latestReached99=battery.get('reached_99') if battery_ok else None,
            daysSinceFull=days_since_full,currentNoFullDays=current_no_full,
            latestEfc=battery['daily_efc'])
        result['energy'].update(status='degraded', latest={
            'date':result['throughDate'],'pvKwh':pv['energy_kwh'],'loadKwh':None,
            'chargeKwh':battery['charge_kwh'],'dischargeKwh':battery['discharge_kwh']})
    totals = report['totals']
    result['lifecycle'].update(status='degraded' if latest else 'unavailable',
        chargeKwh=totals['charge_kwh'],dischargeKwh=totals['discharge_kwh'],
        periodEfc=totals['daily_efc'])
    exposure = lifecycle_soc_exposure(rows)
    if (rows and not report['missing_dates'] and len(exposure['daily']) == len(rows)
            and all(day['coverage'] >= .9 for day in exposure['daily'])):
        result['lifecycle'].update(
            highSocHoursAbove90=exposure['above_90_hours'],
            highSocHoursAbove95=exposure['above_95_hours'])
    return validate_energy_ui_payload(result,now=generated_at)
