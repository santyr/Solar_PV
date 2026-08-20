from datetime import date, datetime, timezone
from types import SimpleNamespace

from earthship_energy.ui_reader import (
    build_energy_ui_snapshot,
    fetch_ui_health_and_forecast,
)


UTC = timezone.utc
NOW = datetime(2026, 8, 20, 18, 0, tzinfo=UTC)


class Cursor:
    def __init__(self, quality, forecast):
        self.quality = quality
        self.forecast = forecast
        self.calls = []
        self.index = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.calls.append((" ".join(sql.split()), params))
        self.index += 1

    def fetchall(self):
        assert self.index == 1
        return self.quality

    def fetchone(self):
        assert self.index == 2
        return self.forecast


class Connection:
    def __init__(self, quality, forecast):
        self.instance = Cursor(quality, forecast)

    def cursor(self):
        return self.instance


def test_health_and_forecast_reader_is_schema_bounded_and_time_bounded():
    issued = datetime(2026, 8, 20, 17, 0, tzinfo=UTC)
    valid = datetime(2026, 8, 21, 6, 0, tzinfo=UTC)
    connection = Connection(
        [
            ("battery.soc_pct", "ok"),
            ("battery.dc_voltage_v", "ok"),
            ("pv.input_power_w", "ok"),
            ("house.ac_power_w", "ok"),
            ("weather.irradiance_w_m2", "ok"),
        ],
        (issued, valid, 7.2),
    )

    forecast, health = fetch_ui_health_and_forecast(
        connection,
        through_date=date(2026, 8, 19),
        generated_at=NOW,
        timezone_name="America/Denver",
    )

    quality_sql, quality_params = connection.instance.calls[0]
    forecast_sql, forecast_params = connection.instance.calls[1]
    assert "energy_analytics.daily_source_quality" in quality_sql
    assert quality_params == (date(2026, 8, 19),)
    assert "energy_analytics.forecast_snapshots" in forecast_sql
    assert "issued_at <= %s" in forecast_sql
    assert "valid_for >= %s" in forecast_sql
    assert "LIMIT 1" in forecast_sql
    assert forecast_params[0] == NOW
    assert forecast["status"] == "current"
    assert forecast["pv24hKwh"] == 7.2
    assert health == {
        "analytics": "ok",
        "forecast": "ok",
        "bms": "ok",
        "schneider": "ok",
        "weather": "ok",
        "collector": "ok",
        "reasons": [],
    }


def test_health_reader_marks_missing_groups_and_stale_forecast_explicitly():
    connection = Connection(
        [("battery.soc_pct", "freshness_unverified")],
        (datetime(2026, 8, 20, 8, 0, tzinfo=UTC), NOW, 4.0),
    )

    forecast, health = fetch_ui_health_and_forecast(
        connection,
        through_date=date(2026, 8, 19),
        generated_at=NOW,
        timezone_name="America/Denver",
    )

    assert forecast["status"] == "stale"
    assert forecast["reason"] == "forecast_issue_older_than_6h"
    assert health["analytics"] == "degraded"
    assert health["bms"] == "degraded"
    assert health["schneider"] == "unavailable"
    assert health["weather"] == "unavailable"
    assert health["collector"] == "degraded"
    assert "missing_schneider_quality_evidence" in health["reasons"]


def test_snapshot_uses_active_epoch_completed_days_and_existing_reports(monkeypatch):
    calls = []
    epochs = (
        SimpleNamespace(
            epoch_id="discover_4_module_2026",
            start_local_date=date(2026, 7, 19),
            current_analytics=True,
            nominal_usable_kwh=20.48,
        ),
    )
    daily = [{
        "local_date": date(2026, 8, 19), "quality": "ok",
        "min_soc_pct": 70.0, "reached_99": False,
        "charge_kwh": 3.0, "discharge_kwh": 4.0, "daily_efc": 0.1,
        "cumulative_efc": 2.1, "hours_above_90": 1.0,
        "hours_above_95": 0.0, "min_temperature_c": 20.0,
        "max_temperature_c": 25.0, "pv_kwh": 5.0, "load_kwh": 6.0,
    }]
    monkeypatch.setattr(
        "earthship_energy.ui_reader.fetch_daily_report_rows",
        lambda connection, epoch, start, end: calls.append(
            ("daily", epoch, start, end)
        ) or daily,
    )
    monkeypatch.setattr(
        "earthship_energy.ui_reader.fetch_module_report_rows",
        lambda connection, start, end: calls.append(("modules", start, end)) or [],
    )
    monkeypatch.setattr(
        "earthship_energy.ui_reader.fetch_ui_health_and_forecast",
        lambda *args, **kwargs: (
            {"status": "unavailable", "issuedAt": None, "validFor": None,
             "pv24hKwh": None, "reason": "no_forecast_snapshot"},
            {"analytics": "ok", "forecast": "unavailable", "bms": "ok",
             "schneider": "ok", "weather": "ok", "collector": "ok",
             "reasons": ["no_forecast_snapshot"]},
        ),
    )

    result = build_energy_ui_snapshot("db", epochs, generated_at=NOW)

    assert calls[0] == (
        "daily", "discover_4_module_2026", date(2026, 7, 19), date(2026, 8, 20)
    )
    assert calls[1][0] == "modules"
    assert result["schema"] == "earthship-energy-ui/v1"
    assert result["throughDate"] == "2026-08-19"
    assert result["epochId"] == "discover_4_module_2026"
