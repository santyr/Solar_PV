"""Deterministic historical energy-balance scenario replay."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    usable_battery_kwh: float
    reserve_soc_pct: float
    pv_multiplier: float
    load_multiplier: float
    inverter_efficiency: float

    def __post_init__(self):
        if self.usable_battery_kwh <= 0:
            raise ValueError("usable battery capacity must be positive")
        if not 0 <= self.reserve_soc_pct < 100:
            raise ValueError("reserve SOC must be between 0 and 100")
        if self.pv_multiplier < 0 or self.load_multiplier < 0:
            raise ValueError("PV/load multipliers must be non-negative")
        if not 0 < self.inverter_efficiency <= 1:
            raise ValueError("inverter efficiency must be in (0, 1]")


@dataclass(frozen=True)
class ScenarioResult:
    minimum_soc_pct: float
    ending_soc_pct: float
    unserved_kwh: float
    curtailed_kwh: float
    worst_deficit_days: int
    sufficient: bool


def replay_energy_balance(history, scenario: Scenario) -> ScenarioResult:
    state = scenario.usable_battery_kwh
    reserve = scenario.usable_battery_kwh * scenario.reserve_soc_pct / 100.0
    minimum = state
    unserved = 0.0
    curtailed = 0.0
    deficit_run = 0
    worst_deficit = 0
    for row in sorted(history, key=lambda item: item["local_date"]):
        pv = max(0.0, float(row["pv_kwh"])) * scenario.pv_multiplier
        load_dc = (
            max(0.0, float(row["load_kwh"]))
            * scenario.load_multiplier
            / scenario.inverter_efficiency
        )
        net = pv - load_dc
        if net < 0:
            deficit_run += 1
            worst_deficit = max(worst_deficit, deficit_run)
        else:
            deficit_run = 0
        proposed = state + net
        if proposed > scenario.usable_battery_kwh:
            curtailed += proposed - scenario.usable_battery_kwh
            state = scenario.usable_battery_kwh
        elif proposed < reserve:
            unserved += reserve - proposed
            state = reserve
        else:
            state = proposed
        minimum = min(minimum, state)
    return ScenarioResult(
        minimum_soc_pct=minimum / scenario.usable_battery_kwh * 100.0,
        ending_soc_pct=state / scenario.usable_battery_kwh * 100.0,
        unserved_kwh=unserved,
        curtailed_kwh=curtailed,
        worst_deficit_days=worst_deficit,
        sufficient=unserved == 0.0,
    )
