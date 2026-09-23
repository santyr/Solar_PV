"""Observed AC-load accounting without inventing a DC-to-AC energy balance.

The inverter-output stream is whole-house load only inside a separately
attested inverter-only period. MPPT output is DC and cannot be subtracted from
AC output to claim surplus, battery flow or conversion efficiency.
"""
from dataclasses import asdict, dataclass

from .ac_reader import read_ac_history
from .power_evidence import utc
from .power_intervals import account_common_power, account_power_intervals
from .power_reader import read_power_history


@dataclass(frozen=True)
class AcDayObservation:
    basis: str
    observed_ac_load_kwh: float | None
    ac_coverage: float
    common_pv_dc_kwh: float | None
    common_ac_load_kwh: float | None
    common_coverage: float
    balance_kwh: None
    balance_reason: str


def summarize_ac_day(ac_intervals, pv_dc_intervals, *, window_start, window_end):
    """Integrate measured intervals; missing time is not a zero-Watt sample."""
    ac = account_power_intervals(ac_intervals, window_start=window_start,
                                 window_end=window_end)
    pv = account_power_intervals(pv_dc_intervals, window_start=window_start,
                                 window_end=window_end)
    common_pv, common_ac = account_common_power(
        pv_dc_intervals, ac_intervals, window_start=window_start,
        window_end=window_end)
    if ac.negative_kwh or pv.negative_kwh:
        raise ValueError('AC/PV output intervals must be nonnegative')
    common = common_ac.covered_seconds > 0
    return AcDayObservation(
        basis='inverter_output_observed_with_attested_topology',
        observed_ac_load_kwh=ac.positive_kwh if ac.covered_seconds else None,
        ac_coverage=ac.coverage,
        common_pv_dc_kwh=common_pv.positive_kwh if common else None,
        common_ac_load_kwh=common_ac.positive_kwh if common else None,
        common_coverage=common_ac.coverage,
        balance_kwh=None,
        balance_reason=('dc_pv_and_ac_load_cross_domain' if common
                        else 'no_common_qualified_intervals'),
    )


def read_ac_day_accounting(settings, *, ac_policy, power_policy, items, tables,
                           local_date, as_of):
    """Read both strict streams for a completed, topology-qualified local day.

    This is read-only and does not write a daily revision or publish to the UI.
    Both source readers fail closed on malformed rows and sequence ambiguity.
    """
    start, end = ac_policy.day_window(local_date, as_of=as_of)
    if utc(power_policy.cutover) > start:
        raise ValueError('existing PV evidence starts after requested day')
    ac_table = ac_policy.resolve_table(items, tables)
    power_table = power_policy.resolve_table(items, tables)
    ac_intervals = read_ac_history(
        settings, ac_table, start, end, cutover=ac_policy.cutover,
        topology_start=ac_policy.topology_from, topology_end=end)
    pv_intervals = read_power_history(
        settings, power_table, start, end,
        cutover=power_policy.cutover)['pv.output_power_w']
    result = summarize_ac_day(ac_intervals, pv_intervals,
                              window_start=start, window_end=end)
    return {'local_date': local_date.isoformat(), 'window_start': start.isoformat(),
            'window_end': end.isoformat(), 'ac_item': ac_policy.item_name,
            'ac_cutover': ac_policy.cutover.isoformat(),
            'topology_from': ac_policy.topology_from.isoformat(),
            'topology_until': (ac_policy.topology_until.isoformat()
                               if ac_policy.topology_until is not None else None),
            **asdict(result)}
