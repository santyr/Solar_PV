from datetime import datetime, timezone
import json

from earthship_energy.scheduled import main


UTC = timezone.utc


def test_energy_ui_publish_closes_read_only_db_before_one_openhab_write(monkeypatch, capsys):
    now = datetime(2026, 8, 20, 18, tzinfo=UTC)
    calls = []

    class Connection:
        closed = False

        def close(self):
            self.closed = True
            calls.append("close")

    connection = Connection()
    monkeypatch.setattr("earthship_energy.scheduled.utc_now", lambda: now)
    monkeypatch.setattr("earthship_energy.scheduled.parse_openhab_jdbc_config", lambda _: "settings")
    monkeypatch.setattr("earthship_energy.scheduled.connect_read_only", lambda settings: calls.append(("connect", settings)) or connection)
    monkeypatch.setattr("earthship_energy.scheduled.load_epoch_config", lambda _: ("epoch",))
    monkeypatch.setattr("earthship_energy.scheduled.load_source_config", lambda: "sources")
    monkeypatch.setattr("earthship_energy.scheduled.fetch_inventory", lambda db: ([(1, "item")], {"item0001"}))
    monkeypatch.setattr("earthship_energy.scheduled.resolve_sources", lambda config, items, tables: ("resolved",))
    monkeypatch.setattr(
        "earthship_energy.scheduled.fetch_live_subsystem_health",
        lambda db, config, resolved, **kwargs: {
            "bms": "ok", "schneider": "ok", "weather": "ok",
            "collector": "ok", "publisher": "ok", "reasons": [],
        },
    )
    monkeypatch.setattr(
        "earthship_energy.scheduled.build_energy_ui_snapshot",
        lambda db, epochs, **kwargs: calls.append(("build", db, epochs, kwargs)) or {"schema": "earthship-energy-ui/v1"},
    )

    def publish(payload, **kwargs):
        assert connection.closed is True
        calls.append(("publish", payload, kwargs))
        return {
            "schema": "earthship-energy-ui-publication/v1", "status": "published",
            "item": "Energy_Analytics_JSON", "generatedAt": now.isoformat(),
            "bytes": 100, "sha256": "a" * 64,
        }

    monkeypatch.setattr("earthship_energy.scheduled.publish_energy_ui_state", publish)
    monkeypatch.setenv("OPENHAB_TOKEN", "test-token")

    assert main([
        "energy-ui-publish", "--jdbc-config", "/protected/jdbc.config",
        "--epochs", "/repo/system-epochs.json",
        "--openhab-url", "http://127.0.0.1:8080",
    ]) == 0
    assert calls[0] == ("connect", "settings")
    assert calls[-2] == "close"
    assert calls[-1][0] == "publish"
    assert calls[-1][2]["token"] == "test-token"
    assert json.loads(capsys.readouterr().out)["status"] == "published"


def test_energy_ui_publish_does_not_write_when_snapshot_build_fails(monkeypatch):
    class Connection:
        closed = False

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr("earthship_energy.scheduled.parse_openhab_jdbc_config", lambda _: "settings")
    monkeypatch.setattr("earthship_energy.scheduled.connect_read_only", lambda _: connection)
    monkeypatch.setattr("earthship_energy.scheduled.load_epoch_config", lambda _: ("epoch",))
    monkeypatch.setattr("earthship_energy.scheduled.load_source_config", lambda: "sources")
    monkeypatch.setattr("earthship_energy.scheduled.fetch_inventory", lambda db: ([(1, "item")], {"item0001"}))
    monkeypatch.setattr("earthship_energy.scheduled.resolve_sources", lambda config, items, tables: ("resolved",))
    monkeypatch.setattr(
        "earthship_energy.scheduled.fetch_live_subsystem_health",
        lambda db, config, resolved, **kwargs: {
            "bms": "ok", "schneider": "ok", "weather": "ok",
            "collector": "ok", "publisher": "ok", "reasons": [],
        },
    )
    monkeypatch.setattr(
        "earthship_energy.scheduled.build_energy_ui_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad analytics")),
    )
    monkeypatch.setattr(
        "earthship_energy.scheduled.publish_energy_ui_state",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("write called")),
    )

    try:
        main(["energy-ui-publish"])
    except ValueError as error:
        assert str(error) == "bad analytics"
    else:
        raise AssertionError("snapshot failure must propagate")
    assert connection.closed is True
