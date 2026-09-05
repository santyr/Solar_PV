# Advisory Record Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist immutable advisory decisions and publication/notification results with strict validation, bounded operations, and explicit retry semantics.

**Architecture:** Solar_PV owns two append-only tables in `energy_analytics` and a small explicit-DSN adapter. The adapter reconstructs each input through earthship-ui's existing pure wire builders and compares the complete canonical JSON, then inserts transactionally; a second statement compares the stored payload after a concurrent conflict. No capture integration or assessment is activated.

**Tech Stack:** Python >=3.12, existing psycopg2>=2.9, PostgreSQL 16, pytest, local Docker `postgres:16` with `--pull=never`.

## Global Constraints

- Approved specification: `/home/sat/earthship-ui/docs/superpowers/specs/2026-09-05-advisory-outcomes-design.md`.
- Work only in `/home/sat/earthship-ui/.worktrees/advisory-outcome-storage`, Solar_PV base `9565f8f`; inspect status before editing and preserve unrelated work.
- Earthship-ui owns the forecast script's capture integration and pure record builders. Solar_PV owns new energy_analytics tables, migrations, bounded reads, outcome assessment, and report generation.
- Production migrations and activation require an attended release approval after tests and review; this design is not that deployment approval.
- No Thompson sampling, exploratory advice, conformal interval publication, new notification, or automatic actuation is introduced.
- Never replay notifications or advisory writes to repair an observational record.
- Migration belongs to an explicit deployment step, never an import-time or startup action.
- Use the reviewed `advisory_records.py` and `advisory_windows.py` in the foundation worktree unchanged; do not duplicate their builders, derive policy, or add package startup I/O.
- Bounds: encoded input and canonical payload each <=16 KiB UTF-8; connect timeout 3 seconds; statement timeout 2 seconds; lock timeout 1 second; one fresh connection per operation, always closed.
- No production DSN discovery, role changes, migrations, service/config changes, or OpenHAB writes in this task. No notifier or OpenHAB imports.
- Runtime privilege contract is schema USAGE and INSERT+SELECT on the two new tables only. A separately approved deployment establishes the runtime role; this migration does not create roles or grant existing roles new rights.
- New evidence is append-only, including protection against UPDATE, DELETE, and TRUNCATE. Rollback preserves evidence.
- Full outcome revisions, measurement assessment, canonical nightly selection, forecast capture integration, and activation remain separate required work; this task does not complete the parent scope or ML tasks 16/18.

---

## File map and installation boundary

Create `analytics/sql/migrations/0002_advisory_records.sql` for schema only, `analytics/src/earthship_energy/advisory_store.py` for strict decoding and atomic storage, `analytics/tests/advisory_db_fixture.py` for disposable database ownership, and `analytics/tests/test_advisory_store.py` for the acceptance tests below. No existing Python module or migration needs modification.

The existing migration owner remains `earthship_energy.migrations.discover_migrations`, `plan_migrations`, and `apply_migrations`. Its checksum ledger discovers 0002 automatically. The test fixture uses that owner explicitly only in its generated disposable database. Do not run the production migration CLI during implementation.

Development import command, from the storage worktree:

```bash
PYTHONPATH=/home/sat/earthship-ui/openhab/scripts:$PWD/analytics/src python3 -m pytest analytics/tests -q
```

During a later attended release, install the reviewed shared modules beside the installed forecast script and explicitly include that directory in the consuming Python path; install the Solar_PV analytics package separately. Do not copy builders into Solar_PV or import the forecast script itself. Deploy schema/dependencies and verify least privileges before enabling the later default-off producer adapter. This plan supplies no activation command.

Current repository evidence: 0001 defines `system_epochs(epoch_id text PRIMARY KEY)`; migration files and owner match that shape. The historical 2026-08-20 architecture inventory predates the schema and is not a current schema claim. Coordinator read-only verification found only migration 0001 applied, the new tables absent, and epoch `discover_4_module_2026` present. Tests create their own epoch and never query that production instance.

### Task 3: Strict append-only advisory decision/result storage

**Files:**

- Create: `analytics/sql/migrations/0002_advisory_records.sql`
- Create: `analytics/src/earthship_energy/advisory_store.py`
- Create: `analytics/tests/advisory_db_fixture.py`
- Test: `analytics/tests/test_advisory_store.py`

**Interfaces:**

- Consumes existing shared `build_decision_record(*, decision_id, issued_at, site_timezone, source_revision, policy_version, bank_epoch, prediction_day, advisory, inputs, thresholds, notification_eligible, notification_suppressed) -> str` and `build_result_record(*, result_id, decision_id, observed_at, kind, target, status) -> str`.
- Produces `AdvisoryStore(dsn: str)`, `put_decision(encoded: str) -> bool`, and `put_result(encoded: str) -> bool`. True means committed insert; False means identical semantic canonical payload already persisted. JSON whitespace/key order are irrelevant; changes to any canonical value conflict. Numeric int/float spelling is normalized by builders only when the supplied record already matches builder semantics.
- Produces `InvalidAdvisoryRecord(ValueError)` for malformed wire records; `AdvisoryConflictError(RuntimeError)` for a reused identity with different content; `AdvisoryStorageError(RuntimeError)` for database/reference/timeout failures. All messages are constant, with suppressed raw exception chaining.
- Missing parent/epoch and result timestamps earlier than the parent's issue time reject transactionally; equality of timestamps is valid. Result observation time remains the actual recorded observation, not insertion time.
- Explicit DSN requires one numeric loopback host and explicit port/database/user/password; no service files, JDBC config discovery, environment-derived fallback, DNS, multi-host failover, or caller-supplied timeout options. Only those five fields are accepted. The adapter fixes `hostaddr` to the same numeric host and disables SSL for this loopback-only contract. Nonempty ambient `PGSERVICE` or `PGSERVICEFILE` is rejected in the constructor and immediately before each connection attempt with constant `AdvisoryStorageError("ambient advisory service configuration forbidden")`; no database call occurs. Secrets stay inside connection configuration and never enter exceptions or logs.

