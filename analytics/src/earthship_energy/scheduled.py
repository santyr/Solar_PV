"""Deterministic helpers and entry points for local scheduled energy work."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from . import cli as energy_cli
from .config import load_source_config
from .db import connect_read_only, connect_write, parse_openhab_jdbc_config
from .forecasts import persist_forecast_snapshots, snapshots_from_openhab_detail
from .inventory import fetch_inventory, resolve_sources


SEVERITIES = ("Routine", "Interesting", "Actionable", "Critical electrical condition")
DEFAULT_JDBC_CONFIG = "/var/lib/openhab/config/org/openhab/jdbc.config"
OPENHAB_FORECAST_URL = "http://127.0.0.1:8080/rest/items/Forecast_10Day_JSON/state"


def utc_now() -> datetime:
    return datetime.now(ZoneInfo("UTC"))


def previous_local_date(now: datetime, timezone_name: str) -> date:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("scheduler time must be timezone-aware")
    return now.astimezone(ZoneInfo(timezone_name)).date() - timedelta(days=1)


def highest_severity(checks: list[dict[str, object]]) -> str:
    try:
        return max(
            (str(check["severity"]) for check in checks),
            key=SEVERITIES.index,
            default="Routine",
        )
    except (KeyError, ValueError) as exc:
        raise ValueError("check severity is outside the closed severity model") from exc


def capture_forecast(payload: dict[str, object], connection) -> dict[str, object]:
    snapshots = snapshots_from_openhab_detail(payload)
    inserted = persist_forecast_snapshots(connection, snapshots)
    return {"status": "ok", "snapshots": len(snapshots), "inserted": inserted}


def build_quality_report(
    *,
    now: datetime,
    timezone_name: str,
    sources_ok: bool,
    latest_aggregate: date | None,
    latest_forecast_issued: datetime | None,
) -> dict[str, object]:
    yesterday = previous_local_date(now, timezone_name)
    checks = [{
        "name": "source_inventory",
        "severity": "Routine" if sources_ok else "Actionable",
        "ok": sources_ok,
    }]
    aggregate_ok = latest_aggregate is not None and latest_aggregate >= yesterday
    checks.append({
        "name": "daily_aggregate",
        "severity": "Routine" if aggregate_ok else "Actionable",
        "ok": aggregate_ok,
        "latest": latest_aggregate.isoformat() if latest_aggregate else None,
        "expected_through": yesterday.isoformat(),
    })
    if latest_forecast_issued is None:
        forecast_age = None
        forecast_severity = "Actionable"
    else:
        if latest_forecast_issued.tzinfo is None or latest_forecast_issued.utcoffset() is None:
            raise ValueError("forecast issue timestamp must be timezone-aware")
        forecast_age = (now - latest_forecast_issued).total_seconds()
        forecast_severity = (
            "Routine" if forecast_age <= 2 * 3600
            else "Interesting" if forecast_age <= 6 * 3600
            else "Actionable"
        )
    checks.append({
        "name": "forecast_snapshot",
        "severity": forecast_severity,
        "ok": forecast_severity == "Routine",
        "age_seconds": forecast_age,
    })
    return {
        "schema": "earthship-energy-quality/v1",
        "generated_at": now.isoformat(),
        "severity": highest_severity(checks),
        "checks": checks,
    }


def assess_backup(
    manifest: dict[str, object],
    *,
    now: datetime,
    readable: bool,
    max_age: timedelta,
) -> dict[str, object]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("backup assessment time must be timezone-aware")
    try:
        verified_at = datetime.fromisoformat(str(manifest["verified_at"]))
        archive = Path(str(manifest["archive_path"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("backup manifest lacks dated verification evidence") from exc
    if verified_at.tzinfo is None or verified_at.utcoffset() is None:
        raise ValueError("backup verified_at must be timezone-aware")
    fresh = now - verified_at <= max_age
    restored = manifest.get("status") == "restore_verified"
    off_host = manifest.get("off_host") is True
    available = archive.is_file()
    disaster_recovery = fresh and restored and readable and available and off_host
    if not off_host:
        severity = "Actionable"
        reason = "verified restore point has no off-host disaster-recovery copy"
    elif not (fresh and restored and readable and available):
        severity = "Actionable"
        reason = "backup evidence is stale, unavailable, unreadable, or unverified"
    else:
        severity = "Routine"
        reason = "fresh readable off-host restore evidence"
    return {
        "fresh": fresh,
        "readable": bool(readable and available),
        "restore_verified": restored,
        "off_host": off_host,
        "disaster_recovery": disaster_recovery,
        "severity": severity,
        "reason": reason,
    }


def write_event(directory: str | Path, payload: dict[str, object]) -> Path:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    event_id = str(payload.get("event_id", ""))
    if not event_id or "/" in event_id or event_id in {".", ".."}:
        raise ValueError("event_id must be a safe non-empty filename component")
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    target = root / f"{event_id}.json"
    if target.exists():
        if target.read_bytes() != encoded:
            raise ValueError("event_id already exists with different evidence")
        return target
    descriptor, temporary_name = tempfile.mkstemp(prefix=".event-", suffix=".tmp", dir=root)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def write_private_json(target: str | Path, payload: dict[str, object]) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(target.parent, 0o700)
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def fetch_openhab_forecast_detail() -> dict[str, object]:
    token = os.environ.get("OPENHAB_TOKEN")
    if not token:
        raise ValueError("OPENHAB_TOKEN is required")
    request = Request(
        OPENHAB_FORECAST_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    with urlopen(request, timeout=20) as response:
        state = response.read().decode("utf-8")
    payload = json.loads(state)
    if not isinstance(payload, dict):
        raise ValueError("OpenHAB forecast detail state must be a JSON object")
    return payload


def read_quality_state(jdbc_config: str) -> tuple[bool, date | None, datetime | None]:
    settings = parse_openhab_jdbc_config(jdbc_config)
    connection = connect_read_only(settings)
    try:
        items, tables = fetch_inventory(connection)
        resolve_sources(load_source_config(), items, tables)
        with connection.cursor() as cursor:
            cursor.execute("SELECT max(local_date) FROM energy_analytics.daily_battery")
            latest_aggregate = cursor.fetchone()[0]
            cursor.execute("SELECT max(issued_at) FROM energy_analytics.forecast_snapshots")
            latest_forecast = cursor.fetchone()[0]
    finally:
        connection.close()
    return True, latest_aggregate, latest_forecast


def archive_is_readable(path: str | Path) -> bool:
    result = subprocess.run(
        ["pg_restore", "--list", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=300,
        check=False,
    )
    return result.returncode == 0


def _event_from_result(kind: str, result: dict[str, object]) -> dict[str, object]:
    evidence = {key: value for key, value in result.items() if key != "generated_at"}
    digest = hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:20]
    return {
        "schema": "earthship-energy-event/v1",
        "event_id": f"{kind}-{digest}",
        "kind": kind,
        "severity": result["severity"],
        "evidence": evidence,
        "status": "pending_investigation",
    }


def _exit_for_severity(severity: str) -> int:
    return {"Routine": 0, "Interesting": 10, "Actionable": 20,
            "Critical electrical condition": 30}[severity]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="energy-scheduled")
    commands = parser.add_subparsers(dest="command", required=True)
    forecast = commands.add_parser("forecast-snapshot")
    forecast.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG)
    aggregate = commands.add_parser("daily-aggregate")
    aggregate.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG)
    aggregate.add_argument("--timezone", default="America/Denver")
    quality = commands.add_parser("data-quality")
    quality.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG)
    quality.add_argument("--timezone", default="America/Denver")
    quality.add_argument(
        "--event-dir", default="~/.local/state/earthship-energy/pending-events"
    )
    backup = commands.add_parser("backup-check")
    backup.add_argument("--manifest", required=True)
    backup.add_argument(
        "--event-dir", default="~/.local/state/earthship-energy/pending-events"
    )
    backup.add_argument("--max-age-days", type=int, default=7)
    monthly = commands.add_parser("monthly-report")
    monthly.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG)
    monthly.add_argument("--timezone", default="America/Denver")
    monthly.add_argument(
        "--output-dir", default="~/.local/state/earthship-energy/reports"
    )
    monthly.add_argument(
        "--event-dir", default="~/.local/state/earthship-energy/pending-events"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "forecast-snapshot":
        payload = fetch_openhab_forecast_detail()
        connection = connect_write(parse_openhab_jdbc_config(args.jdbc_config))
        try:
            result = capture_forecast(payload, connection)
        finally:
            connection.close()
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    if args.command == "daily-aggregate":
        local_date = previous_local_date(utc_now(), args.timezone)
        return energy_cli.main([
            "aggregate",
            "--date",
            local_date.isoformat(),
            "--apply",
            "--jdbc-config",
            args.jdbc_config,
        ])
    if args.command == "data-quality":
        now = utc_now()
        sources_ok, latest_aggregate, latest_forecast = read_quality_state(
            args.jdbc_config
        )
        result = build_quality_report(
            now=now,
            timezone_name=args.timezone,
            sources_ok=sources_ok,
            latest_aggregate=latest_aggregate,
            latest_forecast_issued=latest_forecast,
        )
        if result["severity"] == "Actionable":
            write_event(Path(args.event_dir).expanduser(), _event_from_result("data-quality", result))
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return _exit_for_severity(str(result["severity"]))
    if args.command == "backup-check":
        manifest_path = Path(args.manifest).expanduser()
        manifest = json.loads(manifest_path.read_text())
        if not isinstance(manifest, dict):
            raise ValueError("backup manifest must be an object")
        normalized = dict(manifest)
        normalized["off_host"] = manifest.get("storage_scope") == "off_host"
        result = assess_backup(
            normalized,
            now=utc_now(),
            readable=archive_is_readable(str(manifest["archive_path"])),
            max_age=timedelta(days=args.max_age_days),
        )
        if result["severity"] == "Actionable":
            write_event(Path(args.event_dir).expanduser(), _event_from_result("backup", result))
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return _exit_for_severity(str(result["severity"]))
    if args.command == "monthly-report":
        today = utc_now().astimezone(ZoneInfo(args.timezone)).date()
        end = today.replace(day=1)
        start = (end - timedelta(days=1)).replace(day=1)
        output = io.StringIO()
        with redirect_stdout(output):
            status = energy_cli.main([
                "report", "monthly",
                "--start", start.isoformat(),
                "--end", end.isoformat(),
                "--format", "json",
                "--jdbc-config", args.jdbc_config,
            ])
        if status != 0:
            return status
        payload = json.loads(output.getvalue())
        report_path = (
            Path(args.output_dir).expanduser()
            / start.strftime("%Y-%m")
            / "energy-monthly.json"
        )
        write_private_json(report_path, payload)
        digest = hashlib.sha256(report_path.read_bytes()).hexdigest()
        result = {
            "schema": "earthship-energy-monthly-preparation/v1",
            "severity": "Interesting",
            "period_start": start.isoformat(),
            "period_end_exclusive": end.isoformat(),
            "report_path": str(report_path),
            "report_sha256": digest,
            "codex_invoked": False,
        }
        write_event(
            Path(args.event_dir).expanduser(),
            _event_from_result("monthly-review", result),
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return _exit_for_severity("Interesting")
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
