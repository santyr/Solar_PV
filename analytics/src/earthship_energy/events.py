"""Confidence-bearing observational energy and household events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


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
