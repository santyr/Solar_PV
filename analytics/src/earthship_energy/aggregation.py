"""Pure daily aggregation and battery sign-calibration logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import sqrt
from typing import Iterable

from .series import (
    Point,
    coverage_ratio,
    duration_above,
    equivalent_full_cycles,
    integrate_trapezoid,
    time_weighted_mean,
)


class SignCalibrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SignCalibration:
    sign: str
    concordant: int
    discordant: int
    confidence: float
    correlation: float | None


@dataclass(frozen=True)
class PowerAggregate:
    energy_kwh: float
    peak_w: float | None
    productive_hours: float
    first_productive_at: datetime | None
    last_productive_at: datetime | None
    coverage: float
    quality: str


@dataclass(frozen=True)
class WeatherAggregate:
    min_temperature_c: float | None
    max_temperature_c: float | None
    mean_temperature_c: float | None
    irradiance_wh_m2: float
    peak_irradiance_w_m2: float | None
    precipitation_mm: float | None
    coverage: float
    quality: str


@dataclass(frozen=True)
class BatteryAggregate:
    min_soc_pct: float | None
    max_soc_pct: float | None
    mean_soc_pct: float | None
    sunrise_soc_pct: float | None
    sunset_soc_pct: float | None
    overnight_soc_drop_pct: float | None
    depth_of_discharge_pct: float | None
    hours_above_90: float
    hours_above_95: float
    hours_below_50: float
    hours_below_25: float
    charge_kwh: float
    discharge_kwh: float
    net_kwh: float
    daily_efc: float
    min_temperature_c: float | None
    max_temperature_c: float | None
    mean_temperature_c: float | None
    reached_95: bool
    reached_99: bool
    reached_100: bool
    first_reached_99_at: datetime | None
    coverage: float
    quality: str


def _correlation(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    x_ss = sum((x - x_mean) ** 2 for x in xs)
    y_ss = sum((y - y_mean) ** 2 for y in ys)
    if x_ss == 0 or y_ss == 0:
        return None
    return numerator / sqrt(x_ss * y_ss)


def calibrate_battery_power_sign(
    power_soc_delta_pairs: Iterable[tuple[float, float]],
    *,
    min_power_w: float = 100.0,
    min_soc_delta_pct: float = 0.1,
    minimum_pairs: int = 4,
    minimum_confidence: float = 0.9,
) -> SignCalibration:
    evidence = [
        (float(power), float(delta))
        for power, delta in power_soc_delta_pairs
        if abs(power) >= min_power_w and abs(delta) >= min_soc_delta_pct
    ]
    if len(evidence) < minimum_pairs:
        raise SignCalibrationError("insufficient sign-calibration evidence")
    same_sign = sum(1 for power, delta in evidence if power * delta > 0)
    opposite_sign = len(evidence) - same_sign
    if same_sign >= opposite_sign:
        sign = "positive_charging"
        concordant, discordant = same_sign, opposite_sign
    else:
        sign = "negative_charging"
        concordant, discordant = opposite_sign, same_sign
    confidence = concordant / len(evidence)
    if confidence < minimum_confidence:
        raise SignCalibrationError("conflicted sign-calibration evidence")
    return SignCalibration(
        sign=sign,
        concordant=concordant,
        discordant=discordant,
        confidence=confidence,
        correlation=_correlation(evidence),
    )


def _value_at(points: list[Point], at: datetime) -> float | None:
    ordered = sorted(points)
    if not ordered or at < ordered[0][0] or at > ordered[-1][0]:
        return None
    for left, right in zip(ordered, ordered[1:]):
        if left[0] <= at <= right[0]:
            seconds = (right[0] - left[0]).total_seconds()
            if seconds == 0:
                return right[1]
            fraction = (at - left[0]).total_seconds() / seconds
            return left[1] + fraction * (right[1] - left[1])
    return ordered[-1][1] if at == ordered[-1][0] else None


def value_at(points: list[Point], at: datetime) -> float | None:
    return _value_at(points, at)


def _quality(coverage: float) -> str:
    if coverage >= 0.9:
        return "ok"
    if coverage >= 0.5:
        return "partial"
    return "insufficient_data"


def aggregate_power(
    power_points: list[Point],
    window_start: datetime,
    window_end: datetime,
    *,
    max_gap: timedelta,
    productive_threshold_w: float = 10.0,
) -> PowerAggregate:
    window_seconds = (window_end - window_start).total_seconds()
    nonnegative = [(at, max(0.0, value)) for at, value in power_points]
    integration = integrate_trapezoid(nonnegative, max_gap)
    coverage = coverage_ratio(integration.covered_seconds, window_seconds)
    productive = [
        (at, value) for at, value in nonnegative
        if value > productive_threshold_w
    ]
    return PowerAggregate(
        energy_kwh=integration.value_hours / 1000.0,
        peak_w=max((value for _, value in nonnegative), default=None),
        productive_hours=(
            duration_above(nonnegative, productive_threshold_w, max_gap) / 3600.0
        ),
        first_productive_at=productive[0][0] if productive else None,
        last_productive_at=productive[-1][0] if productive else None,
        coverage=coverage,
        quality=_quality(coverage),
    )


def aggregate_weather(
    temperature_c_points: list[Point],
    irradiance_points: list[Point],
    window_start: datetime,
    window_end: datetime,
    *,
    max_gap: timedelta,
    precipitation_mm_points: list[Point] | None = None,
) -> WeatherAggregate:
    window_seconds = (window_end - window_start).total_seconds()
    temperature = integrate_trapezoid(temperature_c_points, max_gap)
    irradiance = integrate_trapezoid(
        [(at, max(0.0, value)) for at, value in irradiance_points], max_gap
    )
    coverage = min(
        coverage_ratio(temperature.covered_seconds, window_seconds),
        coverage_ratio(irradiance.covered_seconds, window_seconds),
    )
    temperature_values = [value for _, value in temperature_c_points]
    irradiance_values = [max(0.0, value) for _, value in irradiance_points]
    return WeatherAggregate(
        min_temperature_c=min(temperature_values, default=None),
        max_temperature_c=max(temperature_values, default=None),
        mean_temperature_c=time_weighted_mean(temperature),
        irradiance_wh_m2=irradiance.value_hours,
        peak_irradiance_w_m2=max(irradiance_values, default=None),
        precipitation_mm=(
            max(0.0, precipitation_mm_points[-1][1])
            if precipitation_mm_points else None
        ),
        coverage=coverage,
        quality=_quality(coverage),
    )


def aggregate_battery(
    *,
    soc_points: list[Point],
    power_points: list[Point],
    temperature_c_points: list[Point],
    window_start: datetime,
    window_end: datetime,
    max_gap: timedelta,
    nominal_usable_kwh: float,
    power_sign: str,
    sunrise: datetime | None = None,
    sunset: datetime | None = None,
) -> BatteryAggregate:
    if power_sign not in {"positive_charging", "negative_charging"}:
        raise SignCalibrationError("battery power sign has not been calibrated")
    sign_factor = 1.0 if power_sign == "positive_charging" else -1.0
    signed = [(at, value * sign_factor) for at, value in power_points]
    charge = integrate_trapezoid(
        [(at, max(0.0, value)) for at, value in signed], max_gap
    )
    discharge = integrate_trapezoid(
        [(at, max(0.0, -value)) for at, value in signed], max_gap
    )
    soc_integration = integrate_trapezoid(soc_points, max_gap)
    temperature = integrate_trapezoid(temperature_c_points, max_gap)
    window_seconds = (window_end - window_start).total_seconds()
    coverage = min(
        coverage_ratio(soc_integration.covered_seconds, window_seconds),
        coverage_ratio(charge.covered_seconds, window_seconds),
        coverage_ratio(temperature.covered_seconds, window_seconds),
    )
    charge_kwh = charge.value_hours / 1000.0
    discharge_kwh = discharge.value_hours / 1000.0
    soc_values = [value for _, value in soc_points]
    temperature_values = [value for _, value in temperature_c_points]
    min_soc = min(soc_values, default=None)
    max_soc = max(soc_values, default=None)
    first_99 = next((at for at, value in sorted(soc_points) if value >= 99), None)
    above_90 = duration_above(soc_points, 90.0, max_gap) / 3600.0
    above_95 = duration_above(soc_points, 95.0, max_gap) / 3600.0
    below_50 = duration_above(
        [(at, -value) for at, value in soc_points], -50.0, max_gap
    ) / 3600.0
    below_25 = duration_above(
        [(at, -value) for at, value in soc_points], -25.0, max_gap
    ) / 3600.0
    return BatteryAggregate(
        min_soc_pct=min_soc,
        max_soc_pct=max_soc,
        mean_soc_pct=time_weighted_mean(soc_integration),
        sunrise_soc_pct=_value_at(soc_points, sunrise) if sunrise else None,
        sunset_soc_pct=_value_at(soc_points, sunset) if sunset else None,
        overnight_soc_drop_pct=None,
        depth_of_discharge_pct=(max_soc - min_soc)
        if min_soc is not None and max_soc is not None
        else None,
        hours_above_90=above_90,
        hours_above_95=above_95,
        hours_below_50=below_50,
        hours_below_25=below_25,
        charge_kwh=charge_kwh,
        discharge_kwh=discharge_kwh,
        net_kwh=charge_kwh - discharge_kwh,
        daily_efc=equivalent_full_cycles(
            charge_kwh, discharge_kwh, nominal_usable_kwh
        ),
        min_temperature_c=min(temperature_values, default=None),
        max_temperature_c=max(temperature_values, default=None),
        mean_temperature_c=time_weighted_mean(temperature),
        reached_95=any(value >= 95 for value in soc_values),
        reached_99=any(value >= 99 for value in soc_values),
        reached_100=any(value >= 100 for value in soc_values),
        first_reached_99_at=first_99,
        coverage=coverage,
        quality=_quality(coverage),
    )
