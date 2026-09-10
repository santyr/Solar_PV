"""Daily SoC statistics must not interpolate gaps or use legacy numeric values."""
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta, timezone
import json
from types import SimpleNamespace

import pytest

from earthship_energy.aggregation import aggregate_battery
from earthship_energy.bms_evidence import build_soc_intervals
from earthship_energy.series import local_day_bounds
from earthship_energy import daily
from earthship_energy.bms_evidence import EvidenceSequenceError
from earthship_energy.config import load_source_config
from earthship_energy.materialize import load_epoch_config, select_epoch

START = datetime(2026, 9, 10, tzinfo=timezone.utc)


def at(seconds, start=START):
    return start + timedelta(seconds=seconds)


def intervals(samples, start=START, end=None):
    rows = []
    for seconds, soc in samples:
        timestamp = at(seconds, start)
        millis = int(timestamp.timestamp() * 1000)
        rows.append((timestamp, json.dumps({
            "version": 1, "streamEpoch": "864142d5-99ee-4b7a-b5fc-e6a96e7274d8",
            "recordedAt": millis, "status": "valid", "reason": "ok",
            "observedAt": millis, "scaleObservedAt": millis,
            "validUntil": millis + 120000, "soc": soc,
        })))
    return build_soc_intervals(rows, start, end or at(600, start), epoch_start=start)


def aggregate(qualified, *, start=START, end=None, **kwargs):
    end = end or at(600, start)
    return aggregate_battery(
        # Deliberately contradictory legacy data must never influence atomic results.
        soc_points=[(start, 0), (end, 100)],
        power_points=[(start, 1000), (end, 1000)],
        temperature_c_points=[(start, 20), (end, 22)],
        window_start=start, window_end=end, max_gap=end-start,
        nominal_usable_kwh=20.48, power_sign="positive_charging",
        soc_intervals=qualified, **kwargs,
    )


def test_qualified_values_durations_and_events_do_not_bridge_gaps():
    result = aggregate(intervals([(0, 20), (180, 95), (240, 100), (360, 50)]),
                       sunrise=at(120), sunset=at(240))
    assert result.min_soc_pct == 20
    assert result.max_soc_pct == 100
    assert result.depth_of_discharge_pct == 80
    assert result.mean_soc_pct == pytest.approx(26100 / 420)
    assert result.coverage == pytest.approx(420 / 600)
    assert result.quality == "partial"
    assert result.hours_above_90 == pytest.approx(180 / 3600)
    assert result.hours_above_95 == pytest.approx(120 / 3600)
    assert result.hours_below_50 == pytest.approx(120 / 3600)
    assert result.hours_below_25 == pytest.approx(120 / 3600)
    assert result.sunrise_soc_pct is None  # exact expiry, not interpolated
    assert result.sunset_soc_pct == 100  # next segment owns the boundary
    assert result.first_reached_99_at == at(240)
    assert result.reached_95 and result.reached_99 and result.reached_100


def test_empty_qualified_history_is_not_a_legacy_fallback():
    result = aggregate([], sunrise=at(60), sunset=at(300))
    for name in ("min_soc_pct", "max_soc_pct", "mean_soc_pct", "depth_of_discharge_pct",
                 "sunrise_soc_pct", "sunset_soc_pct", "first_reached_99_at"):
        assert getattr(result, name) is None
    assert result.coverage == 0
    assert result.quality == "insufficient_data"
    assert result.hours_above_90 == result.hours_above_95 == 0
    assert result.hours_below_50 == result.hours_below_25 == 0
    assert not (result.reached_95 or result.reached_99 or result.reached_100)


@pytest.mark.parametrize("qualified", [[], intervals([(0, 20), (300, 100)])])
def test_power_temperature_and_energy_throughput_efc_are_unchanged(qualified):
    legacy = asdict(aggregate(None))
    atomic = asdict(aggregate(qualified))
    for field in ("charge_kwh", "discharge_kwh", "net_kwh", "daily_efc",
                  "min_temperature_c", "max_temperature_c", "mean_temperature_c"):
        assert atomic[field] == legacy[field]
    assert atomic["daily_efc"] == pytest.approx((1 / 6) / (2 * 20.48))


@pytest.mark.parametrize("soc", [25, 50, 90, 95, 99, 100])
def test_threshold_durations_are_strict_but_reached_flags_are_inclusive(soc):
    result = aggregate(intervals([(0, soc)]), end=at(120))
    assert result.hours_above_90 == (120 / 3600 if soc > 90 else 0)
    assert result.hours_above_95 == (120 / 3600 if soc > 95 else 0)
    assert result.hours_below_50 == (120 / 3600 if soc < 50 else 0)
    assert result.hours_below_25 == 0
    assert result.reached_95 == (soc >= 95)
    assert result.reached_99 == (soc >= 99)
    assert result.reached_100 == (soc >= 100)


@pytest.mark.parametrize("day,hours", [(date(2026, 3, 8), 23), (date(2026, 11, 1), 25)])
def test_dst_coverage_uses_actual_utc_day_duration(day, hours):
    start, end = local_day_bounds(day, "America/Denver")
    result = aggregate(intervals([(0, 75)], start, end), start=start, end=end)
    assert result.coverage == pytest.approx(120 / (hours * 3600))
    assert result.mean_soc_pct == 75


