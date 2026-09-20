"""Qualified-only reporting: observed throughput, never a lifetime estimate."""
from datetime import date, datetime, timedelta
from math import fsum

from .power_evidence import utc
from .power_snapshot_reader import MAX_DAYS, read_power_snapshots
from .power_store import POLICY, encode_snapshot


def build_power_report(rows, *, epoch_id, cutover, start_date, end_date, as_of):
    if type(start_date) is not date or type(end_date) is not date:
        raise ValueError('local date bounds required')
    if not 1 <= (end_date-start_date).days <= MAX_DAYS:
        raise ValueError('power report window must be 1 to 366 days')
    cutover, as_of = utc(cutover), utc(as_of)
    daily = []
    previous = None
    for row in rows:
        payload = row['payload']
        day, payload_cutover, _, digest = encode_snapshot(payload)
        if (row['epoch_id'] != epoch_id or row['policy'] != POLICY
                or utc(row['cutover']) != cutover or payload_cutover != cutover
                or row['local_date'] != day or not start_date <= day < end_date
                or (previous is not None and day <= previous)
                or row['payload_sha256'] != digest or utc(row['computed_at']) > as_of):
            raise ValueError('power report revision identity mismatch')
        if utc(datetime.fromisoformat(payload['window_end'])) > as_of:
            raise ValueError('power report requires completed windows')
        battery, pv = payload['battery'], payload['pv']
        daily.append({
            'local_date': day.isoformat(), 'snapshot_id': row['snapshot_id'],
            'payload_sha256': digest, 'computed_at': utc(row['computed_at']).isoformat(),
            'charge_kwh': battery['charge_kwh'], 'discharge_kwh': battery['discharge_kwh'],
            'daily_efc': battery['daily_efc'], 'battery_daily_coverage': battery['coverage'],
            'pv_input_kwh': pv['energy_kwh'], 'pv_output_kwh': pv['output_energy_kwh'],
            'pv_daily_coverage': pv['coverage'],
        })
        previous = day
    present = {row['local_date'] for row in daily}
    missing = [(start_date+timedelta(days=i)).isoformat()
               for i in range((end_date-start_date).days)
               if (start_date+timedelta(days=i)).isoformat() not in present]
    return {
        'report': 'qualified_power', 'schema_version': 1, 'epoch_id': epoch_id,
        'accounting_policy': POLICY, 'cutover': cutover.isoformat(),
        'as_of': as_of.isoformat(), 'window_start': start_date.isoformat(),
        'window_end_exclusive': end_date.isoformat(),
        'basis': 'observed_qualified_throughput_in_requested_window',
        'legacy_included': False, 'missing_dates': missing,
        'days_present': len(daily), 'daily': daily,
        'totals': {name: fsum(row[name] for row in daily) if daily else None
                   for name in ('charge_kwh','discharge_kwh','daily_efc',
                                'pv_input_kwh','pv_output_kwh')},
        'balance': {'load_kwh': None, 'surplus_deficit_kwh': None,
                    'reason': 'ac_load_evidence_unqualified'},
    }


def read_power_report(settings, **kwargs):
    return build_power_report(read_power_snapshots(settings, **kwargs), **kwargs)


def build_qualified_lifecycle_report(rows, **kwargs):
    """Period use only; no lifetime, temperature or BMS-counter inference."""
    evidence = build_power_report(rows, **kwargs)
    daily = evidence['daily']
    return {
        **{key: value for key, value in evidence.items()
           if key not in ('report', 'totals', 'balance', 'daily')},
        'report': 'qualified_lifecycle',
        'status': 'partial_observations' if daily else 'unavailable',
        'charge_kwh': evidence['totals']['charge_kwh'],
        'discharge_kwh': evidence['totals']['discharge_kwh'],
        'period_efc': evidence['totals']['daily_efc'],
        'lifetime_efc': None,
        'ending_cumulative_efc': None,
        'daily': [{key: value for key, value in day.items()
                   if not key.startswith('pv_')} for day in daily],
        'unavailable': {
            'lifetime_efc': 'requested_window_is_not_complete_bank_lifetime',
            'temperature_exposure': 'not_qualified_by_power_evidence',
            'high_soc_exposure': 'not_qualified_by_power_evidence',
            'bms_cycle_counter_comparison': 'independent_module_counter_evidence_required',
        },
    }


def read_qualified_lifecycle_report(settings, **kwargs):
    return build_qualified_lifecycle_report(read_power_snapshots(settings, **kwargs), **kwargs)
