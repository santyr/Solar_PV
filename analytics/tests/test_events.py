from datetime import datetime, timedelta, timezone

import pytest

from earthship_energy.events import ObservationalEvent, SnowEvent


START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_inferred_shade_and_kiva_events_have_no_control_authority():
    for kind in ("indoor_shade", "kiva_use"):
        event = ObservationalEvent(
            event_kind=kind,
            state="likely",
            started_at=START,
            ended_at=START + timedelta(minutes=10),
            method="sensor_fusion",
            method_version="v1",
            confidence=0.8,
            operator_confirmed=False,
            evidence={"source": "test"},
        )
        assert event.authority == "observational_only"


def test_event_validation_rejects_bad_confidence_and_time_order():
    with pytest.raises(ValueError, match="confidence"):
        ObservationalEvent("kiva_use", "likely", START, None, "x", "v1", 1.1)
    with pytest.raises(ValueError, match="ended_at"):
        ObservationalEvent(
            "kiva_use", "likely", START, START - timedelta(seconds=1), "x", "v1", 0.5
        )


def test_snow_event_states_are_closed_set():
    assert SnowEvent(START, "snow_covered", "operator", 1.0).state == "snow_covered"
    with pytest.raises(ValueError, match="snow state"):
        SnowEvent(START, "maybe", "operator", 1.0)
