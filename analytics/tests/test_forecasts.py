from datetime import datetime, timezone

import pytest

from earthship_energy.forecasts import ForecastSnapshot, select_forecast_as_of


UTC = timezone.utc
VALID = datetime(2026, 1, 2, 12, tzinfo=UTC)


def snapshot(issued_hour, value):
    return ForecastSnapshot(
        source="open_meteo",
        issued_at=datetime(2026, 1, 1, issued_hour, tzinfo=UTC),
        valid_for=VALID,
        metric="temperature_c",
        value=value,
        unit="degC",
        payload={},
    )


def test_selects_latest_forecast_known_at_origin_without_future_leakage():
    snapshots = [snapshot(0, 1.0), snapshot(6, 2.0), snapshot(12, 3.0)]
    chosen = select_forecast_as_of(
        snapshots,
        source="open_meteo",
        metric="temperature_c",
        valid_for=VALID,
        origin=datetime(2026, 1, 1, 8, tzinfo=UTC),
    )
    assert chosen.value == 2.0


def test_no_forecast_is_explicit_when_none_was_known_at_origin():
    chosen = select_forecast_as_of(
        [snapshot(6, 2.0)],
        source="open_meteo",
        metric="temperature_c",
        valid_for=VALID,
        origin=datetime(2026, 1, 1, 5, tzinfo=UTC),
    )
    assert chosen is None


def test_forecast_requires_aware_ordered_timestamps():
    with pytest.raises(ValueError):
        ForecastSnapshot(
            source="x",
            issued_at=datetime(2026, 1, 2, tzinfo=UTC),
            valid_for=datetime(2026, 1, 1, tzinfo=UTC),
            metric="x",
            value=1,
            unit=None,
            payload={},
        )
