from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path

from earthship_energy.scheduled import (
    assess_backup,
    build_quality_report,
    capture_forecast,
    highest_severity,
    previous_local_date,
    write_event,
    main,
)


UTC = timezone.utc


def test_previous_local_date_uses_site_calendar_across_dst():
    assert previous_local_date(
        datetime(2026, 11, 2, 7, 30, tzinfo=UTC), "America/Denver"
    ).isoformat() == "2026-11-01"


def test_highest_severity_uses_closed_order():
    checks = [
        {"name": "source_inventory", "severity": "Routine"},
        {"name": "aggregate_age", "severity": "Actionable"},
        {"name": "forecast_age", "severity": "Interesting"},
    ]
    assert highest_severity(checks) == "Actionable"


def test_backup_assessment_distinguishes_restore_point_from_disaster_recovery(tmp_path):
    archive = tmp_path / "openhab.dump"
    archive.write_bytes(b"archive")
    now = datetime(2026, 8, 20, 12, tzinfo=UTC)
    manifest = {
        "status": "restore_verified",
        "archive_path": str(archive),
        "verified_at": (now - timedelta(days=1)).isoformat(),
        "off_host": False,
    }

    result = assess_backup(manifest, now=now, readable=True, max_age=timedelta(days=7))

    assert result["fresh"] is True
    assert result["readable"] is True
    assert result["disaster_recovery"] is False
    assert result["severity"] == "Actionable"
    assert "off-host" in result["reason"]


def test_write_event_is_private_atomic_and_idempotent(tmp_path):
    payload = {"schema": "earthship-energy-event/v1", "event_id": "same", "severity": "Actionable"}

    first = write_event(tmp_path, payload)
    second = write_event(tmp_path, payload)

    assert first == second
    assert json.loads(first.read_text()) == payload
    assert os.stat(first).st_mode & 0o777 == 0o600
    assert not list(Path(tmp_path).glob("*.tmp"))


def test_capture_forecast_reports_idempotent_insert_count(monkeypatch):
    payload = {
        "version": 1,
        "generatedAt": "2026-08-20T10:01:49-06:00",
        "timezone": "America/Denver",
        "days": [{
            "date": "2026-08-21",
            "summary": {"pvKwh": 6.9},
            "hours": [],
        }],
    }
    monkeypatch.setattr(
        "earthship_energy.scheduled.persist_forecast_snapshots",
        lambda connection, rows: 0 if connection == "db" and len(rows) == 1 else -1,
    )

    result = capture_forecast(payload, "db")

    assert result == {"status": "ok", "snapshots": 1, "inserted": 0}


def test_quality_report_escalates_missing_yesterday_aggregate():
    now = datetime(2026, 8, 20, 12, tzinfo=UTC)
    report = build_quality_report(
        now=now,
        timezone_name="America/Denver",
        sources_ok=True,
        latest_aggregate=date(2026, 8, 18),
        latest_forecast_issued=now - timedelta(hours=3),
    )

    assert report["severity"] == "Actionable"
    assert {row["name"]: row["severity"] for row in report["checks"]} == {
        "source_inventory": "Routine",
        "daily_aggregate": "Actionable",
        "forecast_snapshot": "Interesting",
    }


def test_forecast_snapshot_command_uses_openhab_detail_and_write_connection(monkeypatch, capsys):
    calls = []

    class Connection:
        def close(self):
            calls.append("close")

    monkeypatch.setattr(
        "earthship_energy.scheduled.fetch_openhab_forecast_detail",
        lambda: {"version": 1},
    )
    monkeypatch.setattr(
        "earthship_energy.scheduled.parse_openhab_jdbc_config",
        lambda _: "settings",
    )
    monkeypatch.setattr(
        "earthship_energy.scheduled.connect_write",
        lambda settings: calls.append(settings) or Connection(),
    )
    monkeypatch.setattr(
        "earthship_energy.scheduled.capture_forecast",
        lambda payload, connection: {"status": "ok", "snapshots": 10, "inserted": 4},
    )

    assert main(["forecast-snapshot", "--jdbc-config", "/protected/jdbc.config"]) == 0
    assert json.loads(capsys.readouterr().out)["inserted"] == 4
    assert calls == ["settings", "close"]


def test_daily_aggregate_command_uses_previous_site_day(monkeypatch):
    calls = []
    fixed_now = datetime(2026, 11, 2, 7, 30, tzinfo=UTC)
    monkeypatch.setattr("earthship_energy.scheduled.utc_now", lambda: fixed_now)
    monkeypatch.setattr(
        "earthship_energy.scheduled.energy_cli.main",
        lambda argv: calls.append(argv) or 0,
    )

    assert main(["daily-aggregate"]) == 0
    assert calls[0][:4] == ["aggregate", "--date", "2026-11-01", "--apply"]


def test_data_quality_command_writes_only_actionable_event(monkeypatch, tmp_path, capsys):
    now = datetime(2026, 8, 20, 12, tzinfo=UTC)
    monkeypatch.setattr(
        "earthship_energy.scheduled.read_quality_state",
        lambda _: (True, date(2026, 8, 18), now - timedelta(hours=3)),
    )
    monkeypatch.setattr("earthship_energy.scheduled.utc_now", lambda: now)

    assert main(["data-quality", "--event-dir", str(tmp_path)]) == 20
    output = json.loads(capsys.readouterr().out)
    assert output["severity"] == "Actionable"
    events = list(tmp_path.glob("*.json"))
    assert len(events) == 1


def test_backup_check_command_reports_same_host_limitation(monkeypatch, tmp_path, capsys):
    archive = tmp_path / "openhab.dump"
    archive.write_bytes(b"archive")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "status": "restore_verified",
        "archive_path": str(archive),
        "verified_at": "2026-08-19T12:00:00+00:00",
        "storage_scope": "same_host_same_filesystem",
    }))
    now = datetime(2026, 8, 20, 12, tzinfo=UTC)
    monkeypatch.setattr("earthship_energy.scheduled.utc_now", lambda: now)
    monkeypatch.setattr("earthship_energy.scheduled.archive_is_readable", lambda _: True)

    assert main([
        "backup-check", "--manifest", str(manifest), "--event-dir", str(tmp_path / "events")
    ]) == 20
    assert json.loads(capsys.readouterr().out)["disaster_recovery"] is False


def test_monthly_report_command_prepares_previous_month_without_invoking_codex(
    monkeypatch, tmp_path, capsys
):
    now = datetime(2026, 8, 20, 12, tzinfo=UTC)
    calls = []
    monkeypatch.setattr("earthship_energy.scheduled.utc_now", lambda: now)

    def report(argv):
        calls.append(argv)
        print(json.dumps({"report": "monthly", "metrics": {"pv_kwh": 12.3}}))
        return 0

    monkeypatch.setattr("earthship_energy.scheduled.energy_cli.main", report)

    assert main([
        "monthly-report", "--output-dir", str(tmp_path / "reports"),
        "--event-dir", str(tmp_path / "events"),
    ]) == 10
    assert calls[0][0:6] == [
        "report", "monthly", "--start", "2026-07-01", "--end", "2026-08-01"
    ]
    report_path = tmp_path / "reports" / "2026-07" / "energy-monthly.json"
    assert json.loads(report_path.read_text())["metrics"]["pv_kwh"] == 12.3
    assert (os.stat(report_path).st_mode & 0o777) == 0o600
    assert len(list((tmp_path / "events").glob("*.json"))) == 1
    assert "Codex" not in capsys.readouterr().out
