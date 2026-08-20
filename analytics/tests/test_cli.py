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
