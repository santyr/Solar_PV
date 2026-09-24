from datetime import date, datetime, timedelta, timezone

import pytest

from earthship_energy.quality import assess_source_quality
from earthship_energy.series import local_day_bounds


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


def test_astro_self_dated_schedule_qualifies_only_matching_local_day():
    start, end = local_day_bounds(date(2026, 9, 23), "America/Denver")
    matching = (start + timedelta(hours=6, minutes=55)).isoformat()
    previous = (start - timedelta(hours=17)).isoformat()
    result = assess_source_quality(
        canonical_name="solar.sunrise_at", row_count=1,
        first_at=start + timedelta(seconds=1), last_at=start + timedelta(seconds=1),
        window_start=start, window_end=end, stale_policy="local_date_must_match",
        stale_after_seconds=None, freshness_item="Sun_Rise_End",
        freshness_points=[(start - timedelta(days=1), previous),
                          (start + timedelta(seconds=1), matching)],
        site_timezone="America/Denver",
    )
    assert result["quality"] == "ok"
    assert result["coverage"] == (end - start - timedelta(seconds=1)) / (end - start)
    assert result["stale_intervals"] == 1


def test_astro_self_dated_schedule_rejects_wrong_day_and_old_carry():
    start, end = local_day_bounds(date(2026, 9, 23), "America/Denver")
    matching = (start + timedelta(hours=6, minutes=55)).isoformat()
    wrong_day = (start + timedelta(days=1, hours=6)).isoformat()
    common = dict(canonical_name="solar.sunrise_at", row_count=1,
                  first_at=start, last_at=start, window_start=start, window_end=end,
                  stale_policy="local_date_must_match", stale_after_seconds=None,
                  freshness_item="Sun_Rise_End", site_timezone="America/Denver")
    wrong = assess_source_quality(**common, freshness_points=[(start, wrong_day)])
    stale = assess_source_quality(**common, freshness_points=[
        (start - timedelta(hours=31), matching)])
    assert wrong["quality"] == stale["quality"] == "insufficient_data"
    assert wrong["coverage"] == stale["coverage"] == 0
    with pytest.raises(ValueError, match="site timezone"):
        assess_source_quality(**{**common, "site_timezone": None},
                              freshness_points=[(start, matching)])


def test_astro_local_date_policy_covers_25_hour_denver_day():
    start, end = local_day_bounds(date(2026, 11, 1), "America/Denver")
    assert end - start == timedelta(hours=25)
    result = assess_source_quality(
        canonical_name="solar.sunset_at", row_count=1,
        first_at=start + timedelta(seconds=1), last_at=start + timedelta(seconds=1),
        window_start=start, window_end=end, stale_policy="local_date_must_match",
        stale_after_seconds=None, freshness_item="Sun_Set_Start",
        freshness_points=[(start + timedelta(seconds=1),
                           (end - timedelta(hours=5)).isoformat())],
        site_timezone="America/Denver",
    )
    assert result["quality"] == "ok"
    assert result["coverage"] == (25 * 3600 - 1) / (25 * 3600)
