"""Command-line interface for deterministic Earthship energy analytics."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from .config import ConfigError, load_source_config
from .daily import build_daily_snapshot
from .db import (
    DatabaseConfigError,
    connect_read_only,
    connect_write,
    parse_openhab_jdbc_config,
)
from .inventory import SourceResolutionError, fetch_inventory, resolve_sources
from .events import SnowEvent, persist_snow_event
from .export import export_feature_csv
from .feature_reader import fetch_feature_rows
from .imports import (
    fetch_existing_import_hashes,
    persist_lynk_import,
    prepare_lynk_import,
)
from .materialize import (
    EpochConfigError,
    load_epoch_config,
    materialize_daily_snapshot,
    seed_reference_data,
    select_epoch,
)
from .migrations import (
    BackupGateError,
    MigrationDriftError,
    apply_migrations,
    discover_migrations,
    get_applied_migrations,
    load_verified_backup_manifest,
    plan_migrations,
)
from .report_reader import fetch_daily_report_rows, fetch_module_report_rows
from .reports import (
    lifecycle_report,
    module_health_report,
    monthly_report,
    winter_report,
)


DEFAULT_JDBC_CONFIG = "/var/lib/openhab/config/org/openhab/jdbc.config"
REPORT_TIMEZONE = ZoneInfo("America/Denver")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="energy-data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_config = subparsers.add_parser("validate-config")
    validate_config.add_argument("--config", type=Path)

    for name in ("validate-sources", "inventory"):
        command = subparsers.add_parser(name)
        command.add_argument("--config", type=Path)
        command.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG, type=Path)
        command.add_argument(
            "--read-only",
            action="store_true",
            help="Compatibility flag; inventory commands are always read-only.",
        )
    migrate = subparsers.add_parser("migrate")
    migrate.add_argument("--migrations", type=Path)
    migrate.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG, type=Path)
    mode = migrate.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    migrate.add_argument("--backup-manifest", type=Path)
    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--date", required=True)
    aggregate.add_argument("--config", type=Path)
    aggregate.add_argument("--epochs", type=Path)
    aggregate.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG, type=Path)
    aggregate_mode = aggregate.add_mutually_exclusive_group()
    aggregate_mode.add_argument("--dry-run", action="store_true")
    aggregate_mode.add_argument("--apply", action="store_true")
    aggregate.add_argument("--backup-manifest", type=Path)
    report = subparsers.add_parser("report")
    report.add_argument("kind", choices=("monthly", "winter", "lifecycle", "modules"))
    report.add_argument("--start")
    report.add_argument("--end", help="Exclusive local end date")
    report.add_argument("--epoch")
    report.add_argument("--epochs", type=Path)
    report.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG, type=Path)
    report.add_argument("--format", choices=("json", "markdown"), default="json")
    lynk = subparsers.add_parser("import-lynk")
    lynk.add_argument("--file", required=True, type=Path)
    lynk.add_argument("--source-name")
    lynk.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG, type=Path)
    lynk_mode = lynk.add_mutually_exclusive_group(required=True)
    lynk_mode.add_argument("--dry-run", action="store_true")
    lynk_mode.add_argument("--apply", action="store_true")
    snow = subparsers.add_parser("record-snow")
    snow.add_argument("--state", required=True, choices=("snow_covered", "snow_cleared"))
    snow.add_argument("--occurred-at", required=True)
    snow.add_argument("--method", required=True)
    snow.add_argument("--confidence", required=True, type=float)
    snow.add_argument("--note")
    snow.add_argument("--evidence-json", default="{}")
    snow.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG, type=Path)
    snow_mode = snow.add_mutually_exclusive_group(required=True)
    snow_mode.add_argument("--dry-run", action="store_true")
    snow_mode.add_argument("--apply", action="store_true")
    feature_export = subparsers.add_parser("export-features")
    feature_export.add_argument("--start", required=True)
    feature_export.add_argument("--end", required=True)
    feature_export.add_argument("--output", required=True, type=Path)
    feature_export.add_argument("--cadence", type=int, choices=(5, 15), default=15)
    feature_export.add_argument("--config", type=Path)
    feature_export.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG, type=Path)
    feature_export.add_argument("--force", action="store_true")
    return parser


def _print(payload: object) -> None:
    def encode(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        raise TypeError(f"cannot encode {type(value).__name__}")

    print(json.dumps(payload, indent=2, sort_keys=True, default=encode))


def _validate_config(config_path: Path | None) -> int:
    config = load_source_config(config_path)
    _print(
        {
            "status": "ok",
            "version": config.version,
            "timezone": config.timezone,
            "sources": len(config.sources),
            "planned_sources": len(config.planned_sources),
        }
    )
    return 0


def _validate_sources(config_path: Path | None, jdbc_path: Path) -> int:
    config = load_source_config(config_path)
    settings = parse_openhab_jdbc_config(jdbc_path)
    try:
        connection = connect_read_only(settings)
    except Exception as exc:
        raise DatabaseConfigError(
            f"database connection failed ({type(exc).__name__})"
        ) from exc
    try:
        items, tables = fetch_inventory(connection)
    finally:
        close = getattr(connection, "close", None)
        if close is not None:
            close()
    resolved = resolve_sources(config, items, tables)
    _print(
        {
            "status": "ok",
            "database": settings.safe_summary(),
            "mode": "read_only",
            "resolved_sources": [source.as_dict() for source in resolved],
        }
    )
    return 0


def _migrate(args) -> int:
    settings = parse_openhab_jdbc_config(args.jdbc_config)
    migrations = discover_migrations(args.migrations)
    if args.apply:
        if args.backup_manifest is None:
            raise BackupGateError("--backup-manifest is required with --apply")
        load_verified_backup_manifest(args.backup_manifest, settings.dbname)
        connection_factory = connect_write
        mode = "apply"
    else:
        connection_factory = connect_read_only
        mode = "dry_run"
    try:
        connection = connection_factory(settings)
    except Exception as exc:
        raise DatabaseConfigError(
            f"database connection failed ({type(exc).__name__})"
        ) from exc
    try:
        applied = get_applied_migrations(connection)
        pending = plan_migrations(migrations, applied)
        applied_now = apply_migrations(connection, pending) if args.apply else []
    finally:
        close = getattr(connection, "close", None)
        if close is not None:
            close()
    _print(
        {
            "status": "ok",
            "mode": mode,
            "database": settings.safe_summary(),
            "pending": [migration.as_dict() for migration in pending],
            "applied_now": applied_now,
        }
    )
    return 0


def _aggregate(args) -> int:
    if not args.dry_run and not args.apply:
        raise ValueError("aggregate requires --dry-run or --apply")
    try:
        local_date = date.fromisoformat(args.date)
    except ValueError as exc:
        raise ValueError("--date must use YYYY-MM-DD") from exc
    config = load_source_config(args.config)
    settings = parse_openhab_jdbc_config(args.jdbc_config)
    if args.apply:
        connection_factory = connect_write
    else:
        connection_factory = connect_read_only
    try:
        connection = connection_factory(settings)
    except Exception as exc:
        raise DatabaseConfigError(
            f"database connection failed ({type(exc).__name__})"
        ) from exc
    try:
        if args.apply:
            pending = plan_migrations(
                discover_migrations(), get_applied_migrations(connection)
            )
            if pending:
                raise MigrationDriftError(
                    "pending migrations must be applied before aggregate"
                )
        items, tables = fetch_inventory(connection)
        resolved = resolve_sources(config, items, tables)
        snapshot = build_daily_snapshot(connection, config, resolved, local_date)
        if args.apply:
            epochs = load_epoch_config(args.epochs)
            epoch = select_epoch(epochs, local_date)
            seed_reference_data(connection, config, epochs)
            result = materialize_daily_snapshot(
                connection, snapshot, epoch.epoch_id
            )
            result.update({"status": "ok", "mode": "materialized"})
        else:
            result = snapshot
    finally:
        close = getattr(connection, "close", None)
        if close is not None:
            close()
    _print(result)
    return 0


def _report(args) -> int:
    epochs = load_epoch_config(args.epochs)
    if args.epoch:
        matches = [epoch for epoch in epochs if epoch.epoch_id == args.epoch]
        if len(matches) != 1:
            raise EpochConfigError(f"unknown epoch: {args.epoch}")
        epoch = matches[0]
    else:
        epoch = next(epoch for epoch in epochs if epoch.current_analytics)
    try:
        start = date.fromisoformat(args.start) if args.start else epoch.start_local_date
        end = date.fromisoformat(args.end) if args.end else date.today()
    except ValueError as exc:
        raise ValueError("report dates must use YYYY-MM-DD") from exc
    if start is None:
        raise ValueError("--start is required for an open-ended historical epoch")
    settings = parse_openhab_jdbc_config(args.jdbc_config)
    connection = connect_read_only(settings)
    try:
        if args.kind == "modules":
            rows = fetch_module_report_rows(
                connection,
                datetime.combine(start, time.min, tzinfo=REPORT_TIMEZONE),
                datetime.combine(end, time.min, tzinfo=REPORT_TIMEZONE),
            )
        else:
            rows = fetch_daily_report_rows(connection, epoch.epoch_id, start, end)
    finally:
        connection.close()
    if args.kind == "monthly":
        payload = monthly_report(rows, epoch_id=epoch.epoch_id)
    elif args.kind == "lifecycle":
        payload = lifecycle_report(rows)
        payload["epoch_id"] = epoch.epoch_id
    elif args.kind == "modules":
        payload = module_health_report(rows)
        payload["epoch_id"] = epoch.epoch_id
    else:
        if epoch.nominal_usable_kwh is None:
            raise ValueError("winter report requires epoch nominal_usable_kwh")
        payload = winter_report(
            rows, nominal_usable_kwh=epoch.nominal_usable_kwh,
            reserve_soc_pct=20.0,
        )
        payload["epoch_id"] = epoch.epoch_id
    if args.format == "json":
        _print(payload)
    else:
        print(f"# {payload['report'].replace('_', ' ').title()}\n")
        print(f"- Epoch: `{epoch.epoch_id}`")
        print(f"- Window: `{start.isoformat()}` through `{(end - timedelta(days=1)).isoformat()}`")
        print("\n```json")
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        print("```")
    return 0


def _import_lynk(args) -> int:
    try:
        content = args.file.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read LYNK CSV: {exc}") from exc
    settings = parse_openhab_jdbc_config(args.jdbc_config)
    connection_factory = connect_write if args.apply else connect_read_only
    try:
        connection = connection_factory(settings)
    except Exception as exc:
        raise DatabaseConfigError(
            f"database connection failed ({type(exc).__name__})"
        ) from exc
    try:
        if args.apply:
            pending = plan_migrations(
                discover_migrations(), get_applied_migrations(connection)
            )
            if pending:
                raise MigrationDriftError(
                    "pending migrations must be applied before LYNK import"
                )
        existing = fetch_existing_import_hashes(connection)
        source_name = args.source_name or args.file.name
        batch = prepare_lynk_import(content, source_name, existing)
        if args.apply:
            result = persist_lynk_import(connection, batch)
            result["mode"] = "materialized"
        else:
            result = {
                "status": batch.status,
                "mode": "dry_run",
                "source_name": source_name,
                "sha256": batch.sha256,
                "rows": len(batch.rows),
            }
    finally:
        connection.close()
    _print(result)
    return 0


def _aware_datetime(raw: str, field: str) -> datetime:
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must include timezone information")
    return value


def _record_snow(args) -> int:
    try:
        evidence = json.loads(args.evidence_json)
    except json.JSONDecodeError as exc:
        raise ValueError("--evidence-json must be valid JSON") from exc
    if not isinstance(evidence, dict):
        raise ValueError("--evidence-json must be an object")
    event = SnowEvent(
        occurred_at=_aware_datetime(args.occurred_at, "--occurred-at"),
        state=args.state,
        method=args.method,
        confidence=args.confidence,
        note=args.note,
        evidence=evidence,
    )
    if not args.apply:
        payload = {
            "status": "ready",
            "mode": "dry_run",
            "event": {
                **asdict(event),
                "authority": "observational_only",
            },
        }
        _print(payload)
        return 0
    settings = parse_openhab_jdbc_config(args.jdbc_config)
    try:
        connection = connect_write(settings)
    except Exception as exc:
        raise DatabaseConfigError(
            f"database connection failed ({type(exc).__name__})"
        ) from exc
    try:
        pending = plan_migrations(
            discover_migrations(), get_applied_migrations(connection)
        )
        if pending:
            raise MigrationDriftError(
                "pending migrations must be applied before recording snow event"
            )
        result = persist_snow_event(connection, event)
    finally:
        connection.close()
    result["mode"] = "materialized"
    _print(result)
    return 0


def _export_features(args) -> int:
    start = _aware_datetime(args.start, "--start")
    end = _aware_datetime(args.end, "--end")
    if end <= start:
        raise ValueError("--end must be after --start")
    if args.output.exists() and not args.force:
        raise ValueError("output exists; pass --force to replace it")
    if not args.output.parent.is_dir():
        raise ValueError("output parent directory does not exist")
    config = load_source_config(args.config)
    settings = parse_openhab_jdbc_config(args.jdbc_config)
    try:
        connection = connect_read_only(settings)
    except Exception as exc:
        raise DatabaseConfigError(
            f"database connection failed ({type(exc).__name__})"
        ) from exc
    try:
        items, tables = fetch_inventory(connection)
        resolved = resolve_sources(config, items, tables)
        source_tables = {
            source.canonical_name: source.table_name
            for source in resolved if source.table_name is not None
        }
        source_conversions = {
            source.canonical_name: source.conversion
            for source in config.sources
        }
        rows = fetch_feature_rows(
            connection, source_tables, start, end,
            cadence_minutes=args.cadence, timezone_name=config.timezone,
            conversions=source_conversions,
        )
    finally:
        connection.close()
    content = export_feature_csv(rows, cadence_minutes=args.cadence)
    try:
        args.output.write_bytes(content)
    except OSError as exc:
        raise ValueError(f"cannot write feature export: {exc}") from exc
    _print({
        "status": "ok",
        "schema_version": 2,
        "rows": len(rows),
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "output": str(args.output),
    })
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate-config":
            return _validate_config(args.config)
        if args.command in {"validate-sources", "inventory"}:
            return _validate_sources(args.config, args.jdbc_config)
        if args.command == "migrate":
            return _migrate(args)
        if args.command == "aggregate":
            return _aggregate(args)
        if args.command == "report":
            return _report(args)
        if args.command == "import-lynk":
            return _import_lynk(args)
        if args.command == "record-snow":
            return _record_snow(args)
        if args.command == "export-features":
            return _export_features(args)
    except (
        BackupGateError,
        ConfigError,
        DatabaseConfigError,
        EpochConfigError,
        MigrationDriftError,
        SourceResolutionError,
        ValueError,
    ) as exc:
        print(f"energy-data: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
