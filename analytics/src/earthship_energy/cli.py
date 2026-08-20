"""Command-line interface for deterministic Earthship energy analytics."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import sys

from .config import ConfigError, load_source_config
from .daily import build_daily_snapshot
from .db import (
    DatabaseConfigError,
    connect_read_only,
    connect_write,
    parse_openhab_jdbc_config,
)
from .inventory import SourceResolutionError, fetch_inventory, resolve_sources
from .migrations import (
    BackupGateError,
    MigrationDriftError,
    apply_migrations,
    discover_migrations,
    get_applied_migrations,
    load_verified_backup_manifest,
    plan_migrations,
)


DEFAULT_JDBC_CONFIG = "/var/lib/openhab/config/org/openhab/jdbc.config"


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
    aggregate.add_argument("--jdbc-config", default=DEFAULT_JDBC_CONFIG, type=Path)
    aggregate.add_argument("--dry-run", action="store_true")
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
    if not args.dry_run:
        raise ValueError("aggregate currently requires --dry-run")
    try:
        local_date = date.fromisoformat(args.date)
    except ValueError as exc:
        raise ValueError("--date must use YYYY-MM-DD") from exc
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
        snapshot = build_daily_snapshot(connection, config, resolved, local_date)
    finally:
        close = getattr(connection, "close", None)
        if close is not None:
            close()
    _print(snapshot)
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
    except (
        BackupGateError,
        ConfigError,
        DatabaseConfigError,
        MigrationDriftError,
        SourceResolutionError,
        ValueError,
    ) as exc:
        print(f"energy-data: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
