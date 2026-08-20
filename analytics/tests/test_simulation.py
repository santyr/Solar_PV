from datetime import date

import pytest

from earthship_energy.simulation import Scenario, replay_energy_balance


HISTORY = [
    {"local_date": date(2026, 1, 1), "pv_kwh": 0.0, "load_kwh": 5.0},
    {"local_date": date(2026, 1, 2), "pv_kwh": 0.0, "load_kwh": 5.0},
]


def test_replay_tracks_reserve_unserved_energy_and_minimum_soc():
    result = replay_energy_balance(
        HISTORY,
        Scenario(
            usable_battery_kwh=20.0,
            reserve_soc_pct=20.0,
            pv_multiplier=1.0,
            load_multiplier=1.0,
            inverter_efficiency=1.0,
        ),
    )
    assert result.minimum_soc_pct == pytest.approx(50.0)
    assert result.unserved_kwh == 0
    assert result.worst_deficit_days == 2


def test_capacity_and_efficiency_change_sufficiency_without_mutating_history():
    scenario = Scenario(10.0, 20.0, 1.0, 1.0, 0.9)
    result = replay_energy_balance(HISTORY, scenario)
    assert result.minimum_soc_pct == pytest.approx(20.0)
    assert result.unserved_kwh > 0
    assert HISTORY[0]["load_kwh"] == 5.0


def test_invalid_scenario_is_rejected():
    with pytest.raises(ValueError):
        Scenario(0, 20, 1, 1, 0.9)