- [ ] **Step 1: Add the disposable PostgreSQL fixture.**

Create `analytics/tests/advisory_db_fixture.py` with this complete content. Docker absence/image absence is a hard failure for this integration suite, not a skipped passing test. Only the exact generated container is cleaned up; cleanup does not inspect or remove any other container. Secrets are generated in memory and passed via subprocess environment names, never argv or printed output.

```python
"""Disposable-only PostgreSQL fixture: no external DSN input or fallback."""
from contextlib import closing
from dataclasses import dataclass
import os
import secrets
import subprocess
import time
from types import SimpleNamespace
from uuid import uuid4

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import make_dsn
import pytest

from earthship_energy.migrations import (
    apply_migrations, discover_migrations, get_applied_migrations, plan_migrations,
)


@dataclass(frozen=True)
class FixtureEndpoint:
    host: str
    port: int
    dbname: str
    user: str
    password: str

    @property
    def dsn(self):
        return make_dsn(
            host=self.host, port=self.port, dbname=self.dbname,
            user=self.user, password=self.password,
        )

    def connect(self, *, connect_timeout=3):
        if os.environ.get("PGSERVICE") or os.environ.get("PGSERVICEFILE"):
            raise RuntimeError("unsafe disposable database environment")
        return psycopg2.connect(
            host=self.host, hostaddr=self.host, port=self.port,
            dbname=self.dbname, user=self.user, password=self.password,
            connect_timeout=connect_timeout, sslmode="disable",
        )


def docker(args, env=None):
    result = subprocess.run(
        ["docker", *args], env=env, capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        raise RuntimeError("disposable advisory database command failed")
    return result.stdout.strip()


@pytest.fixture(scope="module")
def advisory_db():
    name = "advisory-test-" + uuid4().hex
    owner_password = secrets.token_hex(24)
    writer_password = secrets.token_hex(24)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("PG")}
    env.update(POSTGRES_PASSWORD=owner_password, POSTGRES_DB="advisory_test")
    created = False
    try:
        docker(["image", "inspect", "postgres:16"])
        docker(["create", "--pull=never", "--name", name,
                "--publish", "127.0.0.1::5432", "--env", "POSTGRES_PASSWORD",
                "--env", "POSTGRES_DB", "postgres:16"], env=env)
        created = True
        docker(["start", name])
        binding = docker(["port", name, "5432/tcp"])
        assert binding.startswith("127.0.0.1:") and "\n" not in binding
        port = int(binding.rsplit(":", 1)[1])
        owner = FixtureEndpoint(
            host="127.0.0.1", port=port, dbname="advisory_test",
            user="postgres", password=owner_password,
        )
        deadline = time.monotonic() + 30
        while True:
            try:
                connection = owner.connect(connect_timeout=1)
                break
            except psycopg2.Error:
                if time.monotonic() >= deadline:
                    raise RuntimeError("disposable advisory database not ready") from None
                time.sleep(0.1)
        with closing(connection), connection:
            pending = plan_migrations(discover_migrations(),
                                      get_applied_migrations(connection))
            assert [m.version for m in pending] == [1, 2]
            assert apply_migrations(connection, pending) == [1, 2]
            with connection.cursor() as cursor:
                cursor.execute("""INSERT INTO energy_analytics.system_epochs
                    (epoch_id, current_analytics) VALUES ('test_bank', true)""")
                cursor.execute(sql.SQL("CREATE ROLE advisory_writer LOGIN PASSWORD {}")
                               .format(sql.Literal(writer_password)))
                cursor.execute("GRANT USAGE ON SCHEMA energy_analytics TO advisory_writer")
                cursor.execute("""GRANT INSERT, SELECT ON
                    energy_analytics.advisory_decisions,
                    energy_analytics.advisory_results TO advisory_writer""")
        writer = FixtureEndpoint(
            host="127.0.0.1", port=port, dbname="advisory_test",
            user="advisory_writer", password=writer_password,
        )
        yield SimpleNamespace(
            host=owner.host, port=owner.port, dbname=owner.dbname,
            owner_user=owner.user, owner_password=owner.password,
            writer_user=writer.user, writer_password=writer.password,
            owner=owner.dsn, writer=writer.dsn,
            connect_owner=owner.connect, connect_writer=writer.connect,
        )
    finally:
        if created:
            docker(["rm", "--force", name])
```

- [ ] **Step 2: Add focused failing tests.**

Create `analytics/tests/test_advisory_store.py` with this complete content:

