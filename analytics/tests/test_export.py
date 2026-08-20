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
        "pv_power_w": 1000.0,
        "load_power_w": 500.0,
        "forecast_issued_at": issued or at - timedelta(hours=1),
        "forecast_valid_for": at,
        "shade_confidence": 0.0,
        "kiva_confidence": 0.0,
    }


def test_feature_csv_is_deterministic_and_has_versioned_columns():
    first = export_feature_csv([row()])
    second = export_feature_csv([row()])
    assert first == second
    text = first.decode()
    assert text.startswith("schema_version,at,epoch_id,")
    assert "discover_4_module_2026" in text


def test_export_rejects_future_forecast_and_wrong_cadence():
    with pytest.raises(FeatureExportError, match="future forecast"):
        export_feature_csv([row(issued=AT + timedelta(minutes=1))])
    with pytest.raises(FeatureExportError, match="cadence"):
        export_feature_csv([row(at=AT + timedelta(minutes=7))], cadence_minutes=15)
