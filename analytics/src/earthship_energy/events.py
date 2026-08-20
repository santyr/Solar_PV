"""Confidence-bearing observational energy and household events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from psycopg2.extras import Json


def _validate_confidence(confidence: float) -> None:
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class ObservationalEvent:
    event_kind: str
    state: str
    started_at: datetime
    ended_at: datetime | None
    method: str
    method_version: str
    confidence: float
    operator_confirmed: bool = False
    evidence: dict[str, object] = field(default_factory=dict)
    authority: str = field(default="observational_only", init=False)

    def __post_init__(self):
        _validate_confidence(self.confidence)
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise ValueError("started_at must be timezone-aware")
        if self.ended_at is not None:
            if self.ended_at.tzinfo is None or self.ended_at.utcoffset() is None:
                raise ValueError("ended_at must be timezone-aware")
            if self.ended_at < self.started_at:
                raise ValueError("ended_at cannot precede started_at")
        if not all((self.event_kind, self.state, self.method, self.method_version)):
            raise ValueError("event kind, state, method, and version are required")
        if not isinstance(self.evidence, dict):
            raise ValueError("event evidence must be an object")


@dataclass(frozen=True)
class SnowEvent:
    occurred_at: datetime
    state: str
    method: str
    confidence: float
    note: str | None = None
    evidence: dict[str, object] = field(default_factory=dict)

    def __post_init__(self):
        if self.state not in {"snow_covered", "snow_cleared"}:
            raise ValueError("invalid snow state")
        _validate_confidence(self.confidence)
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")


def _persist(connection, sql: str, params: tuple[object, ...]) -> dict[str, object]:
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            inserted = cursor.fetchone()
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {
        "status": "inserted" if inserted is not None else "duplicate",
        "event_id": int(inserted[0]) if inserted is not None else None,
    }


def persist_snow_event(connection, event: SnowEvent) -> dict[str, object]:
    return _persist(
        connection,
        """INSERT INTO energy_analytics.snow_events
           (occurred_at, state, method, confidence, note, evidence)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (occurred_at, state, method) DO NOTHING
           RETURNING event_id""",
        (
            event.occurred_at, event.state, event.method, event.confidence,
            event.note, Json(event.evidence),
        ),
    )


def persist_observational_event(
    connection, event: ObservationalEvent
) -> dict[str, object]:
    return _persist(
        connection,
        """INSERT INTO energy_analytics.system_events
           (event_kind, state, started_at, ended_at, method, method_version,
            confidence, operator_confirmed, evidence)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (event_kind, started_at, method, method_version)
           DO NOTHING
           RETURNING event_id""",
        (
            event.event_kind, event.state, event.started_at, event.ended_at,
            event.method, event.method_version, event.confidence,
            event.operator_confirmed, Json(event.evidence),
        ),
    )


def fetch_snow_state_as_of(connection, at: datetime) -> str | None:
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("snow-state boundary must be timezone-aware")
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT state
               FROM energy_analytics.snow_events
               WHERE occurred_at < %s
               ORDER BY occurred_at DESC, event_id DESC
               LIMIT 1""",
            (at,),
        )
        row = cursor.fetchone()
    return str(row[0]) if row is not None else None