```python
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date, datetime, timezone
import importlib
import json
import time
from uuid import uuid4

import psycopg2
from psycopg2 import sql
import pytest

from advisory_records import build_decision_record, build_result_record
import advisory_db_fixture as db_fixture
from advisory_db_fixture import FixtureEndpoint, advisory_db
from earthship_energy import advisory_store as module
from earthship_energy.advisory_store import (
    AdvisoryStore, AdvisoryConflictError, AdvisoryStorageError, InvalidAdvisoryRecord,
)


def decision(**changes):
    args = dict(
        decision_id=uuid4(), issued_at=datetime(2026, 9, 5, 12, 40, tzinfo=timezone.utc),
        site_timezone="America/Denver", source_revision="test-rev",
        policy_version="test-v1", bank_epoch="test_bank", prediction_day=date(2026, 9, 5),
        advisory="none", notification_eligible=False, notification_suppressed=False,
        inputs=dict(weather_today_high_raw_f=80, weather_today_low_raw_f=50,
                    tomorrow_high_raw_f=81, tomorrow_low_raw_f=51,
                    tomorrow_high_corrected_f=82, tomorrow_low_corrected_f=52,
                    high_bias_f=1, low_bias_f=1, next_three_highs_raw_f=[81, 82, 83],
                    three_day_high_mean_corrected_f=83, pv_today_kwh=20,
                    trough_tomorrow_pct=65),
        thresholds=dict(close_up_high_f=82, close_up_streak_f=80,
                        vent_high_f=75, trough_dm_pct=40),
    )
    args.update(changes)
    return build_decision_record(**args)


def result(parent, **changes):
    args = dict(result_id=uuid4(), decision_id=json.loads(parent)["decision_id"],
                observed_at=datetime(2026, 9, 5, 12, 40, tzinfo=timezone.utc),
                kind="publication", target="Predicted_SoC_Trough_Tomorrow",
                status="accepted")
    args.update(changes)
    return build_result_record(**args)


def changed(encoded, **changes):
    payload = json.loads(encoded)
    payload.update(changes)
    return json.dumps(payload)


def test_round_trip_and_retries(advisory_db):
    store = AdvisoryStore(advisory_db.writer)
    origin = decision()
    observed = result(origin)
    assert store.put_decision(origin) is True
    assert store.put_decision(json.dumps(json.loads(origin), indent=2)) is False
    assert store.put_result(observed) is True
    assert store.put_result(observed) is False
    with pytest.raises(AdvisoryConflictError, match="advisory identity conflict"):
        store.put_decision(changed(origin, advisory="vent_tonight"))
    with pytest.raises(AdvisoryConflictError, match="advisory identity conflict"):
        store.put_result(changed(observed, status="failed"))
    with closing(advisory_db.connect_writer()) as connection:
        with connection.cursor() as cursor:
            for table, key, encoded in [
                ("advisory_decisions", "decision_id", origin),
                ("advisory_results", "result_id", observed),
            ]:
                payload = json.loads(encoded)
                cursor.execute(sql.SQL("SELECT payload FROM energy_analytics.{} WHERE {}=%s")
                               .format(sql.Identifier(table), sql.Identifier(key)),
                               (payload[key],))
                assert cursor.fetchone()[0] == payload


def test_references_and_chronology(advisory_db):
    store = AdvisoryStore(advisory_db.writer)
    origin = decision()
    with pytest.raises(AdvisoryStorageError):
        store.put_result(result(origin))
    with pytest.raises(AdvisoryStorageError):
        store.put_decision(decision(bank_epoch="missing_bank"))
    assert store.put_decision(origin)
    with pytest.raises(AdvisoryStorageError):
        store.put_result(result(origin, observed_at=datetime(2026, 9, 5, 12, 39,
                                                            tzinfo=timezone.utc)))
    assert store.put_result(result(origin))


def test_concurrent_identical_and_conflicting_retries(advisory_db):
    origin = decision()
    stores = [AdvisoryStore(advisory_db.writer) for _ in range(6)]

    def put_with(store, payload, kind):
        put = store.put_decision if kind == "decision" else store.put_result
        try:
            return put(payload)
        except AdvisoryStorageError:
            return "bounded-storage-error"

    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(
            lambda store: put_with(store, origin, "decision"), stores,
        ))
        assert outcomes.count(True) == 1
        assert set(outcomes) <= {True, False, "bounded-storage-error"}
        assert AdvisoryStore(advisory_db.writer).put_decision(origin) is False
        observed = result(origin)
        outcomes = list(pool.map(
            lambda store: put_with(store, observed, "result"), stores,
        ))
        assert outcomes.count(True) == 1
        assert set(outcomes) <= {True, False, "bounded-storage-error"}
        assert AdvisoryStore(advisory_db.writer).put_result(observed) is False
    for kind in ("decision", "result"):
        original = decision() if kind == "decision" else result(origin)
        alternative = changed(original, **({"advisory": "vent_tonight"}
                                           if kind == "decision" else {"status": "failed"}))
        def attempt(store, payload):
            put = store.put_decision if kind == "decision" else store.put_result
            try:
                return put(payload)
            except AdvisoryConflictError:
                return "conflict"
            except AdvisoryStorageError:
                return "bounded-storage-error"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(
                attempt,
                [AdvisoryStore(advisory_db.writer), AdvisoryStore(advisory_db.writer)],
                [original, alternative],
            ))
        assert outcomes.count(True) == 1
        assert set(outcomes) <= {True, "conflict", "bounded-storage-error"}
        settled = []
        for payload in (original, alternative):
            put = (AdvisoryStore(advisory_db.writer).put_decision if kind == "decision"
                   else AdvisoryStore(advisory_db.writer).put_result)
            try:
                settled.append(put(payload))
            except AdvisoryConflictError:
                settled.append("conflict")
        assert settled.count(False) == settled.count("conflict") == 1


@pytest.mark.parametrize("variable", ["PGSERVICE", "PGSERVICEFILE"])
def test_fixture_endpoint_rejects_unsafe_ambient_configuration_before_connect(
        variable, monkeypatch):
    endpoint = FixtureEndpoint(
        host="127.0.0.1", port=15432, dbname="generated_db",
        user="generated_user", password="generated_password",
    )
    monkeypatch.setenv(variable, "unsafe-ambient-value")
    def forbidden(*args, **kwargs):
        pytest.fail("unsafe fixture environment attempted a database connection")
    monkeypatch.setattr(db_fixture.psycopg2, "connect", forbidden)
    with pytest.raises(RuntimeError, match="unsafe disposable database environment"):
        endpoint.connect(connect_timeout=1)


def test_fixture_connections_pin_the_generated_endpoint(advisory_db, monkeypatch):
    real_connect = psycopg2.connect
    calls = []
    def tracked(*args, **kwargs):
        calls.append((args, kwargs))
        return real_connect(*args, **kwargs)
    monkeypatch.setattr(db_fixture.psycopg2, "connect", tracked)
    with closing(advisory_db.connect_owner()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            assert cursor.fetchone() == (advisory_db.dbname, advisory_db.owner_user)
    assert calls[0][0] == ()
    assert calls[0][1] == {
        "host": advisory_db.host, "hostaddr": advisory_db.host,
        "port": advisory_db.port, "dbname": advisory_db.dbname,
        "user": advisory_db.owner_user, "password": advisory_db.owner_password,
        "connect_timeout": 3, "sslmode": "disable",
    }


def test_same_record_contention_is_bounded_and_retry_compares_committed_winner(advisory_db):
    origin = decision()
    payload = json.loads(origin)
    with closing(advisory_db.connect_writer()) as winner:
        with winner.cursor() as cursor:
            cursor.execute(
                """INSERT INTO energy_analytics.advisory_decisions
                   (decision_id, issued_at, bank_epoch, payload)
                   VALUES (%s, %s, %s, %s::jsonb)""",
                (payload["decision_id"], payload["issued_at"], payload["bank_epoch"], origin),
            )
        started = time.monotonic()
        with pytest.raises(AdvisoryStorageError) as caught:
            AdvisoryStore(advisory_db.writer).put_decision(origin)
        assert str(caught.value) == "advisory storage unavailable"
        assert 0.7 <= time.monotonic() - started < 4
        winner.commit()
    assert AdvisoryStore(advisory_db.writer).put_decision(origin) is False


def test_fixture_endpoint_pins_hostaddr_over_ambient_value(monkeypatch):
    endpoint = FixtureEndpoint(
        host="127.0.0.1", port=15432, dbname="generated_db",
        user="generated_user", password="generated_password",
    )
    calls = []
    monkeypatch.setenv("PGHOSTADDR", "192.0.2.1")
    monkeypatch.setattr(
        db_fixture.psycopg2, "connect",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    endpoint.connect(connect_timeout=1)
    assert calls[0][0] == ()
    assert calls[0][1]["host"] == calls[0][1]["hostaddr"] == "127.0.0.1"


@pytest.mark.parametrize("kind", ["decision", "result"])
def test_strict_validation_precedes_connection(kind, monkeypatch):
    origin = decision()
    encoded = origin if kind == "decision" else result(origin)
    payload = json.loads(encoded)
    bad = [None, b"{}", "[]", "null", "{", " " * 16385,
           encoded[:-1] + ',"schema_version":1}',
           changed(encoded, schema_version=True), changed(encoded, schema_version=1.0),
           changed(encoded, schema_version=2), changed(encoded, extra="secret"),
           changed(encoded, decision_id="broken"),
           changed(encoded, record_type="wrong")]
    for field in payload:
        missing = dict(payload)
        missing.pop(field)
        bad.append(json.dumps(missing))
    if kind == "decision":
        for value in (True, float("nan"), float("inf"), "12", None):
            inputs = dict(payload["inputs"], pv_today_kwh=value)
            bad.append(changed(encoded, inputs=inputs))
        bad.extend([changed(encoded, issued_at="2026-09-05T12:40:00"),
                    changed(encoded, site_timezone="Not/A_Zone"),
                    changed(encoded, targets={}),
                    changed(encoded, notification={"eligible": False,
                                                   "suppressed": False, "extra": 1})])
        bad.append(encoded.replace('"pv_today_kwh":20.0',
                                   '"pv_today_kwh":20.0,"pv_today_kwh":20.0'))
        bad.append(encoded.replace('"pv_today_kwh":20.0', '"pv_today_kwh":1e999'))
    else:
        bad.extend([changed(encoded, observed_at="2026-09-05T12:40:00"),
                    changed(encoded, status="delivered"),
                    changed(encoded, target="actuator"), changed(encoded, kind="action")])
    def forbidden(*args, **kwargs):
        pytest.fail("invalid record attempted connection")
    monkeypatch.setattr(module.psycopg2, "connect", forbidden)
    store = AdvisoryStore("host=127.0.0.1 port=1 dbname=test user=test password=test")
    put = store.put_decision if kind == "decision" else store.put_result
    for value in bad:
        with pytest.raises(InvalidAdvisoryRecord, match="invalid advisory record"):
            put(value)


def test_import_constructor_and_explicit_dsn(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("import/constructor attempted database connection")
    monkeypatch.setattr(module.psycopg2, "connect", forbidden)
    importlib.reload(module)
    # Reload changes class identities; refer to the module here and restore
    # the test module aliases so subsequent exception checks use current classes.
    globals().update({name: getattr(module, name) for name in (
        "AdvisoryStore", "AdvisoryConflictError", "AdvisoryStorageError",
        "InvalidAdvisoryRecord")})
    module.AdvisoryStore("host=127.0.0.1 port=1 dbname=test user=test password=test")
    for dsn in (None, "", "dbname=test", "service=production",
                "host=localhost port=1 dbname=t user=u password=p",
                "host=192.0.2.1 port=1 dbname=t user=u password=p",
                "host=a,b port=1 dbname=t user=u password=p",
                "host=a port=1 dbname=t user=u password=p options='-c statement_timeout=0'"):
        with pytest.raises(ValueError, match="explicit advisory DSN required"):
            module.AdvisoryStore(dsn)


@pytest.mark.parametrize("table", ["advisory_decisions", "advisory_results"])
@pytest.mark.parametrize("verb", ["UPDATE", "DELETE", "TRUNCATE"])
def test_runtime_cannot_mutate(advisory_db, table, verb):
    statement = {"UPDATE": "UPDATE energy_analytics.{} SET payload=payload",
                 "DELETE": "DELETE FROM energy_analytics.{}",
                 "TRUNCATE": "TRUNCATE energy_analytics.{}"}[verb]
    for connect in (advisory_db.connect_writer, advisory_db.connect_owner):
        with closing(connect()) as connection:
            with connection.cursor() as cursor:
                with pytest.raises(psycopg2.Error):
                    cursor.execute(sql.SQL(statement).format(sql.Identifier(table)))


def test_runtime_privileges_are_minimal(advisory_db):
    with closing(advisory_db.connect_writer()) as connection:
        with connection.cursor() as cursor:
            for table in ("advisory_decisions", "advisory_results"):
                for privilege in ("INSERT", "SELECT", "UPDATE", "DELETE", "TRUNCATE",
                                  "REFERENCES", "TRIGGER"):
                    cursor.execute("SELECT has_table_privilege(current_user, %s, %s)",
                                   ("energy_analytics." + table, privilege))
                    assert cursor.fetchone()[0] == (privilege in {"INSERT", "SELECT"})
            cursor.execute("SELECT has_table_privilege(current_user, %s, 'SELECT')",
                           ("energy_analytics.system_epochs",))
            assert cursor.fetchone()[0] is False
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cursor.execute("CREATE TABLE energy_analytics.forbidden (id int)")


def test_connections_closed_and_settings_fixed(advisory_db, monkeypatch):
    real_connect = psycopg2.connect
    connections, calls = [], []
    def tracked(*args, **kwargs):
        calls.append(kwargs)
        connection = real_connect(*args, **kwargs)
        connections.append(connection)
        with connection.cursor() as cursor:
            for name, expected in (("statement_timeout", "2s"), ("lock_timeout", "1s")):
                cursor.execute(sql.SQL("SHOW {}").format(sql.Identifier(name)))
                assert cursor.fetchone()[0] == expected
        connection.rollback()
        return connection
    monkeypatch.setattr(module.psycopg2, "connect", tracked)
    store = AdvisoryStore(advisory_db.writer)
    origin = decision()
    store.put_decision(origin)
    store.put_decision(origin)
    with pytest.raises(AdvisoryConflictError):
        store.put_decision(changed(origin, advisory="vent_tonight"))
    with pytest.raises(AdvisoryStorageError):
        store.put_decision(decision(bank_epoch="absent"))
    assert len(connections) == 4 and all(connection.closed for connection in connections)
    assert all(call["connect_timeout"] == 3 for call in calls)


def test_ambient_connection_overrides_cannot_redirect(advisory_db, monkeypatch):
    monkeypatch.setenv("PGHOSTADDR", "192.0.2.1")
    monkeypatch.setenv("PGHOST", "unrelated.invalid")
    monkeypatch.setenv("PGPORT", "1")
    monkeypatch.setenv("PGDATABASE", "unrelated")
    monkeypatch.setenv("PGUSER", "unrelated")
    monkeypatch.setenv("PGPASSWORD", "unrelated")
    monkeypatch.setenv("PGOPTIONS", "-c statement_timeout=0")
    assert AdvisoryStore(advisory_db.writer).put_decision(decision())


@pytest.mark.parametrize("variable", ["PGSERVICE", "PGSERVICEFILE"])
def test_ambient_service_configuration_rejected_without_connection(variable, monkeypatch):
    # Unit-test isolation only: production code never edits process environment.
    monkeypatch.delenv("PGSERVICE", raising=False)
    monkeypatch.delenv("PGSERVICEFILE", raising=False)
    def forbidden(*args, **kwargs):
        pytest.fail("ambient service configuration attempted connection")
    monkeypatch.setattr(module.psycopg2, "connect", forbidden)
    dsn = "host=127.0.0.1 port=1 dbname=test user=test password=test"
    store = AdvisoryStore(dsn)
    monkeypatch.setenv(variable, "private-service-configuration")
    for operation in (lambda: AdvisoryStore(dsn),
                      lambda: store.put_decision(decision()),
                      lambda: store.put_result(result(decision()))):
        with pytest.raises(AdvisoryStorageError) as caught:
            operation()
        assert str(caught.value) == "ambient advisory service configuration forbidden"


@pytest.mark.parametrize("table,field", [
    ("advisory_decisions", "decision_id"), ("advisory_decisions", "issued_at"),
    ("advisory_decisions", "bank_epoch"), ("advisory_results", "result_id"),
    ("advisory_results", "decision_id"), ("advisory_results", "observed_at"),
])
@pytest.mark.parametrize("null_value", [False, True])
def test_direct_sql_rejects_missing_or_null_identity(advisory_db, table, field, null_value):
    origin = decision()
    AdvisoryStore(advisory_db.writer).put_decision(origin)
    parent = json.loads(origin)
    payload = json.loads(decision() if table == "advisory_decisions" else result(origin))
    original = dict(payload)
    if null_value:
        payload[field] = None
    else:
        payload.pop(field)
    if table == "advisory_decisions":
        statement = """INSERT INTO energy_analytics.advisory_decisions
            (decision_id, issued_at, bank_epoch, payload) VALUES (%s, %s, %s, %s::jsonb)"""
        parameters = (original["decision_id"], original["issued_at"],
                      original["bank_epoch"], json.dumps(payload))
    else:
        statement = """INSERT INTO energy_analytics.advisory_results
            (result_id, decision_id, parent_issued_at, observed_at, payload)
            VALUES (%s, %s, %s, %s, %s::jsonb)"""
        parameters = (original["result_id"], original["decision_id"], parent["issued_at"],
                      original["observed_at"], json.dumps(payload))
    with closing(advisory_db.connect_writer()) as connection:
        with connection.cursor() as cursor:
            with pytest.raises(psycopg2.errors.CheckViolation):
                cursor.execute(statement, parameters)


def test_real_lock_timeout_and_cleanup(advisory_db, monkeypatch):
    real_connect = psycopg2.connect
    captured = []
    with closing(advisory_db.connect_owner()) as blocker:
        with blocker.cursor() as cursor:
            cursor.execute("LOCK energy_analytics.advisory_decisions IN ACCESS EXCLUSIVE MODE")
        def tracked(*args, **kwargs):
            connection = real_connect(*args, **kwargs)
            captured.append(connection)
            return connection
        monkeypatch.setattr(module.psycopg2, "connect", tracked)
        started = time.monotonic()
        with pytest.raises(AdvisoryStorageError, match="advisory storage unavailable"):
            AdvisoryStore(advisory_db.writer).put_decision(decision())
        assert 0.7 <= time.monotonic() - started < 4
        assert captured and all(connection.closed for connection in captured)
        blocker.rollback()


def test_real_statement_timeout_and_cleanup(advisory_db, monkeypatch):
    real_connect = psycopg2.connect
    with closing(advisory_db.connect_owner()) as setup, setup:
        with setup.cursor() as cursor:
            cursor.execute("""CREATE FUNCTION energy_analytics.test_delay() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN PERFORM pg_sleep(4); RETURN NEW; END $$""")
            cursor.execute("""CREATE TRIGGER test_delay BEFORE INSERT ON
                energy_analytics.advisory_decisions FOR EACH ROW
                EXECUTE FUNCTION energy_analytics.test_delay()""")
    captured = []
    def tracked(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        captured.append(connection)
        return connection
    monkeypatch.setattr(module.psycopg2, "connect", tracked)
    try:
        started = time.monotonic()
        with pytest.raises(AdvisoryStorageError, match="advisory storage unavailable"):
            AdvisoryStore(advisory_db.writer).put_decision(decision())
        assert 1.7 <= time.monotonic() - started < 4
        assert captured and all(connection.closed for connection in captured)
    finally:
        with closing(advisory_db.connect_owner()) as connection, connection:
            with connection.cursor() as cursor:
                cursor.execute("DROP TRIGGER test_delay ON energy_analytics.advisory_decisions")
                cursor.execute("DROP FUNCTION energy_analytics.test_delay()")


def test_connection_errors_are_sanitized(monkeypatch):
    def broken(*args, **kwargs):
        raise psycopg2.OperationalError("password=do-not-log host=private-host")
    monkeypatch.setattr(module.psycopg2, "connect", broken)
    with pytest.raises(AdvisoryStorageError) as caught:
        AdvisoryStore("host=127.0.0.1 port=1 dbname=test user=test password=test").put_decision(decision())
    assert str(caught.value) == "advisory storage unavailable"
    assert caught.value.__suppress_context__
```

