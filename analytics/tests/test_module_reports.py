from datetime import datetime, timedelta, timezone

import pytest

from earthship_energy.reports import module_health_report


UTC = timezone.utc
START = datetime(2026, 8, 1, tzinfo=UTC)


def sample(module, hour, *, current, spread, charge, discharge, faults=()):
    return {
        "batch_id": 7,
        "source_name": "lynk-2026-08.csv",
        "sha256": "a" * 64,
        "module_id": module,
        "sampled_at": START + timedelta(hours=hour),
        "soc_pct": 90.0 - hour,
        "voltage_v": 52.0,
        "current_a": current,
        "temperature_c": 24.0 + hour,
        "cell_spread_mv": spread,
        "charge_kwh": charge,
        "discharge_kwh": discharge,
        "faults": list(faults),
    }


def test_module_health_report_preserves_provenance_and_trends():
    rows = [
        sample("module-1", 0, current=2.0, spread=8, charge=10, discharge=9),
        sample("module-2", 0, current=1.0, spread=9, charge=10, discharge=9),
        sample("module-1", 1, current=3.0, spread=10, charge=10.5, discharge=9.2),
        sample("module-2", 1, current=1.0, spread=12, charge=10.4, discharge=9.3, faults=("WARN",)),
    ]
    report = module_health_report(rows)
    assert report["schema_version"] == 1
    assert report["window"] == {
        "start": "2026-08-01T00:00:00+00:00",
        "end": "2026-08-01T01:00:00+00:00",
        "samples": 4,
    }
    assert report["provenance"] == [{
        "batch_id": 7,
        "source_name": "lynk-2026-08.csv",
        "sha256": "a" * 64,
    }]
    assert report["summary"]["module_count"] == 2
    assert report["summary"]["latest_current_sharing_range_a"] == 2.0
    assert report["summary"]["maximum_cell_spread_mv"] == 12.0
    first = report["modules"]["module-1"]
    assert first["charge_throughput_delta_kwh"] == 0.5
    assert first["discharge_throughput_delta_kwh"] == 0.2
    assert first["latest_current_deviation_a"] == 1.0
    assert report["modules"]["module-2"]["faults_observed"] == ["WARN"]


def test_module_health_report_explicitly_reports_no_samples():
    assert module_health_report([]) == {
        "report": "module_health",
        "schema_version": 1,
        "status": "unavailable",
        "reason": "no_module_samples",
        "modules": {},
        "provenance": [],
    }


@pytest.mark.parametrize('counters', [
    [10, 9], [10, 1, 11], [10, None, 11], [None, 10, 11],
    [10, 11, None], [10, float('nan'), 11], [10, float('inf')],
    [-1, 2], [True, 2], [10, 'invalid', 11], [10],
])
def test_module_counter_uncertainty_is_not_zero_or_endpoint_delta(counters):
    rows = [sample('module-1', hour, current=0, spread=0,
                   charge=value, discharge=20 + hour)
            for hour, value in enumerate(counters)]
    result = module_health_report(rows)['modules']['module-1']
    assert result['charge_throughput_delta_kwh'] is None
    if len(counters) > 1:
        assert result['discharge_throughput_delta_kwh'] == len(counters) - 1


def test_module_counter_observed_zero_and_sorted_growth_remain_valid():
    rows = [sample('module-1', hour, current=0, spread=0,
                   charge=10, discharge=20 + hour)
            for hour in [2, 0, 1]]
    result = module_health_report(rows)['modules']['module-1']
    assert result['charge_throughput_delta_kwh'] == 0
    assert result['discharge_throughput_delta_kwh'] == 2


def test_module_conflicting_same_timestamp_counters_are_unknown():
    rows = [sample('module-1', hour, current=0, spread=0,
                   charge=value, discharge=20)
            for hour, value in [(0, 10), (0, 11), (1, 12)]]
    result = module_health_report(rows)['modules']['module-1']
    assert result['charge_throughput_delta_kwh'] is None
    assert result['discharge_throughput_delta_kwh'] == 0
