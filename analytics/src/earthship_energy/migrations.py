"""Checksum-pinned, transactional analytics schema migrations."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re


MIGRATION_NAME = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


class MigrationDriftError(RuntimeError):
    pass


class BackupGateError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    sql: str
    sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "name": self.name,
            "sha256": self.sha256,
        }


def default_migrations_path() -> Path:
    return Path(__file__).resolve().parents[2] / "sql" / "migrations"


def discover_migrations(path: str | Path | None = None) -> list[Migration]:
    directory = Path(path) if path is not None else default_migrations_path()
    migrations = []
    versions = set()
    for migration_path in sorted(directory.glob("*.sql")):
        match = MIGRATION_NAME.fullmatch(migration_path.name)
        if not match:
            raise ValueError(f"invalid migration filename: {migration_path.name}")
        version = int(match.group(1))
        if version in versions:
            raise ValueError(f"duplicate migration version: {version}")
        versions.add(version)
        raw = migration_path.read_bytes()
        migrations.append(
            Migration(
                version=version,
                name=match.group(2),
                path=migration_path,
                sql=raw.decode("utf-8"),
                sha256=hashlib.sha256(raw).hexdigest(),
            )
        )
    if not migrations:
        raise ValueError(f"no migrations found in {directory}")
    return sorted(migrations, key=lambda migration: migration.version)


def plan_migrations(
    migrations: list[Migration], applied: dict[int, str]
) -> list[Migration]:
    pending = []
    for migration in migrations:
        existing = applied.get(migration.version)
        if existing is None:
            pending.append(migration)
        elif existing != migration.sha256:
            raise MigrationDriftError(
                f"migration {migration.version:04d} checksum drift"
            )
    unknown = set(applied) - {migration.version for migration in migrations}
    if unknown:
        raise MigrationDriftError(f"database has unknown migrations: {sorted(unknown)}")
    return pending


def get_applied_migrations(connection) -> dict[int, str]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('energy_analytics.schema_migrations')")
        if cursor.fetchone()[0] is None:
            return {}
        cursor.execute(
            "SELECT version, sha256 FROM energy_analytics.schema_migrations"
        )
        return {int(version): sha256 for version, sha256 in cursor.fetchall()}


def apply_migrations(connection, pending: list[Migration]) -> list[int]:
    if not pending:
        return []
    try:
        with connection.cursor() as cursor:
            for migration in pending:
                cursor.execute(migration.sql)
                cursor.execute(
                    """INSERT INTO energy_analytics.schema_migrations
                       (version, name, sha256) VALUES (%s, %s, %s)""",
                    (migration.version, migration.name, migration.sha256),
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return [migration.version for migration in pending]


def load_verified_backup_manifest(
    path: str | Path, expected_database: str
) -> dict[str, object]:
    try:
        payload = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupGateError(f"cannot load verified backup manifest: {exc}") from exc
    required = {
        "version",
        "database",
        "status",
        "archive_sha256",
        "archive_path",
    }
    if not isinstance(payload, dict) or required - set(payload):
        raise BackupGateError("backup manifest is incomplete")
    if payload["version"] != 1 or payload["database"] != expected_database:
        raise BackupGateError("backup manifest database/version mismatch")
    if payload["status"] != "restore_verified":
        raise BackupGateError("backup restore has not been verified")
    archive_path = Path(str(payload["archive_path"]))
    if not archive_path.is_absolute() or not archive_path.is_file():
        raise BackupGateError("backup archive path is unavailable")
    expected_sha = str(payload["archive_sha256"])
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        raise BackupGateError("backup archive checksum is invalid")
    digest = hashlib.sha256()
    with archive_path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected_sha:
        raise BackupGateError("backup archive checksum mismatch")
    return payload