- [ ] **Step 3: Run the new tests to establish the red result.**

```bash
PYTHONPATH=/home/sat/earthship-ui/openhab/scripts:$PWD/analytics/src python3 -m pytest analytics/tests/test_advisory_store.py -q
```

Expected: collection fails because `earthship_energy.advisory_store` does not exist. Do not mistake a missing Docker installation or shared-builder import for the intended red result.

- [ ] **Step 4: Add the explicit schema migration.**

Create `analytics/sql/migrations/0002_advisory_records.sql`:

```sql
CREATE TABLE energy_analytics.advisory_decisions (
    decision_id uuid PRIMARY KEY,
    issued_at timestamptz NOT NULL,
    bank_epoch text NOT NULL REFERENCES energy_analytics.system_epochs(epoch_id),
    payload jsonb NOT NULL,
    UNIQUE (decision_id, issued_at),
    CHECK (jsonb_typeof(payload) = 'object'),
    CHECK (octet_length(payload::text) <= 16384),
    CHECK (((payload->>'decision_id')::uuid = decision_id) IS TRUE),
    CHECK (((payload->>'issued_at')::timestamptz = issued_at) IS TRUE),
    CHECK ((payload->>'bank_epoch' = bank_epoch) IS TRUE)
);

CREATE TABLE energy_analytics.advisory_results (
    result_id uuid PRIMARY KEY,
    decision_id uuid NOT NULL,
    parent_issued_at timestamptz NOT NULL,
    observed_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    FOREIGN KEY (decision_id, parent_issued_at)
        REFERENCES energy_analytics.advisory_decisions(decision_id, issued_at),
    CHECK (observed_at >= parent_issued_at),
    CHECK (jsonb_typeof(payload) = 'object'),
    CHECK (octet_length(payload::text) <= 16384),
    CHECK (((payload->>'result_id')::uuid = result_id) IS TRUE),
    CHECK (((payload->>'decision_id')::uuid = decision_id) IS TRUE),
    CHECK (((payload->>'observed_at')::timestamptz = observed_at) IS TRUE)
);

CREATE INDEX advisory_results_decision_idx
    ON energy_analytics.advisory_results(decision_id, observed_at);

CREATE FUNCTION energy_analytics.reject_advisory_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'advisory evidence is append only' USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER advisory_decisions_append_only
    BEFORE UPDATE OR DELETE OR TRUNCATE ON energy_analytics.advisory_decisions
    FOR EACH STATEMENT EXECUTE FUNCTION energy_analytics.reject_advisory_mutation();
CREATE TRIGGER advisory_results_append_only
    BEFORE UPDATE OR DELETE OR TRUNCATE ON energy_analytics.advisory_results
    FOR EACH STATEMENT EXECUTE FUNCTION energy_analytics.reject_advisory_mutation();

REVOKE ALL ON energy_analytics.advisory_decisions,
              energy_analytics.advisory_results FROM PUBLIC;
```

