from copy import deepcopy
from datetime import date, datetime, timedelta, timezone

import pytest

from earthship_energy.ui_payload import (
    MAX_PAYLOAD_BYTES,
    build_energy_ui_payload,
    encode_energy_ui_payload,
    validate_energy_ui_payload,
)


UTC = timezone.utc
GENERATED = datetime(2026, 8, 20, 18, 0, tzinfo=UTC)
DAILY = [
    {
        "local_date": date(2026, 8, 18),
        "min_soc_pct": 61.0,
        "reached_99": False,
        "charge_kwh": 3.0,
        "discharge_kwh": 4.0,
        "daily_efc": 0.17,
        "cumulative_efc": 4.2,
        "hours_above_90": 2.0,
        "hours_above_95": 0.5,
        "pv_kwh": 5.0,
        "load_kwh": 6.0,
        "quality": "ok",
    },
    {
        "local_date": date(2026, 8, 19),
        "min_soc_pct": 67.0,
        "reached_99": True,
        "charge_kwh": 4.0,
        "discharge_kwh": 3.0,
        "daily_efc": 0.16,
        "cumulative_efc": 4.36,
        "hours_above_90": 4.0,
        "hours_above_95": 1.0,
        "pv_kwh": 8.0,
        "load_kwh": 5.0,
        "quality": "ok",
    },
]


def payload():
    return build_energy_ui_payload(
        generated_at=GENERATED,
        timezone_name="America/Denver",
        epoch_id="discover_4_module_2026",
        daily_rows=DAILY,
        winter={
            "winter_observation_days": 0,
            "conclusion": "insufficient_winter_observations",
            "observed": None,
        },
        lifecycle={
            "charge_kwh": 7.0,
            "discharge_kwh": 7.0,
            "cumulative_efc": 0.33,
            "ending_cumulative_efc": 4.36,
            "high_soc_exposure_hours": {"above_90": 6.0, "above_95": 1.5},
        },
        module_health={
            "status": "unavailable",
            "reason": "no_module_samples",
            "modules": {},
            "provenance": [],
        },
        forecast={
            "status": "current",
            "issuedAt": "2026-08-20T17:00:00+00:00",
            "validFor": "2026-08-21T06:00:00-06:00",
            "pv24hKwh": 7.2,
            "reason": None,
        },
        health={
            "analytics": "ok",
            "forecast": "ok",
            "bms": "ok",
            "schneider": "ok",
            "weather": "ok",
            "collector": "ok",
            "reasons": [],
        },
    )


def test_payload_is_deterministic_versioned_and_explicit():
    first = payload()
    second = payload()

    assert first == second
    assert first["schema"] == "earthship-energy-ui/v1"
    assert set(first) == {
        "schema", "generatedAt", "timezone", "epochId", "throughDate",
        "status", "battery", "energy", "winter", "lifecycle", "forecast",
        "health",
    }
    assert first["throughDate"] == "2026-08-19"
    assert first["battery"] == {
        "status": "ok",
        "latestMinSocPct": 67.0,
        "latestReached99": True,
        "endingCumulativeEfc": 4.36,
        "currentNoFullDays": 0,
        "daysSinceFull": 0,
    }
    assert first["energy"]["latest"] == {
        "date": "2026-08-19",
        "pvKwh": 8.0,
        "loadKwh": 5.0,
        "chargeKwh": 4.0,
        "dischargeKwh": 3.0,
    }
    assert first["energy"]["activeLoads"] == {
        "status": "unavailable",
        "measurement": "state_only",
        "reason": "no_power_meter_contract",
    }
    assert first["energy"]["observedCurtailmentKwh"] is None
    assert first["winter"]["status"] == "unavailable"
    assert first["forecast"]["nextMorningSocPct"] is None
    assert first["forecast"]["fullToday"] is None
    assert first["forecast"]["fullTomorrow"] is None
    assert first["lifecycle"]["stateOfHealthPct"] is None
    assert first["status"] == "degraded"
    assert len(encode_energy_ui_payload(first)) < MAX_PAYLOAD_BYTES


def test_payload_reports_no_quality_approved_rows_without_fake_zeroes():
    result = build_energy_ui_payload(
        generated_at=GENERATED,
        timezone_name="America/Denver",
        epoch_id="discover_4_module_2026",
        daily_rows=[],
        winter=None,
        lifecycle=None,
        module_health=None,
        forecast=None,
        health=None,
    )

    assert result["throughDate"] is None
    assert result["battery"]["latestMinSocPct"] is None
    assert result["energy"]["latest"] is None
    assert result["health"]["analytics"] == "unavailable"
    assert result["status"] == "unavailable"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.update(extra=True), "unknown fields"),
        (lambda value: value.__setitem__("schema", "earthship-energy-ui/v2"), "schema"),
        (lambda value: value.__setitem__("generatedAt", "2026-08-20T18:00:00"), "aware"),
        (lambda value: value["battery"].__setitem__("latestMinSocPct", True), "finite number"),
        (lambda value: value["energy"]["latest"].__setitem__("pvKwh", float("nan")), "finite number"),
        (lambda value: value["health"].__setitem__("analytics", "healthy"), "status"),
    ],
)
def test_validator_rejects_shape_type_and_vocabulary_drift(mutate, message):
    candidate = deepcopy(payload())
    mutate(candidate)

    with pytest.raises(ValueError, match=message):
        validate_energy_ui_payload(candidate, now=GENERATED + timedelta(minutes=1))


def test_validator_rejects_future_generation_and_oversized_encoding():
    with pytest.raises(ValueError, match="future"):
        validate_energy_ui_payload(payload(), now=GENERATED - timedelta(seconds=1))

    oversized = deepcopy(payload())
    oversized["lifecycle"]["moduleHealth"]["reason"] = "x" * MAX_PAYLOAD_BYTES
    with pytest.raises(ValueError, match="below 16 KiB"):
        encode_energy_ui_payload(oversized)
