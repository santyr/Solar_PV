from datetime import datetime, timedelta, timezone

import pytest

from earthship_energy.aggregation import (
    SignCalibrationError,
    aggregate_battery,
    aggregate_power,
    aggregate_weather,
    calibrate_battery_power_sign,
)


UTC = timezone.utc
START = datetime(2026, 1, 1, tzinfo=UTC)


def points(*values):
    return [(START + timedelta(hours=i), float(value)) for i, value in enumerate(values)]


def test_calibrates_positive_battery_power_as_charging():
    result = calibrate_battery_power_sign(
        [(500.0, 1.0), (1000.0, 2.0), (-400.0, -1.0), (-800.0, -2.0)]
    )
    assert result.sign == "positive_charging"
    assert result.concordant == 4
    assert result.confidence == pytest.approx(1.0)


def test_sign_calibration_fails_when_evidence_is_weak_or_conflicted():
    with pytest.raises(SignCalibrationError):
        calibrate_battery_power_sign([(500.0, 1.0), (500.0, -1.0)])
    with pytest.raises(SignCalibrationError):
        calibrate_battery_power_sign([(0.0, 0.0)])


def test_daily_battery_aggregation_integrates_charge_discharge_and_efc():
    result = aggregate_battery(
        soc_points=points(80, 90, 100),
        power_points=points(-1000, 1000, 1000),
        temperature_c_points=points(20, 22, 24),
        window_start=START,
        window_end=START + timedelta(hours=2),
        max_gap=timedelta(hours=1),
        nominal_usable_kwh=20.0,
        power_sign="positive_charging",
        sunrise=START + timedelta(minutes=30),
        sunset=START + timedelta(hours=1, minutes=30),
    )
    assert result.min_soc_pct == 80
    assert result.max_soc_pct == 100
    assert result.mean_soc_pct == pytest.approx(90)
    assert result.sunrise_soc_pct == pytest.approx(85)
    assert result.sunset_soc_pct == pytest.approx(95)
    assert result.depth_of_discharge_pct == 20
    assert result.charge_kwh == pytest.approx(1.5)
    assert result.discharge_kwh == pytest.approx(0.5)
    assert result.net_kwh == pytest.approx(1.0)
    assert result.daily_efc == pytest.approx(0.05)
    assert result.reached_95 is True
    assert result.reached_99 is True
    assert result.reached_100 is True
    assert result.first_reached_99_at == START + timedelta(hours=2)
    assert result.coverage == pytest.approx(1.0)
    assert result.quality == "ok"


def test_battery_aggregation_refuses_unknown_power_sign():
    with pytest.raises(SignCalibrationError):
        aggregate_battery(
            soc_points=points(80, 81),
            power_points=points(10, 10),
            temperature_c_points=points(20, 20),
            window_start=START,
            window_end=START + timedelta(hours=1),
            max_gap=timedelta(hours=1),
            nominal_usable_kwh=20,
            power_sign="calibration_required",
        )


def test_power_aggregation_reports_energy_peak_and_gap_quality():
    result = aggregate_power(
        points(0, 1000, 2000),
        START,
        START + timedelta(hours=2),
        max_gap=timedelta(hours=1),
    )
    assert result.energy_kwh == pytest.approx(2.0)
    assert result.peak_w == 2000
    assert result.productive_hours == pytest.approx(1.99)
    assert result.first_productive_at == START + timedelta(hours=1)
    assert result.last_productive_at == START + timedelta(hours=2)
    assert result.coverage == 1.0
    assert result.quality == "ok"


def test_weather_aggregation_uses_canonical_units():
    result = aggregate_weather(
        temperature_c_points=points(0, 10, 20),
        irradiance_points=points(0, 500, 0),
        precipitation_mm_points=points(0, 2, 4),
        window_start=START,
        window_end=START + timedelta(hours=2),
        max_gap=timedelta(hours=1),
    )
    assert result.min_temperature_c == 0
    assert result.max_temperature_c == 20
    assert result.mean_temperature_c == pytest.approx(10)
    assert result.irradiance_wh_m2 == pytest.approx(500)
    assert result.peak_irradiance_w_m2 == 500
    assert result.precipitation_mm == 4
    assert result.coverage == 1.0
