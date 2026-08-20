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
