import hashlib
import json

import pytest

from earthship_energy.migrations import (
    BackupGateError,
    MigrationDriftError,
    apply_migrations,
    discover_migrations,
    load_verified_backup_manifest,
    plan_migrations,
)


def write_migration(path, name, sql):
    target = path / name
    target.write_text(sql)
    return target


def test_discovers_ordered_migrations_with_checksums(tmp_path):
    write_migration(tmp_path, "0002_second.sql", "SELECT 2;")
    first = write_migration(tmp_path, "0001_first.sql", "SELECT 1;")
    migrations = discover_migrations(tmp_path)
    assert [m.version for m in migrations] == [1, 2]
    assert migrations[0].sha256 == hashlib.sha256(first.read_bytes()).hexdigest()


def test_rejects_invalid_or_duplicate_migration_names(tmp_path):
    write_migration(tmp_path, "bad.sql", "SELECT 1;")
    with pytest.raises(ValueError, match="migration filename"):
        discover_migrations(tmp_path)


def test_plan_is_idempotent_and_refuses_checksum_drift(tmp_path):
    write_migration(tmp_path, "0001_first.sql", "SELECT 1;")
    migration = discover_migrations(tmp_path)[0]
    assert plan_migrations([migration], {}) == [migration]
    assert plan_migrations([migration], {1: migration.sha256}) == []
    with pytest.raises(MigrationDriftError, match="checksum drift"):
        plan_migrations([migration], {1: "0" * 64})


def test_verified_backup_manifest_is_mandatory_for_apply(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(BackupGateError):
        load_verified_backup_manifest(missing, expected_database="openhab")
    archive = tmp_path / "openhab.dump"
    archive.write_bytes(b"verified backup fixture")
    manifest = tmp_path / "backup.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "database": "openhab",
                "status": "restore_verified",
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "archive_path": str(archive),
            }
        )
    )
    assert load_verified_backup_manifest(manifest, "openhab")["status"] == "restore_verified"


class FakeCursor:
    def __init__(self, statements):
        self.statements = statements

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.statements.append((sql, params))


class FakeConnection:
    def __init__(self):
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return FakeCursor(self.statements)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_apply_executes_pending_migrations_and_records_checksum(tmp_path):
    write_migration(tmp_path, "0001_first.sql", "CREATE SCHEMA x;")
    pending = discover_migrations(tmp_path)
    connection = FakeConnection()
    applied = apply_migrations(connection, pending)
    assert applied == [1]
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.statements[0] == ("CREATE SCHEMA x;", None)
    assert "schema_migrations" in connection.statements[1][0]
    assert connection.statements[1][1][0] == 1


def test_initial_schema_has_required_tables():
    from earthship_energy.migrations import default_migrations_path

    sql = (default_migrations_path() / "0001_energy_analytics.sql").read_text()
    for table in (
        "metric_sources",
        "system_epochs",
        "snow_events",
        "forecast_snapshots",
        "lynk_import_batches",
        "battery_module_samples",
        "daily_battery",
        "daily_pv",
        "daily_load",
        "daily_weather",
        "daily_source_quality",
        "analysis_runs",
    ):
        assert f"CREATE TABLE energy_analytics.{table}" in sql
