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
                decision_id=payload["decision_id"], issued_at=datetime.fromisoformat(payload["issued_at"]),
                site_timezone=payload["site_timezone"], source_revision=payload["source_revision"],
                policy_version=payload["policy_version"], bank_epoch=payload["bank_epoch"],
                prediction_day=date.fromisoformat(payload["prediction_day"]), advisory=payload["advisory"],
                inputs=payload["inputs"], thresholds=payload["thresholds"],
                notification_eligible=payload["notification"]["eligible"],
                notification_suppressed=payload["notification"]["suppressed"],
            )
        else:
            canonical = build_result_record(
                result_id=payload["result_id"], decision_id=payload["decision_id"],
                observed_at=datetime.fromisoformat(payload["observed_at"]), kind=payload["kind"],
                target=payload["target"], status=payload["status"],
            )
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

    def put_decision(self, encoded):
        payload, canonical = _decode(encoded, "decision")
        return self._put(payload, canonical, "decision")

    def put_result(self, encoded):
        payload, canonical = _decode(encoded, "result")
        return self._put(payload, canonical, "result")

    def _put(self, payload, canonical, kind):
        _reject_ambient_service()
        connection = None
        try:
            connection = psycopg2.connect(self._dsn, connect_timeout=3, hostaddr=self._hostaddr,
                sslmode="disable", options="-c statement_timeout=2000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000")
            connection.set_session(isolation_level="READ COMMITTED", autocommit=False)
            with connection:
                with connection.cursor() as cursor:
                    if kind == "decision":
                        cursor.execute("""INSERT INTO energy_analytics.advisory_decisions
                            (decision_id, issued_at, bank_epoch, payload) VALUES (%s, %s, %s, %s::jsonb)
                            ON CONFLICT (decision_id) DO NOTHING RETURNING decision_id""",
                            (payload["decision_id"], payload["issued_at"], payload["bank_epoch"], canonical))
                        lookup = "SELECT payload = %s::jsonb FROM energy_analytics.advisory_decisions WHERE decision_id = %s"
                        identity = payload["decision_id"]
                    else:
                        cursor.execute("""INSERT INTO energy_analytics.advisory_results
                            (result_id, decision_id, parent_issued_at, observed_at, payload)
                            SELECT %s, decision_id, issued_at, %s, %s::jsonb FROM energy_analytics.advisory_decisions
                            WHERE decision_id = %s ON CONFLICT (result_id) DO NOTHING RETURNING result_id""",
                            (payload["result_id"], payload["observed_at"], canonical, payload["decision_id"]))
                        lookup = "SELECT payload = %s::jsonb FROM energy_analytics.advisory_results WHERE result_id = %s"
                        identity = payload["result_id"]
                    if cursor.fetchone() is not None:
                        return True
                    cursor.execute(lookup, (canonical, identity))
                    existing = cursor.fetchone()
                    if existing is None:
                        raise AdvisoryStorageError("advisory storage unavailable")
                    if not existing[0]:
                        raise AdvisoryConflictError("advisory identity conflict")
                    return False
        except psycopg2.Error:
            raise AdvisoryStorageError("advisory storage unavailable") from None
        finally:
            if connection is not None:
                connection.close()
