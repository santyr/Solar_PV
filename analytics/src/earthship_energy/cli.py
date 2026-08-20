"""Command-line interface for deterministic Earthship energy analytics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .config import ConfigError, load_source_config
from .db import DatabaseConfigError, connect_read_only, parse_openhab_jdbc_config
from .inventory import SourceResolutionError, fetch_inventory, resolve_sources


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
    return parser


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


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


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate-config":
            return _validate_config(args.config)
        if args.command in {"validate-sources", "inventory"}:
            return _validate_sources(args.config, args.jdbc_config)
    except (ConfigError, DatabaseConfigError, SourceResolutionError) as exc:
        print(f"energy-data: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
