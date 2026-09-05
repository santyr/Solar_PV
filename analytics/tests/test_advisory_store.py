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
    with closing(advisory_db.connect_owner()) as owner:
        with owner.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            assert cursor.fetchone() == (advisory_db.dbname, advisory_db.owner_user)
    assert calls == [((), {
        "host": advisory_db.host,
        "hostaddr": advisory_db.host,
        "port": advisory_db.port,
        "dbname": advisory_db.dbname,
        "user": advisory_db.owner_user,
        "password": advisory_db.owner_password,
        "connect_timeout": 3,
        "sslmode": "disable",
    })]


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
        elapsed = time.monotonic() - started
        assert str(caught.value) == "advisory storage unavailable"
        assert 0.7 <= elapsed < 4
        winner.commit()
    assert AdvisoryStore(advisory_db.writer).put_decision(origin) is False


def test_fixture_endpoint_pins_hostaddr_over_ambient_value(monkeypatch):
    endpoint = FixtureEndpoint(
        host="127.0.0.1", port=15432, dbname="generated_db",
        user="generated_user", password="generated_password",
    )
    sentinel = object()
    calls = []
    monkeypatch.setenv("PGHOSTADDR", "192.0.2.1")

    def tracked(*args, **kwargs):
        calls.append((args, kwargs))
        return sentinel

    monkeypatch.setattr(db_fixture.psycopg2, "connect", tracked)
    assert endpoint.connect(connect_timeout=1) is sentinel
    assert calls[0][0] == ()
    assert calls[0][1]["host"] == calls[0][1]["hostaddr"] == "127.0.0.1"
    assert calls[0][1]["port"] == 15432
    assert calls[0][1]["dbname"] == "generated_db"
    assert calls[0][1]["user"] == "generated_user"
    assert calls[0][1]["password"] == "generated_password"


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
