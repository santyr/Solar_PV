from datetime import datetime, timedelta, timezone

import pytest

from earthship_energy.events import (
    ObservationalEvent,
    SnowEvent,
    persist_observational_event,
    persist_snow_event,
)


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


class Cursor:
    def __init__(self, returned=(17,)):
        self.returned = returned
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.returned


class Connection:
    def __init__(self, returned=(17,)):
        self.cursor_instance = Cursor(returned)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_persists_snow_event_idempotently_with_evidence():
    connection = Connection()
    event = SnowEvent(
        START, "snow_cleared", "operator", 1.0,
        note="array cleared", evidence={"photo": "receipt-7"},
    )
    result = persist_snow_event(connection, event)
    assert result == {"status": "inserted", "event_id": 17}
    sql, params = connection.cursor_instance.executed[0]
    assert "INSERT INTO energy_analytics.snow_events" in sql
    assert "ON CONFLICT" in sql
    assert params[:4] == (START, "snow_cleared", "operator", 1.0)
    assert connection.commits == 1


def test_duplicate_observational_event_is_successful_noop():
    connection = Connection(returned=None)
    event = ObservationalEvent(
        "kiva_use", "likely", START, START + timedelta(minutes=10),
        "thermal_residual", "v1", 0.8, evidence={"window": "bounded"},
    )
    result = persist_observational_event(connection, event)
    assert result == {"status": "duplicate", "event_id": None}
    sql, _ = connection.cursor_instance.executed[0]
    assert "INSERT INTO energy_analytics.system_events" in sql
    assert "ON CONFLICT" in sql
    assert connection.commits == 1
