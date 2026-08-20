from datetime import datetime, timedelta, timezone

from earthship_energy.quality import assess_source_quality


UTC = timezone.utc
START = datetime(2026, 8, 19, tzinfo=UTC)
END = START + timedelta(hours=1)


def test_timestamp_companion_expires_instead_of_authorizing_daywide_carry():
    result = assess_source_quality(
        canonical_name="battery.dc_power_w",
        row_count=2,
        first_at=START + timedelta(minutes=1),
        last_at=START + timedelta(minutes=10),
        window_start=START,
        window_end=END,
        stale_policy="timestamp_threshold",
        stale_after_seconds=120,
        freshness_item="DC_LastUpdate",
        freshness_points=[
            (START, START.isoformat()),
            (START + timedelta(minutes=10),
             (START + timedelta(minutes=10)).isoformat()),
            (END, (START + timedelta(minutes=10)).isoformat()),
        ],
    )
    assert result["coverage"] == 240 / 3600
    assert result["stale_intervals"] == 2
    assert result["quality"] == "insufficient_data"


def test_ok_status_companion_authorizes_unchanged_measurement():
    result = assess_source_quality(
        canonical_name="battery.soc_pct",
        row_count=0,
        first_at=None,
        last_at=None,
        window_start=START,
        window_end=END,
        stale_policy="status_must_equal_OK",
        stale_after_seconds=None,
        freshness_item="BMS_Comms_Status",
        freshness_points=[(START, "OK"), (END, "OK")],
    )
    assert result["coverage"] == 1
    assert result["quality"] == "ok"
    assert result["detail"]["freshness_basis"] == "BMS_Comms_Status"


def test_source_without_health_companion_is_explicitly_unverified():
    result = assess_source_quality(
        canonical_name="thermal.indoor_illuminance",
        row_count=3,
        first_at=START,
        last_at=END,
        window_start=START,
        window_end=END,
        stale_policy="source_quality",
        stale_after_seconds=None,
        freshness_item=None,
        freshness_points=[],
    )
    assert result["coverage"] == 0
    assert result["quality"] == "freshness_unverified"
