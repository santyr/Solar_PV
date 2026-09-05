from datetime import date, datetime, timezone
import json
from uuid import uuid4
import importlib
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor

import psycopg2
import pytest
from psycopg2 import sql
from advisory_records import build_decision_record, build_result_record
from advisory_db_fixture import advisory_db
from earthship_energy import advisory_store as module
from earthship_energy.advisory_store import AdvisoryStore, AdvisoryConflictError, AdvisoryStorageError, InvalidAdvisoryRecord

def decision(**changes):
    args = dict(decision_id=uuid4(), issued_at=datetime(2026,9,5,12,40,tzinfo=timezone.utc), site_timezone="America/Denver", source_revision="test-rev", policy_version="test-v1", bank_epoch="test_bank", prediction_day=date(2026,9,5), advisory="none", notification_eligible=False, notification_suppressed=False, inputs=dict(weather_today_high_raw_f=80, weather_today_low_raw_f=50, tomorrow_high_raw_f=81, tomorrow_low_raw_f=51, tomorrow_high_corrected_f=82, tomorrow_low_corrected_f=52, high_bias_f=1, low_bias_f=1, next_three_highs_raw_f=[81,82,83], three_day_high_mean_corrected_f=83, pv_today_kwh=20, trough_tomorrow_pct=65), thresholds=dict(close_up_high_f=82, close_up_streak_f=80, vent_high_f=75, trough_dm_pct=40))
    args.update(changes)
    return build_decision_record(**args)

def result(parent, **changes):
    args = dict(result_id=uuid4(), decision_id=json.loads(parent)["decision_id"], observed_at=datetime(2026,9,5,12,40,tzinfo=timezone.utc), kind="publication", target="Predicted_SoC_Trough_Tomorrow", status="accepted")
    args.update(changes)
    return build_result_record(**args)

def changed(encoded, **changes):
    payload = json.loads(encoded); payload.update(changes); return json.dumps(payload)

def test_round_trip_and_retries(advisory_db):
    store, origin = AdvisoryStore(advisory_db.writer), decision(); observed = result(origin)
    assert store.put_decision(origin) is True
    assert store.put_decision(json.dumps(json.loads(origin), indent=2)) is False
    assert store.put_result(observed) is True and store.put_result(observed) is False
    with pytest.raises(AdvisoryConflictError, match="advisory identity conflict"): store.put_decision(changed(origin, advisory="vent_tonight"))
    with pytest.raises(AdvisoryConflictError, match="advisory identity conflict"): store.put_result(changed(observed, status="failed"))

def test_references_and_chronology(advisory_db):
    store, origin = AdvisoryStore(advisory_db.writer), decision()
    with pytest.raises(AdvisoryStorageError): store.put_result(result(origin))
    with pytest.raises(AdvisoryStorageError): store.put_decision(decision(bank_epoch="missing_bank"))
    assert store.put_decision(origin)
    with pytest.raises(AdvisoryStorageError): store.put_result(result(origin, observed_at=datetime(2026,9,5,12,39,tzinfo=timezone.utc)))
    assert store.put_result(result(origin))

def test_concurrent_identical_retries(advisory_db):
    store, origin = AdvisoryStore(advisory_db.writer), decision()
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert list(pool.map(store.put_decision, [origin]*6)).count(True) == 1
        observed = result(origin)
        assert list(pool.map(store.put_result, [observed]*6)).count(True) == 1

@pytest.mark.parametrize("kind", ["decision", "result"])
def test_strict_validation_precedes_connection(kind, monkeypatch):
    origin, encoded = decision(), None
    encoded = origin if kind == "decision" else result(origin)
    bad = [None, b"{}", "[]", "null", "{", " " * 16385, changed(encoded, schema_version=2), changed(encoded, extra="secret"), changed(encoded, record_type="wrong")]
    def forbidden(*args, **kwargs): pytest.fail("invalid record attempted connection")
    monkeypatch.setattr(module.psycopg2, "connect", forbidden)
    store = AdvisoryStore("host=127.0.0.1 port=1 dbname=test user=test password=test")
    put = store.put_decision if kind == "decision" else store.put_result
    for value in bad:
        with pytest.raises(InvalidAdvisoryRecord, match="invalid advisory record"): put(value)

def test_import_constructor_and_explicit_dsn(monkeypatch):
    monkeypatch.setattr(module.psycopg2, "connect", lambda *a, **k: pytest.fail("connection"))
    importlib.reload(module)
    globals().update({name: getattr(module, name) for name in ("AdvisoryStore", "AdvisoryConflictError", "AdvisoryStorageError", "InvalidAdvisoryRecord")})
    for dsn in (None, "", "dbname=test", "service=production", "host=localhost port=1 dbname=t user=u password=p", "host=192.0.2.1 port=1 dbname=t user=u password=p", "host=a,b port=1 dbname=t user=u password=p"):
        with pytest.raises(ValueError, match="explicit advisory DSN required"): module.AdvisoryStore(dsn)

@pytest.mark.parametrize("variable", ["PGSERVICE", "PGSERVICEFILE"])
def test_ambient_service_configuration_rejected(variable, monkeypatch):
    monkeypatch.setenv(variable, "private-service-configuration")
    dsn = "host=127.0.0.1 port=1 dbname=test user=test password=test"
    with pytest.raises(AdvisoryStorageError, match="ambient advisory service configuration forbidden"): AdvisoryStore(dsn)

@pytest.mark.parametrize("table", ["advisory_decisions", "advisory_results"])
@pytest.mark.parametrize("verb", ["UPDATE", "DELETE", "TRUNCATE"])
def test_runtime_cannot_mutate(advisory_db, table, verb):
    statement = {"UPDATE":"UPDATE energy_analytics.{} SET payload=payload", "DELETE":"DELETE FROM energy_analytics.{}", "TRUNCATE":"TRUNCATE energy_analytics.{}"}[verb]
    for dsn in (advisory_db.writer, advisory_db.owner):
        with closing(psycopg2.connect(dsn)) as connection, connection.cursor() as cursor:
            with pytest.raises(psycopg2.Error): cursor.execute(sql.SQL(statement).format(sql.Identifier(table)))
