"""Strict loading for the versioned metric-source contract."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigError(ValueError):
    pass


TOP_LEVEL_FIELDS = {
    "version",
    "timezone",
    "sources",
    "planned_sources",
    "denied_name_patterns",
}
SOURCE_REQUIRED_FIELDS = {
    "canonical_name",
    "item_name",
    "device",
    "protocol",
    "raw_unit",
    "canonical_unit",
    "scale",
    "sign",
    "stale_policy",
    "kind",
    "confidence",
    "required",
}
SOURCE_OPTIONAL_FIELDS = {
    "conversion",
    "freshness_item",
    "role",
    "stale_after_seconds",
}


@dataclass(frozen=True)
class MetricSource:
    canonical_name: str
    item_name: str
    device: str
    protocol: str
    raw_unit: str
    canonical_unit: str
    scale: float
    sign: str
    stale_policy: str
    kind: str
    confidence: float
    required: bool
    conversion: str | None = None
    freshness_item: str | None = None
    role: str | None = None
    stale_after_seconds: int | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MetricSource":
        fields = set(payload)
        missing = SOURCE_REQUIRED_FIELDS - fields
        unknown = fields - SOURCE_REQUIRED_FIELDS - SOURCE_OPTIONAL_FIELDS
        if missing:
            raise ConfigError(f"source missing required fields: {sorted(missing)}")
        if unknown:
            raise ConfigError(f"source has unknown fields: {sorted(unknown)}")
        try:
            source = cls(**payload)
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"invalid source: {exc}") from exc
        if not source.canonical_name or not source.item_name:
            raise ConfigError("source names must be non-empty")
        if not isinstance(source.required, bool):
            raise ConfigError("source required must be boolean")
        if not (0.0 <= float(source.confidence) <= 1.0):
            raise ConfigError("source confidence must be between 0 and 1")
        if source.stale_after_seconds is not None and source.stale_after_seconds <= 0:
            raise ConfigError("stale_after_seconds must be positive")
        return source


@dataclass(frozen=True)
class SourceConfig:
    version: int
    timezone: str
    sources: tuple[MetricSource, ...]
    planned_sources: tuple[dict[str, Any], ...] = ()
    denied_name_patterns: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SourceConfig":
        unknown = set(payload) - TOP_LEVEL_FIELDS
        if unknown:
            raise ConfigError(f"unknown top-level fields: {sorted(unknown)}")
        if payload.get("version") != 1:
            raise ConfigError("source config version must be 1")
        timezone_name = payload.get("timezone")
        if not isinstance(timezone_name, str):
            raise ConfigError("timezone must be a string")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ConfigError(f"unknown timezone: {timezone_name}") from exc
        raw_sources = payload.get("sources")
        if not isinstance(raw_sources, list) or not raw_sources:
            raise ConfigError("sources must be a non-empty list")
        sources = tuple(MetricSource.from_payload(item) for item in raw_sources)
        canonical_names = [source.canonical_name for source in sources]
        if len(canonical_names) != len(set(canonical_names)):
            raise ConfigError("duplicate canonical_name")
        item_names = [source.item_name for source in sources]
        if len(item_names) != len(set(item_names)):
            raise ConfigError("duplicate item_name")
        denied = payload.get("denied_name_patterns", [])
        if not isinstance(denied, list) or not all(isinstance(x, str) for x in denied):
            raise ConfigError("denied_name_patterns must be strings")
        try:
            for pattern in denied:
                re.compile(pattern)
        except re.error as exc:
            raise ConfigError(f"invalid denied_name_pattern: {exc}") from exc
        planned = payload.get("planned_sources", [])
        if not isinstance(planned, list) or not all(isinstance(x, dict) for x in planned):
            raise ConfigError("planned_sources must be objects")
        return cls(
            version=1,
            timezone=timezone_name,
            sources=sources,
            planned_sources=tuple(planned),
            denied_name_patterns=tuple(denied),
        )


def default_source_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "metric-sources.json"


def load_source_config(path: str | Path | None = None) -> SourceConfig:
    config_path = Path(path) if path is not None else default_source_config_path()
    try:
        payload = json.loads(config_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot load source config: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError("source config must be a JSON object")
    return SourceConfig.from_payload(payload)