def test_clips_intervals_to_requested_window_and_rejects_overlap():
    qualified = intervals([(0, 99), (180, 20)])
    result = aggregate(qualified, start=at(60), end=at(240), sunrise=at(240))
    assert result.coverage == pytest.approx(120 / 180)
    assert result.mean_soc_pct == 59.5
    assert result.first_reached_99_at == at(60)
    assert result.sunrise_soc_pct is None
    with pytest.raises(ValueError, match="nonoverlapping"):
        aggregate([qualified[0], qualified[0]])
    with pytest.raises(ValueError, match="nonoverlapping"):
        aggregate(list(reversed(qualified)))


@pytest.mark.parametrize("covered,quality", [(540, "ok"), (539, "partial"),
                                            (300, "partial"), (299, "insufficient_data")])
def test_existing_quality_cutoffs_are_preserved(covered, quality):
    qualified = intervals([(n, 75) for n in range(0, covered, 120)], end=at(covered))
    assert aggregate(qualified).quality == quality


@pytest.mark.parametrize("failure", [None, "missing", "sequence", "previous_sequence"])
def test_daily_reader_uses_atomic_values_and_original_bank_bounds(monkeypatch, failure):
    config = load_source_config()
    config = replace(config, sources=tuple(
        replace(source, stale_policy="atomic_bms_evidence", freshness_item="BMS_SOC_Evidence_JSON")
        if source.canonical_name == "battery.soc_pct" else source for source in config.sources
    ))
    day = date(2026, 9, 10)
    start, end = local_day_bounds(day, config.timezone)
    epoch = select_epoch(load_epoch_config(), day)
    tables = {name: f"item{index:04d}" for index, name in enumerate(
        sorted(daily.REQUIRED_DAILY | {"solar.sunrise_at", "solar.sunset_at"}), 1)}
    resolved = [SimpleNamespace(canonical_name=name, table_name=table,
                               freshness_table_name=("item0613" if failure != "missing" else None)
                               if name == "battery.soc_pct" else None)
                for name, table in tables.items()]
    reads = []

    def numeric(_connection, table, left, right):
        assert table != tables["battery.soc_pct"], "legacy SoC must not be read"
        return [(left, 1000), (right, 1000)]

    def qualified(_connection, table, left, right, *, epoch_start, epoch_end):
        assert table == "item0613"
        assert epoch_start == local_day_bounds(epoch.start_local_date, config.timezone)[0]
        assert epoch_start < left  # not a relabeled start-of-day carry
        assert epoch_end is None
        reads.append((left, right))
        if failure == "sequence" or (failure == "previous_sequence" and left < start):
            raise EvidenceSequenceError("duplicate persistence timestamp")
        return intervals([(0, 75 if left == start else 90)], left, right)

    def text(_connection, table, left, right):
        assert table in {tables["solar.sunrise_at"], tables["solar.sunset_at"]}
        return [(left, (left + timedelta(seconds=60)).isoformat())]

    stats_tables = []

    def stats(_connection, table, left, right):
        stats_tables.append(table)
        return (1, left, left)

    monkeypatch.setattr(daily, "fetch_numeric_series", numeric)
    monkeypatch.setattr(daily, "fetch_bms_soc_intervals", qualified)
    monkeypatch.setattr(daily, "fetch_text_series", text)
    monkeypatch.setattr(daily, "fetch_observation_stats", stats)
    monkeypatch.setattr(daily, "fetch_snow_state_as_of", lambda *_: None)
    result = daily.build_daily_snapshot(object(), config, resolved, day, bank_epoch=epoch)
    battery = result["battery"]
    source = next(row for row in result["source_quality"] if row["canonical_name"] == "battery.soc_pct")
    assert tables["battery.soc_pct"] not in stats_tables
    assert source["detail"]["freshness_basis"] == "BMS_SOC_Evidence_JSON"
    if failure in {"missing", "sequence"}:
        assert battery["min_soc_pct"] is None
        assert battery["sunrise_soc_pct"] is None
        assert battery["overnight_soc_drop_pct"] is None
        assert source["coverage"] == 0
        assert source["stale_intervals"] == 1
    else:
        assert battery["min_soc_pct"] == battery["max_soc_pct"] == 75
        assert battery["sunrise_soc_pct"] == battery["sunset_soc_pct"] == 75
        assert battery["overnight_soc_drop_pct"] == (None if failure == "previous_sequence" else 15)
        assert source["coverage"] == pytest.approx(120 / (end-start).total_seconds())
        assert source["detail"]["reason"] is None
    assert source["quality"] == "insufficient_data"
    assert battery["charge_kwh"] == 24
    assert battery["daily_efc"] == pytest.approx(24 / (2 * 20.48))
    assert len(reads) == (0 if failure == "missing" else 2)
    if failure == "sequence":
        assert source["detail"]["reason"] == "ambiguous_evidence_sequence"
    with pytest.raises(ValueError, match="physical bank start"):
        daily.build_daily_snapshot(object(), config, resolved, day)
