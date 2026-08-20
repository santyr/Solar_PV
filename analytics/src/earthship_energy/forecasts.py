"""Forecast snapshot contracts that prevent retrospective future leakage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


@dataclass(frozen=True)
class ForecastSnapshot:
    source: str
    issued_at: datetime
    valid_for: datetime
    metric: str
    value: float | None
    unit: str | None
    payload: dict[str, object]

    def __post_init__(self):
        if not _aware(self.issued_at) or not _aware(self.valid_for):
            raise ValueError("forecast timestamps must be timezone-aware")
        if self.valid_for < self.issued_at:
            raise ValueError("valid_for cannot precede issued_at")
        if not self.source or not self.metric:
            raise ValueError("forecast source and metric are required")
        if not isinstance(self.payload, dict):
            raise ValueError("forecast payload must be an object")


def select_forecast_as_of(
    snapshots: Iterable[ForecastSnapshot],
    *,
    source: str,
    metric: str,
    valid_for: datetime,
    origin: datetime,
) -> ForecastSnapshot | None:
    if not _aware(valid_for) or not _aware(origin):
        raise ValueError("selection timestamps must be timezone-aware")
    candidates = [
        snapshot
        for snapshot in snapshots
        if snapshot.source == source
        and snapshot.metric == metric
        and snapshot.valid_for == valid_for
        and snapshot.issued_at <= origin
    ]
    return max(candidates, key=lambda snapshot: snapshot.issued_at, default=None)
