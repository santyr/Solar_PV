"""Assessment child process: explicit credentials, sanitized output, no actions."""
import json
import os


def main():
    if os.environ.get("ADVISORY_ASSESS_ENABLED") != "1":
        print('{"status":"disabled"}')
        return 0
    connection = None
    try:
        from datetime import datetime, timezone
        import psycopg2
        from .advisory_store import AdvisoryStore
        from .materialize import load_epoch_config
        from .trough_runner import run_trough_assessments

        store = AdvisoryStore(os.environ["ADVISORY_ASSESS_DSN"])
        bank_id = os.environ["ADVISORY_ASSESS_BANK_EPOCH"]
        bank = next(epoch for epoch in load_epoch_config() if epoch.epoch_id == bank_id and epoch.current_analytics)
        cutoff = datetime.fromisoformat(os.environ["ADVISORY_ASSESS_CUTOVER_AT"])
        now = datetime.now(timezone.utc)
        if cutoff.utcoffset() is None or cutoff > now:
            raise ValueError("invalid cutover")
        site_timezone = os.environ["ADVISORY_ASSESS_TIMEZONE"]
        connection = psycopg2.connect(store._dsn, hostaddr=store._hostaddr,
            sslmode="disable", connect_timeout=3,
            options="-c default_transaction_read_only=on -c statement_timeout=2000 "
                    "-c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000")
        with connection.cursor() as cursor:
            cursor.execute("SELECT itemid FROM public.items WHERE itemname=%s LIMIT 2", ("BMS_SOC_Evidence_JSON",))
            matches = cursor.fetchall()
        if len(matches) != 1 or type(matches[0][0]) is not int or matches[0][0] < 0:
            raise ValueError("ambiguous evidence mapping")
        table = f"item{matches[0][0]:04d}"
        connection.rollback()  # finish discovery before runner configures its dedicated session
        report = run_trough_assessments(connection, store, now=now, site_timezone=site_timezone,
            bank_epoch=bank, cutover_at=cutoff, evidence_table=table)
        encoded = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if len(encoded.encode()) > 16384:
            raise ValueError("report too large")
        print(encoded)
        return 0
    except Exception:
        # Never include DSNs, database errors, source rows or traceback output.
        print('{"status":"unavailable","reason":"assessment_worker_failed"}')
        return 1
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                # Process exit also releases the connection. Cleanup must not
                # expose driver errors after the sanitized result was emitted.
                pass


if __name__ == "__main__":
    raise SystemExit(main())