Composite FK and CHECK enforce chronology without UPDATE, privileged trigger reads, or SELECT rights on `system_epochs`. Mutation-denial triggers also protect ordinary owner DML; a schema owner can explicitly change schema, so this is not a claim of superuser-proof storage. Complete strict wire validation is the adapter contract; raw SQL INSERT permission is not an alternate supported wire API.

- [ ] **Step 5: Add the bounded storage adapter.**

Create `analytics/src/earthship_energy/advisory_store.py`:

```python
"""Explicit, bounded, append-only advisory evidence storage."""
from datetime import date, datetime
from ipaddress import ip_address
import json
import os

import psycopg2
from psycopg2.extensions import parse_dsn

from advisory_records import build_decision_record, build_result_record

MAX_BYTES = 16 * 1024


class InvalidAdvisoryRecord(ValueError):
    pass


class AdvisoryConflictError(RuntimeError):
    pass


class AdvisoryStorageError(RuntimeError):
    pass


def _reject_ambient_service():
    if os.environ.get("PGSERVICE") or os.environ.get("PGSERVICEFILE"):
        raise AdvisoryStorageError("ambient advisory service configuration forbidden")


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("nonfinite number")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _decode(encoded, kind):
    try:
        if not isinstance(encoded, str) or len(encoded.encode("utf-8")) > MAX_BYTES:
            raise ValueError("size/type")
        payload = json.loads(encoded, object_pairs_hook=_object, parse_constant=_constant)
        if not isinstance(payload, dict) or type(payload.get("schema_version")) is not int:
            raise ValueError("version")
        if payload["schema_version"] != 1 or payload.get("record_type") != "advisory_" + kind:
            raise ValueError("kind/version")
        if kind == "decision":
            canonical = build_decision_record(
                decision_id=payload["decision_id"],
                issued_at=datetime.fromisoformat(payload["issued_at"]),
                site_timezone=payload["site_timezone"],
                source_revision=payload["source_revision"],
                policy_version=payload["policy_version"], bank_epoch=payload["bank_epoch"],
                prediction_day=date.fromisoformat(payload["prediction_day"]),
                advisory=payload["advisory"], inputs=payload["inputs"],
                thresholds=payload["thresholds"],
                notification_eligible=payload["notification"]["eligible"],
                notification_suppressed=payload["notification"]["suppressed"],
            )
        else:
            canonical = build_result_record(
                result_id=payload["result_id"], decision_id=payload["decision_id"],
                observed_at=datetime.fromisoformat(payload["observed_at"]),
                kind=payload["kind"], target=payload["target"], status=payload["status"],
            )
        # String comparison distinguishes booleans from numbers and rejects
        # extras, forged targets, and noncanonical dates/UUIDs at every level.
        if _canonical(payload) != canonical or len(canonical.encode("utf-8")) > MAX_BYTES:
            raise ValueError("schema mismatch")
        return payload, canonical
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise InvalidAdvisoryRecord("invalid advisory record") from None


class AdvisoryStore:
    def __init__(self, dsn: str):
        _reject_ambient_service()
        try:
            if not isinstance(dsn, str) or not dsn.strip():
                raise ValueError("DSN")
            fields = parse_dsn(dsn)
            required = {"host", "port", "dbname", "user", "password"}
            if set(fields) != required or any(not fields.get(k) for k in required):
                raise ValueError("DSN")
            if not ip_address(fields["host"]).is_loopback or not 1 <= int(fields["port"]) <= 65535:
                raise ValueError("endpoint")
            self._dsn = dsn
            self._hostaddr = fields["host"]
        except (ValueError, TypeError, psycopg2.Error):
            raise ValueError("explicit advisory DSN required") from None

    def put_decision(self, encoded: str) -> bool:
        payload, canonical = _decode(encoded, "decision")
        return self._put(payload, canonical, "decision")

    def put_result(self, encoded: str) -> bool:
        payload, canonical = _decode(encoded, "result")
        return self._put(payload, canonical, "result")

    def _put(self, payload, canonical, kind):
        _reject_ambient_service()
        connection = None
        try:
            connection = psycopg2.connect(
                self._dsn, connect_timeout=3,
                hostaddr=self._hostaddr, sslmode="disable",
                options="-c statement_timeout=2000 -c lock_timeout=1000 "
                        "-c idle_in_transaction_session_timeout=5000",
            )
            # Explicit READ COMMITTED gives the retry comparison a fresh
            # snapshot after INSERT waits on another transaction's unique key.
            connection.set_session(isolation_level="READ COMMITTED", autocommit=False)
            with connection:
                with connection.cursor() as cursor:
                    if kind == "decision":
                        cursor.execute("""INSERT INTO energy_analytics.advisory_decisions
                            (decision_id, issued_at, bank_epoch, payload)
                            VALUES (%s, %s, %s, %s::jsonb)
                            ON CONFLICT (decision_id) DO NOTHING RETURNING decision_id""",
                            (payload["decision_id"], payload["issued_at"],
                             payload["bank_epoch"], canonical))
                        lookup = """SELECT payload = %s::jsonb FROM
                            energy_analytics.advisory_decisions WHERE decision_id = %s"""
                        identity = payload["decision_id"]
                    else:
                        cursor.execute("""INSERT INTO energy_analytics.advisory_results
                            (result_id, decision_id, parent_issued_at, observed_at, payload)
                            SELECT %s, decision_id, issued_at, %s, %s::jsonb
                            FROM energy_analytics.advisory_decisions WHERE decision_id = %s
                            ON CONFLICT (result_id) DO NOTHING RETURNING result_id""",
                            (payload["result_id"], payload["observed_at"], canonical,
                             payload["decision_id"]))
                        lookup = """SELECT payload = %s::jsonb FROM
                            energy_analytics.advisory_results WHERE result_id = %s"""
                        identity = payload["result_id"]
                    if cursor.fetchone() is not None:
                        inserted = True
                    else:
                        cursor.execute(lookup, (canonical, identity))
                        existing = cursor.fetchone()
                        if existing is None:
                            raise AdvisoryStorageError("advisory storage unavailable")
                        if not existing[0]:
                            raise AdvisoryConflictError("advisory identity conflict")
                        inserted = False
            return inserted
        except psycopg2.Error:
            raise AdvisoryStorageError("advisory storage unavailable") from None
        finally:
            if connection is not None:
                connection.close()
```

