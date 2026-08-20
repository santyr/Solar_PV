from datetime import datetime, timezone

import pytest
from psycopg2.extras import Json

from earthship_energy.forecasts import (
    ForecastSnapshot,
    persist_forecast_snapshots,
    select_forecast_as_of,
    snapshots_from_openhab_detail,
)


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


def test_openhab_detail_preserves_issue_and_valid_times():
    payload = {
        "version": 1,
        "generatedAt": "2026-08-20T10:01:49-06:00",
        "timezone": "America/Denver",
        "days": [{
            "date": "2026-08-21",
            "summary": {"highF": 93.5, "pvKwh": 6.9},
            "hours": [{
                "at": "2026-08-21T11:00:00-06:00",
                "tempF": 88.2,
                "radiationWm2": 742.0,
            }],
        }],
    }

    snapshots = snapshots_from_openhab_detail(payload)

    by_metric = {snapshot.metric: snapshot for snapshot in snapshots}
    assert by_metric["temperature_f"].issued_at.isoformat() == payload["generatedAt"]
    assert by_metric["temperature_f"].valid_for.isoformat() == payload["days"][0]["hours"][0]["at"]
    assert by_metric["daily_pv_kwh"].valid_for.isoformat() == "2026-08-21T00:00:00-06:00"
    assert by_metric["daily_pv_kwh"].payload == {"forecast_version": 1}


def test_openhab_detail_rejects_naive_or_malformed_contract():
    with pytest.raises(ValueError, match="generatedAt"):
        snapshots_from_openhab_detail({
            "version": 1,
            "generatedAt": "2026-08-20T10:00:00",
            "timezone": "America/Denver",
            "days": [],
        })


def test_openhab_detail_omits_periods_already_started_before_issue():
    payload = {
        "version": 1,
        "generatedAt": "2026-08-20T10:01:49-06:00",
        "timezone": "America/Denver",
        "days": [{
            "date": "2026-08-20",
            "summary": {"highF": 93.5},
            "hours": [
                {"at": "2026-08-20T10:00:00-06:00", "tempF": 85.0},
                {"at": "2026-08-20T11:00:00-06:00", "tempF": 88.0},
            ],
        }],
    }

    snapshots = snapshots_from_openhab_detail(payload)

    assert [(row.metric, row.valid_for.hour) for row in snapshots] == [
        ("temperature_f", 11)
    ]


def test_forecast_persistence_is_idempotent():
    statements = []

    class Cursor:
        rowcount = 1

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, sql, params):
            statements.append((sql, params))

    class Connection:
        def cursor(self):
            return Cursor()

        def commit(self):
            statements.append(("commit", None))

    count = persist_forecast_snapshots(Connection(), [snapshot(6, 2.0)])

    assert count == 1
    assert "ON CONFLICT (source, issued_at, valid_for, metric) DO NOTHING" in statements[0][0]
    assert isinstance(statements[0][1][6], Json)
    assert statements[-1] == ("commit", None)
