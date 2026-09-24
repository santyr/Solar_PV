from copy import deepcopy
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


def detail_v2():
    return {
        "version": 2,
        "generatedAt": "2026-09-05T06:40:29-06:00",
        "timezone": "America/Denver",
        "temperatureAdjustment": {
            "highCorrectionF": 3.4,
            "lowCorrectionF": -8.2,
            "hourlyMethod": "hourly-blend",
            "hourBuckets": [
                {"hour": hour, "count": 5, "weight": 0.5} for hour in range(24)
            ],
        },
        "days": [{
            "date": "2026-09-06",
            "summary": {"pvKwh": 6.9},
            "hours": [{"at": "2026-09-06T11:00:00-06:00", "tempF": 88.2}],
        }],
    }


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
    assert by_metric["daily_pv_kwh"].valid_for.isoformat() == "2026-08-22T00:00:00-06:00"
    assert by_metric["daily_pv_kwh"].payload == {"forecast_version": 1, "forecast_day": "2026-08-21"}


def test_v2_preserves_corrected_values_and_provenance():
    payload = detail_v2()
    rows = snapshots_from_openhab_detail(payload)
    row = next(row for row in rows if row.metric == "temperature_f")
    assert row.value == 88.2
    assert row.issued_at.isoformat() == payload["generatedAt"]
    assert row.payload == {
        "forecast_version": 2,
        "temperatureAdjustment": payload["temperatureAdjustment"],
    }


def test_v2_provenance_is_independent_of_mutated_input():
    payload = detail_v2()
    expected = deepcopy(payload["temperatureAdjustment"])
    rows = snapshots_from_openhab_detail(payload)
    payload["temperatureAdjustment"]["hourBuckets"][0]["weight"] = 0.9
    assert rows[0].payload["temperatureAdjustment"] == expected


@pytest.mark.parametrize("version", [True, False, 1.0, 2.0, 3, "2"])
def test_openhab_detail_rejects_unsupported_or_noninteger_versions(version):
    payload = detail_v2()
    payload["version"] = version
    with pytest.raises(ValueError, match="version must be 1 or 2"):
        snapshots_from_openhab_detail(payload)


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda p: p.pop("temperatureAdjustment"), "required"),
        (lambda p: p.__setitem__("temperatureAdjustment", []), "required"),
        (lambda p: p["temperatureAdjustment"].pop("highCorrectionF"), "corrections"),
        (lambda p: p["temperatureAdjustment"].pop("lowCorrectionF"), "corrections"),
        (lambda p: p["temperatureAdjustment"].__setitem__("highCorrectionF", True), "finite numeric"),
        (lambda p: p["temperatureAdjustment"].__setitem__("lowCorrectionF", float("inf")), "finite numeric"),
        (lambda p: p["temperatureAdjustment"].__setitem__("hourlyMethod", "other"), "method"),
        (lambda p: p["temperatureAdjustment"].__setitem__("hourBuckets", []), "24 buckets"),
        (lambda p: p["temperatureAdjustment"]["hourBuckets"].reverse(), "ordered"),
        (lambda p: p["temperatureAdjustment"]["hourBuckets"][0].pop("hour"), "ordered"),
        (lambda p: p["temperatureAdjustment"]["hourBuckets"][0].__setitem__("count", -1), "count/weight"),
        (lambda p: p["temperatureAdjustment"]["hourBuckets"][0].__setitem__("count", True), "count/weight"),
        (lambda p: p["temperatureAdjustment"]["hourBuckets"][0].__setitem__("weight", -0.1), "count/weight"),
        (lambda p: p["temperatureAdjustment"]["hourBuckets"][0].__setitem__("weight", 1.1), "count/weight"),
        (lambda p: p["temperatureAdjustment"]["hourBuckets"][0].__setitem__("weight", True), "finite numeric"),
    ],
)
def test_v2_rejects_malformed_temperature_adjustment(mutate, message):
    payload = detail_v2()
    mutate(payload)
    with pytest.raises(ValueError, match=message):
        snapshots_from_openhab_detail(payload)


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("value", [True, "88.2", float("nan"), float("inf")])
@pytest.mark.parametrize("location, field", [("summary", "pvKwh"), ("hours", "tempF")])
def test_openhab_detail_rejects_invalid_recognized_metrics(version, value, location, field):
    payload = detail_v2()
    payload["version"] = version
    if version == 1:
        payload.pop("temperatureAdjustment")
    if location == "summary":
        payload["days"][0]["summary"][field] = value
    else:
        payload["days"][0]["hours"][0][field] = value
    with pytest.raises(ValueError, match="finite numeric or null"):
        snapshots_from_openhab_detail(payload)


@pytest.mark.parametrize("version", [1, 2])
def test_openhab_detail_preserves_null_metrics(version):
    payload = detail_v2()
    payload["version"] = version
    if version == 1:
        payload.pop("temperatureAdjustment")
    payload["days"][0]["summary"]["pvKwh"] = None
    payload["days"][0]["hours"][0]["tempF"] = None
    rows = snapshots_from_openhab_detail(payload)
    assert {row.value for row in rows} == {None}


@pytest.mark.parametrize("version", [1, 2])
def test_openhab_detail_validates_past_metrics_before_omitting(version):
    payload = detail_v2()
    payload["version"] = version
    if version == 1:
        payload.pop("temperatureAdjustment")
    payload["generatedAt"] = "2026-09-06T12:00:00-06:00"
    payload["days"][0]["summary"]["pvKwh"] = True
    payload["days"][0]["hours"][0]["tempF"] = "invalid"
    with pytest.raises(ValueError, match="finite numeric or null"):
        snapshots_from_openhab_detail(payload)


@pytest.mark.parametrize("version", [1, 2])
def test_same_day_summary_remains_valid_until_next_midnight_for_both_versions(version):
    payload = detail_v2()
    payload["version"] = version
    if version == 1:
        payload.pop("temperatureAdjustment")
    payload["generatedAt"] = "2026-09-06T06:40:29-06:00"
    rows = snapshots_from_openhab_detail(payload)
    assert [row.metric for row in rows] == ["daily_pv_kwh", "temperature_f"]
    assert rows[0].valid_for.isoformat() == "2026-09-07T00:00:00-06:00"


@pytest.mark.parametrize("version", [1, 2])
def test_next_day_midnight_uses_dst_aware_site_offset(version):
    payload = detail_v2()
    payload["version"] = version
    if version == 1:
        payload.pop("temperatureAdjustment")
    payload["generatedAt"] = "2026-10-31T06:40:29-06:00"
    payload["days"][0]["date"] = "2026-11-01"
    payload["days"][0]["hours"][0]["at"] = "2026-11-01T11:00:00-07:00"
    rows = snapshots_from_openhab_detail(payload)
    by_metric = {row.metric: row for row in rows}
    assert by_metric["daily_pv_kwh"].valid_for.isoformat() == "2026-11-02T00:00:00-07:00"
    assert by_metric["temperature_f"].valid_for.isoformat() == "2026-11-01T11:00:00-07:00"


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
        ("daily_high_f", 0),
        ("temperature_f", 11)
    ]


def test_repeated_v2_capture_preserves_persistence_identity():
    payload = detail_v2()

    first = snapshots_from_openhab_detail(payload)
    second = snapshots_from_openhab_detail(payload)

    identity = lambda row: (row.source, row.issued_at, row.valid_for, row.metric)
    assert [identity(row) for row in first] == [identity(row) for row in second]


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
