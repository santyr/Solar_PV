"""Read existing atomic SoC exposure from revision-validated daily snapshots."""
from datetime import datetime
from math import fsum, isclose, isfinite
from .power_evidence import utc


def lifecycle_soc_exposure(rows):
    daily = []
    unavailable = []
    for row in rows:
        payload = row['payload']
        day = row['local_date'].isoformat()
        quality = [q for q in payload.get('source_quality', [])
                   if q.get('canonical_name') == 'battery.soc_pct']
        if len(quality) > 1:
            raise ValueError('ambiguous SoC exposure quality')
        detail = quality[0].get('detail', {}) if quality else {}
        if (detail.get('policy') != 'atomic_bms_evidence'
                or detail.get('freshness_basis') != 'BMS_SOC_Evidence_JSON'
                or detail.get('reason') is not None):
            unavailable.append(day)
            continue
        window = (utc(datetime.fromisoformat(payload['window_end'])) -
                  utc(datetime.fromisoformat(payload['window_start']))).total_seconds()
        valid = detail.get('valid_seconds')
        duration = detail.get('window_seconds')
        coverage = quality[0].get('coverage')
        above90 = payload['battery'].get('hours_above_90')
        above95 = payload['battery'].get('hours_above_95')
        values = (valid, duration, coverage, above90, above95)
        if any(type(x) not in (int, float) or not isfinite(x) for x in values):
            raise ValueError('invalid atomic SoC exposure values')
        if (not isclose(duration, window, abs_tol=1e-6) or not 0 <= valid <= window
                or not isclose(coverage, valid/window, abs_tol=1e-9)
                or not 0 <= above95 <= above90 <= valid/3600 + 1e-9):
            raise ValueError('inconsistent atomic SoC exposure coverage')
        if valid == 0:
            unavailable.append(day)
            continue
        daily.append({'local_date': day, 'coverage': coverage, 'valid_seconds': valid,
                      'window_seconds': window, 'above_90_hours': above90,
                      'above_95_hours': above95, 'snapshot_id': row['snapshot_id'],
                      'payload_sha256': row['payload_sha256']})
    return {'basis': 'observed_atomic_bms_soc_intervals', 'daily': daily,
            'unavailable_present_dates': unavailable,
            'above_90_hours': fsum(x['above_90_hours'] for x in daily) if daily else None,
            'above_95_hours': fsum(x['above_95_hours'] for x in daily) if daily else None,
            'valid_seconds': fsum(x['valid_seconds'] for x in daily) if daily else None}
