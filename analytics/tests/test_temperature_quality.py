from datetime import date
from types import SimpleNamespace

import pytest

from earthship_energy import daily, temperature_quality
from earthship_energy.config import load_source_config
from earthship_energy.series import local_day_bounds
from weather_temperature_evidence import TemperaturePolicy
import weather_temperature_config
import weather_temperature_history
import hourly_temperature_runtime


def test_north_wall_quality_uses_closed_receipt_window_not_numeric_rows(monkeypatch):
    start, end = local_day_bounds(date(2026, 9, 23), "America/Denver")
    policy = TemperaturePolicy("AmbientWeather-WH31E", 193, -80, 160, 120)
    monkeypatch.setattr(weather_temperature_config, "load_temperature_policies",
                        lambda _path: {"north_wall": policy})
    monkeypatch.setattr(hourly_temperature_runtime, "read_db_config", lambda _path: {})
    calls = []

    def read(factory, **kwargs):
        calls.append(kwargs)
        assert kwargs["stream"] == "north_wall"
        assert kwargs["include_provenance"] is True
        return dict(covered_seconds=85954.173886, total_seconds=86400,
                    maximum_gap_seconds=373.823224, gap_count=3,
                    history_sha256="a" * 64)

    monkeypatch.setattr(weather_temperature_history, "fetch_temperature_window", read)
    result = temperature_quality.read_north_wall_quality(
        "/unused/database", "/unused/policy", start=start, end=end,
        assessed_at=end, row_count=1, first_at=start, last_at=start,
    )
    assert len(calls) == 1
    assert result["quality"] == "ok"
    assert result["coverage"] == pytest.approx(85954.173886 / 86400)
    assert result["stale_intervals"] == 3
    assert result["row_count"] == 1  # A held numeric row cannot create coverage.
    assert result["detail"]["maximum_gap_seconds"] == 373.823224
    assert result["detail"]["history_sha256"] == "a" * 64


def test_north_wall_wrong_identity_or_unavailable_history_fails_closed(monkeypatch):
    start, end = local_day_bounds(date(2026, 9, 23), "America/Denver")
    monkeypatch.setattr(weather_temperature_config, "load_temperature_policies",
                        lambda _path: {"north_wall": TemperaturePolicy(
                            "AmbientWeather-WH31E", 194, -80, 160, 120)})
    monkeypatch.setattr(hourly_temperature_runtime, "read_db_config", lambda _path: {})
    arguments = dict(db_config_path="/unused/database", policy_path="/unused",
                     start=start, end=end, assessed_at=end, row_count=0,
                     first_at=None, last_at=None)
    with pytest.raises(ValueError, match="identity mismatch"):
        temperature_quality.read_north_wall_quality(**arguments)
    monkeypatch.setattr(weather_temperature_config, "load_temperature_policies",
                        lambda _path: {"north_wall": TemperaturePolicy(
                            "AmbientWeather-WH31E", 193, -80, 160, 120)})
    monkeypatch.setattr(weather_temperature_history, "fetch_temperature_window",
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            RuntimeError("history unavailable")))
    with pytest.raises(RuntimeError, match="history unavailable"):
        temperature_quality.read_north_wall_quality(**arguments)


def test_daily_north_wall_opt_in_requires_complete_elapsed_evidence(monkeypatch):
    config = load_source_config()
    tables = {name: f"item{i:04d}" for i, name in enumerate(sorted(daily.REQUIRED_DAILY), 1)}
    tables[temperature_quality.NORTH_WALL_SOURCE] = "item0099"
    resolved = [SimpleNamespace(canonical_name=name, table_name=table)
                for name, table in tables.items()]
    day = date(2026, 9, 23)
    start, end = local_day_bounds(day, config.timezone)
    db_config = object()
    options = dict(temperature_evidence_db_config=db_config,
                   temperature_evidence_policy="/unused/policy",
                   temperature_evidence_assessed_at=end)
    with pytest.raises(ValueError, match="complete temperature evidence"):
        daily.build_daily_snapshot(object(), config, resolved, day,
                                   temperature_evidence_db_config=db_config)
    with pytest.raises(ValueError, match="elapsed local day"):
        daily.build_daily_snapshot(object(), config, resolved, day,
                                   **{**options, "temperature_evidence_assessed_at": start})

    calls = []
    monkeypatch.setattr(daily, "read_north_wall_quality", lambda *args, **kwargs: (
        calls.append((args, kwargs)) or dict(canonical_name=temperature_quality.NORTH_WALL_SOURCE,
        coverage=0.9, quality="ok", stale_intervals=1)))
    monkeypatch.setattr(daily, "fetch_numeric_series", lambda *_args: [])
    monkeypatch.setattr(daily, "fetch_text_series", lambda *_args: [])
    monkeypatch.setattr(daily, "fetch_observation_stats", lambda *_args: (0, None, None))
    monkeypatch.setattr(daily, "fetch_snow_state_as_of", lambda *_args: None)
    # The legacy SoC branch lets this test isolate the optional temperature path.
    from dataclasses import replace
    config = replace(config, sources=tuple(
        replace(source, stale_policy="status_must_equal_OK", freshness_item="BMS_Comms_Status")
        if source.canonical_name == "battery.soc_pct" else source for source in config.sources))
    result = daily.build_daily_snapshot(object(), config, resolved, day, **options)
    assert len(calls) == 1
    assert calls[0][1]["row_count"] == 0
    assert next(row for row in result["source_quality"]
                if row["canonical_name"] == temperature_quality.NORTH_WALL_SOURCE)["coverage"] == 0.9
