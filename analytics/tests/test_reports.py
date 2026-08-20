from datetime import date

from earthship_energy.reports import lifecycle_report, monthly_report, winter_report


DAILY = [
    {
        "local_date": date(2026, 1, 1),
        "min_soc_pct": 70.0,
        "pv_kwh": 4.0,
        "load_kwh": 5.0,
        "charge_kwh": 3.0,
        "discharge_kwh": 4.0,
        "daily_efc": 0.17,
        "reached_99": False,
        "quality": "ok",
    },
    {
        "local_date": date(2026, 1, 2),
        "min_soc_pct": 80.0,
        "pv_kwh": 7.0,
        "load_kwh": 5.0,
        "charge_kwh": 4.0,
        "discharge_kwh": 3.0,
        "daily_efc": 0.17,
        "reached_99": True,
        "quality": "ok",
    },
]


def test_monthly_report_is_reproducible_and_versioned():
    first = monthly_report(DAILY, epoch_id="discover_4_module_2026")
    second = monthly_report(DAILY, epoch_id="discover_4_module_2026")
    assert first == second
    assert first["schema_version"] == 1
    assert first["metrics"]["pv_kwh"] == 11
    assert first["metrics"]["load_kwh"] == 10


def test_winter_report_runs_required_capacity_scenarios():
    report = winter_report(DAILY, nominal_usable_kwh=20.48, reserve_soc_pct=20)
    assert list(report["capacity_scenarios_pct"]) == ["100", "90", "80", "70", "60"]
    assert report["question"] == "Are four Discover modules still sufficient?"
    assert report["winter_observation_days"] == 2
    assert report["conclusion"] == "scenario_results_available"


def test_winter_report_does_not_present_summer_as_winter_evidence():
    summer = [{**DAILY[0], "local_date": date(2026, 8, 1)}]
    report = winter_report(summer, nominal_usable_kwh=20.48, reserve_soc_pct=20)
    assert report["winter_observation_days"] == 0
    assert report["conclusion"] == "insufficient_winter_observations"


def test_lifecycle_report_preserves_throughput_and_efc():
    report = lifecycle_report(DAILY)
    assert report["charge_kwh"] == 7
    assert report["discharge_kwh"] == 7
    assert report["cumulative_efc"] == 0.34
