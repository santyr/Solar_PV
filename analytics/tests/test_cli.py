import json

from earthship_energy import cli

from test_config import minimal_source, write_config


def source_config(tmp_path):
    return write_config(
        tmp_path,
        {"version": 1, "timezone": "UTC", "sources": [minimal_source()]},
    )


def test_validate_config_prints_secret_free_json(tmp_path, capsys):
    path = source_config(tmp_path)
    assert cli.main(["validate-config", "--config", str(path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "planned_sources": 0,
        "sources": 1,
        "status": "ok",
        "timezone": "UTC",
        "version": 1,
    }


def test_validate_sources_uses_read_only_inventory(tmp_path, monkeypatch, capsys):
    path = source_config(tmp_path)
    calls = []

    class Settings:
        def safe_summary(self):
            return {"host": "db", "dbname": "openhab", "user": "reader", "port": 5432}

    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: Settings())
    monkeypatch.setattr(cli, "connect_read_only", lambda _: calls.append("connect") or object())
    monkeypatch.setattr(
        cli,
        "fetch_inventory",
        lambda _: ([(550, "BMS_SOC")], {"item0550"}),
    )
    assert cli.main(
        [
            "validate-sources",
            "--config",
            str(path),
            "--jdbc-config",
            "/protected/jdbc.config",
        ]
    ) == 0
    output = json.loads(capsys.readouterr().out)
    assert calls == ["connect"]
    assert output["status"] == "ok"
    assert output["resolved_sources"][0]["table_name"] == "item0550"
    assert "password" not in json.dumps(output).lower()


def test_migrate_dry_run_lists_pending_without_write(tmp_path, monkeypatch, capsys):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "0001_first.sql").write_text("SELECT 1;")

    class Settings:
        dbname = "openhab"

        def safe_summary(self):
            return {"host": "db", "dbname": "openhab", "user": "reader", "port": 5432}

    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: Settings())
    monkeypatch.setattr(cli, "connect_read_only", lambda _: object())
    monkeypatch.setattr(cli, "get_applied_migrations", lambda _: {})
    assert cli.main(
        [
            "migrate",
            "--migrations",
            str(migrations),
            "--jdbc-config",
            "/x",
            "--dry-run",
        ]
    ) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "dry_run"
    assert output["pending"][0]["version"] == 1


def test_migrate_apply_refuses_without_verified_backup(tmp_path, monkeypatch, capsys):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "0001_first.sql").write_text("SELECT 1;")

    class Settings:
        dbname = "openhab"

    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: Settings())
    rc = cli.main(
        [
            "migrate",
            "--migrations",
            str(migrations),
            "--jdbc-config",
            "/x",
            "--apply",
        ]
    )
    assert rc == 2
    assert "backup" in capsys.readouterr().err.lower()


def test_aggregate_date_runs_read_only_dry_run(tmp_path, monkeypatch, capsys):
    path = source_config(tmp_path)

    class Settings:
        pass

    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: Settings())
    monkeypatch.setattr(cli, "connect_read_only", lambda _: object())
    monkeypatch.setattr(cli, "fetch_inventory", lambda _: ([], set()))
    monkeypatch.setattr(cli, "resolve_sources", lambda *_: [])
    monkeypatch.setattr(
        cli,
        "build_daily_snapshot",
        lambda _connection, _config, _resolved, day: {
            "status": "ok",
            "mode": "read_only_dry_run",
            "local_date": day.isoformat(),
        },
    )
    assert cli.main(
        ["aggregate", "--date", "2026-01-02", "--config", str(path), "--dry-run"]
    ) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["local_date"] == "2026-01-02"
    assert output["mode"] == "read_only_dry_run"


def test_aggregate_apply_requires_current_schema_not_backup(tmp_path, monkeypatch, capsys):
    path = source_config(tmp_path)

    class Settings:
        pass

    class Connection:
        def close(self):
            pass

    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: Settings())
    monkeypatch.setattr(cli, "connect_write", lambda _: Connection())
    monkeypatch.setattr(cli, "discover_migrations", lambda: [object()])
    monkeypatch.setattr(cli, "get_applied_migrations", lambda _: {})
    monkeypatch.setattr(cli, "plan_migrations", lambda *_: [object()])
    rc = cli.main([
        "aggregate", "--date", "2026-01-02", "--config", str(path), "--apply"
    ])
    assert rc == 2
    assert "pending migration" in capsys.readouterr().err.lower()


