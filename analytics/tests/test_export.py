from datetime import datetime, timedelta, timezone

import pytest

from earthship_energy.export import FeatureExportError, export_feature_csv


UTC = timezone.utc
AT = datetime(2026, 1, 1, 12, tzinfo=UTC)


def row(at=AT, issued=None):
    return {
        "at": at,
        "epoch_id": "discover_4_module_2026",
        "battery_soc_pct": 80.0,
        "battery_soc_pct_lag_1h": 78.0,
        "pv_power_w": 1000.0,
        "pv_power_w_lag_1h": 500.0,
        "load_power_w": 500.0,
        "load_power_w_lag_1h": 450.0,
        "outdoor_temperature_c": 12.0,
        "outdoor_irradiance_w_m2": 700.0,
        "daylight_observed": True,
        "dishwasher_active": False,
        "shurflo_pump_active": True,
        "forecast_temperature_f": 55.0,
        "forecast_radiation_w_m2": 650.0,
        "forecast_daily_pv_kwh": 7.2,
        "forecast_issued_at": issued or at - timedelta(hours=1),
        "forecast_valid_for": at,
        "daily_pv_forecast_issued_at": issued or at - timedelta(hours=1),
        "daily_pv_forecast_valid_for": at.replace(hour=0),
        "forecast_status": "current",
        "shade_confidence": 0.0,
        "kiva_confidence": 0.0,
    }


def test_feature_csv_is_deterministic_and_has_versioned_columns():
    feature = {**row(), "outdoor_temperature_c": 27.600000000000005}
    first = export_feature_csv([feature])
    second = export_feature_csv([feature])
    assert first == second
    text = first.decode()
    assert text.startswith("schema_version,at,epoch_id,")
    assert text.splitlines()[1].startswith("2,")
    assert "discover_4_module_2026" in text
    assert ",27.6," in text


def test_export_rejects_future_forecast_and_wrong_cadence():
    with pytest.raises(FeatureExportError, match="future forecast"):
        export_feature_csv([row(issued=AT + timedelta(minutes=1))])
    with pytest.raises(FeatureExportError, match="cadence"):
        export_feature_csv([row(at=AT + timedelta(minutes=7))], cadence_minutes=15)


def test_export_allows_explicitly_unavailable_forecast_without_fake_timestamps():
    unavailable = {
        **row(),
        "forecast_temperature_f": None,
        "forecast_radiation_w_m2": None,
        "forecast_daily_pv_kwh": None,
        "forecast_issued_at": None,
        "forecast_valid_for": None,
        "daily_pv_forecast_issued_at": None,
        "daily_pv_forecast_valid_for": None,
        "forecast_status": "unavailable",
    }
    text = export_feature_csv([unavailable]).decode()
    assert "unavailable" in text