`ON CONFLICT DO NOTHING` never requires UPDATE privileges. Compare full JSONB, not a digest, in a separate READ COMMITTED statement: a same-statement snapshot cannot reliably see the concurrent winner. A result for an uncommitted/missing parent is an explicit storage failure; the caller can retry the same result after the parent commits, with no side-effect replay. All retry operations have fixed query counts and no internal retry loop. Database statement/lock bounds are per statement; the fresh-connection operation can include connection establishment plus up to two bounded statements and commit. Explicit numeric loopback host/hostaddr prevents DNS resolution and ambient `PGHOSTADDR` redirection. Integration tests verify explicit host/database/user/timeout overrides; separate unit tests verify ambient service configuration rejects without a connection, both at construction and after construction for each write method.

Review correction: libpq can consult ambient `PGSERVICE`/`PGSERVICEFILE` despite a `service=''` keyword, so an empty service argument does not suppress fallback. Fail closed on either nonempty variable instead of editing global environment, introducing subprocesses, or generating service/credential files. The check and libpq environment read are not atomic: a foreign thread or native extension mutating these process variables during connection setup can race the guard. Deployment must keep process environment fixed for the adapter's lifetime; this small in-process adapter cannot guarantee isolation from concurrent foreign environment mutation. Calls made after a variable changes are checked again and reject. No suppression guarantee under such concurrent mutation is claimed.