def test_aggregate_apply_seeds_and_materializes(tmp_path, monkeypatch, capsys):
    path = source_config(tmp_path)
    manifest = tmp_path / "backup.json"
    manifest.write_text("{}")
    epochs_path = tmp_path / "epochs.json"
    epochs_path.write_text("{}")
    calls = []

    class Settings:
        dbname = "openhab"

    class Connection:
        def close(self):
            calls.append("close")

    epoch = type("Epoch", (), {"epoch_id": "current"})()
    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: Settings())
    monkeypatch.setattr(cli, "connect_write", lambda _: Connection())
    monkeypatch.setattr(cli, "discover_migrations", lambda: [object()])
    monkeypatch.setattr(cli, "get_applied_migrations", lambda _: {1: "sha"})
    monkeypatch.setattr(cli, "plan_migrations", lambda *_: [])
    monkeypatch.setattr(cli, "fetch_inventory", lambda _: ([], set()))
    monkeypatch.setattr(cli, "resolve_sources", lambda *_: [])
    monkeypatch.setattr(cli, "load_epoch_config", lambda _: (epoch,))
    monkeypatch.setattr(cli, "select_epoch", lambda *_: epoch)
    monkeypatch.setattr(cli, "seed_reference_data", lambda *_: calls.append("seed") or {})
    monkeypatch.setattr(cli, "build_daily_snapshot", lambda *_: {
        "status": "ok", "mode": "read_only_dry_run", "local_date": "2026-01-02"
    })
    monkeypatch.setattr(cli, "materialize_daily_snapshot", lambda *_: {
        "tables_written": 4, "epoch_id": "current"
    })
    assert cli.main([
        "aggregate", "--date", "2026-01-02", "--config", str(path),
        "--epochs", str(epochs_path), "--apply",
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "materialized"
    assert output["tables_written"] == 4
    assert calls == ["seed", "close"]


def test_report_reads_compact_products_and_prints_json(monkeypatch, capsys):
    class Connection:
        def close(self):
            pass

    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: object())
    monkeypatch.setattr(cli, "connect_read_only", lambda _: Connection())
    monkeypatch.setattr(cli, "fetch_daily_report_rows", lambda *_: [{
        "local_date": __import__("datetime").date(2026, 8, 1),
        "pv_kwh": 7, "load_kwh": 5, "min_soc_pct": 80,
        "reached_99": True, "charge_kwh": 3, "discharge_kwh": 2,
        "daily_efc": .12, "quality": "ok",
    }])
    assert cli.main([
        "report", "monthly", "--start", "2026-08-01", "--end", "2026-09-01",
        "--epoch", "discover_4_module_2026", "--format", "json",
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["report"] == "monthly"
    assert output["metrics"]["pv_kwh"] == 7


def test_module_report_uses_bounded_module_reader(monkeypatch, capsys):
    class Connection:
        def close(self):
            pass

    captured = []
    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: object())
    monkeypatch.setattr(cli, "connect_read_only", lambda _: Connection())
    monkeypatch.setattr(
        cli, "fetch_module_report_rows",
        lambda _connection, start, end: captured.append((start, end)) or [],
    )
    assert cli.main([
        "report", "modules", "--start", "2026-08-01", "--end", "2026-09-01",
        "--epoch", "discover_4_module_2026", "--format", "json",
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["report"] == "module_health"
    assert output["status"] == "unavailable"
    assert output["epoch_id"] == "discover_4_module_2026"
    assert captured[0][0].isoformat() == "2026-08-01T00:00:00-06:00"
    assert captured[0][1].isoformat() == "2026-09-01T00:00:00-06:00"


def test_lynk_import_dry_run_is_write_free(tmp_path, monkeypatch, capsys):
    source = tmp_path / "lynk.csv"
    source.write_bytes(b"module csv")

    class Connection:
        def close(self):
            pass

    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: object())
    monkeypatch.setattr(cli, "connect_read_only", lambda _: Connection())
    monkeypatch.setattr(cli, "fetch_existing_import_hashes", lambda _: set())
    batch = type("Batch", (), {
        "status": "ready", "sha256": "a" * 64, "rows": (1, 2),
    })()
    monkeypatch.setattr(cli, "prepare_lynk_import", lambda *_: batch)
    assert cli.main(["import-lynk", "--file", str(source), "--dry-run"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "mode": "dry_run", "rows": 2, "sha256": "a" * 64,
        "source_name": "lynk.csv", "status": "ready",
    }


def test_lynk_import_apply_persists_with_current_schema(tmp_path, monkeypatch, capsys):
    source = tmp_path / "lynk.csv"
    source.write_bytes(b"module csv")
    calls = []

    class Connection:
        def close(self):
            calls.append("close")

    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: object())
    monkeypatch.setattr(cli, "connect_write", lambda _: Connection())
    monkeypatch.setattr(cli, "discover_migrations", lambda: [object()])
    monkeypatch.setattr(cli, "get_applied_migrations", lambda _: {1: "sha"})
    monkeypatch.setattr(cli, "plan_migrations", lambda *_: [])
    monkeypatch.setattr(cli, "fetch_existing_import_hashes", lambda _: set())
    batch = type("Batch", (), {
        "status": "ready", "sha256": "b" * 64, "rows": (1,),
    })()
    monkeypatch.setattr(cli, "prepare_lynk_import", lambda *_: batch)
    monkeypatch.setattr(
        cli, "persist_lynk_import",
        lambda *_: {"status": "imported", "batch_id": 7, "rows": 1, "sha256": "b" * 64},
    )
    assert cli.main(["import-lynk", "--file", str(source), "--apply"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "materialized"
    assert output["batch_id"] == 7
    assert calls == ["close"]


def test_record_snow_dry_run_validates_without_database_write(monkeypatch, capsys):
    assert cli.main([
        "record-snow", "--state", "snow_cleared",
        "--occurred-at", "2026-01-01T10:00:00-07:00",
        "--method", "operator", "--confidence", "1.0",
        "--note", "panels cleared", "--dry-run",
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "dry_run"
    assert output["event"]["state"] == "snow_cleared"
    assert output["event"]["occurred_at"] == "2026-01-01T10:00:00-07:00"
    assert output["event"]["authority"] == "observational_only"


def test_record_snow_apply_is_schema_gated(monkeypatch, capsys):
    class Connection:
        def close(self):
            pass

    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: object())
    monkeypatch.setattr(cli, "connect_write", lambda _: Connection())
    monkeypatch.setattr(cli, "discover_migrations", lambda: [object()])
    monkeypatch.setattr(cli, "get_applied_migrations", lambda _: {1: "sha"})
    monkeypatch.setattr(cli, "plan_migrations", lambda *_: [])
    monkeypatch.setattr(
        cli, "persist_snow_event",
        lambda _connection, _event: {"status": "inserted", "event_id": 9},
    )
    assert cli.main([
        "record-snow", "--state", "snow_covered",
        "--occurred-at", "2026-01-01T10:00:00Z",
        "--method", "operator", "--confidence", "0.9", "--apply",
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {"event_id": 9, "mode": "materialized", "status": "inserted"}


def test_export_features_writes_versioned_csv_from_read_only_database(
    tmp_path, monkeypatch, capsys
):
    output_path = tmp_path / "features.csv"

    class Connection:
        def close(self):
            pass

    monkeypatch.setattr(cli, "parse_openhab_jdbc_config", lambda _: object())
    monkeypatch.setattr(cli, "connect_read_only", lambda _: Connection())
    monkeypatch.setattr(cli, "fetch_inventory", lambda _: ([], set()))
    monkeypatch.setattr(
        cli, "resolve_sources",
        lambda *_: [type("Resolved", (), {
            "canonical_name": "battery.soc_pct", "table_name": "item0001",
        })()],
    )
    monkeypatch.setattr(
        cli, "fetch_feature_rows", lambda *_args, **_kwargs: [{"at": "row"}],
    )
    monkeypatch.setattr(cli, "export_feature_csv", lambda *_args, **_kwargs: b"schema\nrow\n")
    assert cli.main([
        "export-features", "--start", "2026-08-01T00:00:00Z",
        "--end", "2026-08-02T00:00:00Z", "--output", str(output_path),
        "--cadence", "15",
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "ok"
    assert result["rows"] == 1
    assert result["bytes"] == len(b"schema\nrow\n")
    assert len(result["sha256"]) == 64
    assert output_path.read_bytes() == b"schema\nrow\n"
