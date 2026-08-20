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
        "hours_above_90": 4.0,
        "hours_above_95": 1.0,
        "min_temperature_c": 10.0,
        "max_temperature_c": 25.0,
        "cumulative_efc": 4.2,
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
        "hours_above_90": 6.0,
        "hours_above_95": 2.0,
        "min_temperature_c": 11.0,
        "max_temperature_c": 26.0,
        "cumulative_efc": 4.37,
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
    assert report["observed"] == {
        "lowest_soc_pct": 70.0,
        "median_min_soc_pct": 75.0,
        "p05_min_soc_pct": 70.5,
        "days_below_soc_pct": {"75": 1, "60": 0, "50": 0, "40": 0, "25": 0},
        "longest_no_full_sequence_days": 1,
        "worst_deficit_period": {
            "start": "2026-01-01",
            "end": "2026-01-01",
            "days": 1,
            "deficit_kwh": 1.0,
            "pv_kwh": 4.0,
            "load_kwh": 5.0,
            "time_to_reach_99_days": 1,
        },
    }
    assert report["pv_storage_tradeoff"]["pv_100pct_storage_100pct"]["sufficient"] is True
    assert report["pv_storage_tradeoff"]["pv_150pct_storage_60pct"]["minimum_soc_pct"] >= 20


def test_winter_report_does_not_present_summer_as_winter_evidence():
    summer = [{**DAILY[0], "local_date": date(2026, 8, 1)}]
    report = winter_report(summer, nominal_usable_kwh=20.48, reserve_soc_pct=20)
    assert report["winter_observation_days"] == 0
    assert report["conclusion"] == "insufficient_winter_observations"
    assert report["observed"] is None
    assert report["capacity_scenarios_pct"] == {}
    assert report["pv_storage_tradeoff"] == {}


def test_winter_report_excludes_non_winter_rows_from_observed_and_simulated_evidence():
    summer_deficit = {
        **DAILY[0],
        "local_date": date(2026, 8, 1),
        "min_soc_pct": 5.0,
        "pv_kwh": 0.0,
        "load_kwh": 100.0,
    }
    report = winter_report(
        [*DAILY, summer_deficit], nominal_usable_kwh=20.48, reserve_soc_pct=20
    )
    assert report["winter_observation_days"] == 2
    assert report["observed"]["lowest_soc_pct"] == 70.0
    baseline = report["capacity_scenarios_pct"]["100"]
    assert baseline["unserved_kwh"] == 0.0


def test_lifecycle_report_preserves_throughput_and_efc():
    report = lifecycle_report(DAILY)
    assert report["charge_kwh"] == 7
    assert report["discharge_kwh"] == 7
    assert report["cumulative_efc"] == 0.34
    assert report["ending_cumulative_efc"] == 4.37
    assert report["high_soc_exposure_hours"] == {"above_90": 10.0, "above_95": 3.0}
    assert report["temperature_exposure_c"] == {"minimum": 10.0, "maximum": 26.0}
    assert report["module_health"] == {"status": "unavailable", "reason": "no_module_samples"}