Approved correction (2026-09-05): fixture-owned owner/writer connections use generated endpoint objects that pass numeric loopback as both `host` and `hostaddr`, plus explicit generated port/database/user/password, and reject ambient `PGSERVICE` or `PGSERVICEFILE` before calling libpq. Concurrent acceptance uses independent `AdvisoryStore` instances. Under unresolved contention a constant sanitized `AdvisoryStorageError` within the fixed timeout is valid; every successful outcome is exactly one `True` plus identical `False` results or a conflicting error, and a caller-controlled same-ID retry after the winner commits must perform the deterministic persisted comparison. No process-local lock, internal retry loop, or unbounded wait is permitted.

- [ ] **Step 6: Run focused and full verification.**

```bash
PYTHONPATH=/home/sat/earthship-ui/openhab/scripts:$PWD/analytics/src python3 -m pytest analytics/tests/test_advisory_store.py -q
PYTHONPATH=/home/sat/earthship-ui/openhab/scripts:$PWD/analytics/src python3 -m pytest analytics/tests -q
git diff --check
git status --short
```

Expected: focused tests all pass against disposable PostgreSQL 16, including generated-endpoint pinning, pre-connect ambient-service rejection, committed idempotency, independent-store uniqueness/conflict behavior, bounded contention failure, and caller-controlled post-commit retry. Full analytics passes all additions, diff check is clean, and only intended files appear. The fixture's `finally` removes its exact generated container on normal test success/failure. If the process is forcibly killed, identify its exact `advisory-test-<uuid>` name from that test invocation before manually removing it; never use a broad Docker prune.

- [ ] **Step 7: Review and commit the independently testable storage increment.**

Inspect the diff against this plan and approved spec; obtain the coordinator's normal spec and code review before accepting the task. Resolve findings, rerun affected tests and the full suite when code changed, and record actual counts. The following commit is an execution-time step, not authorization for this planning worker to commit or deploy:

```bash
git add analytics/sql/migrations/0002_advisory_records.sql analytics/src/earthship_energy/advisory_store.py analytics/tests/advisory_db_fixture.py analytics/tests/test_advisory_store.py docs/superpowers/plans/2026-09-05-advisory-record-storage.md
git commit -m "feat: store immutable advisory decisions and results"
git status --short
```

Hand off the verified commit and test evidence. Do not push, migrate production, grant roles, configure a production DSN, activate capture, or claim completed-night assessment complete as part of this task.
