from datetime import timezone

import pytest

from earthship_energy.imports import (
    ImportError,
    fetch_existing_import_hashes,
    persist_lynk_import,
    prepare_lynk_import,
)


CSV = b"""module_id,sampled_at,soc_pct,voltage_v,current_a,temperature_c,cell_spread_mv,charge_kwh,discharge_kwh,faults
module-1,2026-08-20T12:00:00Z,90,52.1,1.2,24.0,8,10,9,
module-2,2026-08-20T12:00:00Z,89,52.0,1.1,24.5,9,10,9,WARN
"""


def test_prepares_typed_checksum_pinned_lynk_import():
    batch = prepare_lynk_import(CSV, "lynk-export.csv", existing_hashes=set())
    assert batch.status == "ready"
    assert len(batch.sha256) == 64
    assert len(batch.rows) == 2
    assert batch.rows[0].sampled_at.tzinfo is timezone.utc
    assert batch.rows[1].faults == ("WARN",)


def test_byte_identical_import_is_idempotent():
    first = prepare_lynk_import(CSV, "lynk-export.csv", existing_hashes=set())
    second = prepare_lynk_import(CSV, "renamed.csv", existing_hashes={first.sha256})
    assert second.status == "duplicate"
    assert second.rows == ()


def test_duplicate_sample_key_or_missing_columns_is_rejected():
    duplicate = CSV + CSV.splitlines(keepends=True)[1]
    with pytest.raises(ImportError, match="duplicate sample"):
        prepare_lynk_import(duplicate, "bad.csv", set())
    with pytest.raises(ImportError, match="columns"):
        prepare_lynk_import(b"module_id,sampled_at\na,2026-01-01T00:00:00Z\n", "bad.csv", set())


class Cursor:
    def __init__(self, hashes=()):
        self.hashes = hashes
        self.executed = []
        self.batch_id = 42

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return [(value,) for value in self.hashes]

    def fetchone(self):
        return (self.batch_id,)


class Connection:
    def __init__(self, hashes=()):
        self.cursor_instance = Cursor(hashes)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_fetches_existing_hashes_and_persists_batch_atomically():
    connection = Connection({"a" * 64})
    assert fetch_existing_import_hashes(connection) == {"a" * 64}
    batch = prepare_lynk_import(CSV, "lynk-export.csv", set())
    result = persist_lynk_import(connection, batch)
    assert result == {"status": "imported", "batch_id": 42, "rows": 2, "sha256": batch.sha256}
    assert connection.commits == 1
    assert connection.rollbacks == 0
    sql = "\n".join(statement for statement, _ in connection.cursor_instance.executed)
    assert "INSERT INTO energy_analytics.lynk_import_batches" in sql
    assert sql.count("INSERT INTO energy_analytics.battery_module_samples") == 2


def test_duplicate_batch_is_a_write_free_success():
    connection = Connection()
    batch = prepare_lynk_import(CSV, "lynk-export.csv", set())
    duplicate = type(batch)(batch.sha256, "renamed.csv", "duplicate", ())
    result = persist_lynk_import(connection, duplicate)
    assert result == {"status": "duplicate", "batch_id": None, "rows": 0, "sha256": batch.sha256}
    assert connection.cursor_instance.executed == []
    assert connection.commits == 0
