from datetime import datetime, timezone
import json
import pytest

from earthship_energy.scheduled import main
from earthship_energy.config import load_source_config


UTC = timezone.utc


def test_ac_v4_publication_is_opt_in_and_reads_before_one_write(monkeypatch, tmp_path):
    now = datetime(2026, 9, 25, 12, tzinfo=UTC)
    calls = []
    class Connection:
        closed = False
        def close(self):
            self.closed = True
            calls.append('close')
    connection = Connection()
    monkeypatch.setattr('earthship_energy.scheduled.utc_now', lambda: now)
    monkeypatch.setattr('earthship_energy.scheduled.parse_openhab_jdbc_config', lambda _: 'settings')
    monkeypatch.setattr('earthship_energy.scheduled.connect_read_only', lambda _: connection)
    monkeypatch.setattr('earthship_energy.scheduled.load_source_config', load_source_config)
    monkeypatch.setattr('earthship_energy.scheduled.fetch_inventory', lambda _: ([], set()))
    monkeypatch.setattr('earthship_energy.scheduled.resolve_sources', lambda *_: [])
    monkeypatch.setattr('earthship_energy.scheduled.fetch_live_subsystem_health', lambda *_a, **_k: {})
    monkeypatch.setattr('earthship_energy.scheduled.load_epoch_config', lambda _: [])
    monkeypatch.setattr('earthship_energy.scheduled.build_energy_ui_snapshot',
                        lambda *_a, **_k: {'schema': 'earthship-energy-ui/v3'})
    def read(_settings, *, policy, start_date, end_date, as_of):
        calls.append(('read', start_date.isoformat(), end_date.isoformat(), as_of))
        assert policy.topology_until is None
        return [{'selected': 'revision'}]
    monkeypatch.setattr('earthship_energy.scheduled.read_ac_snapshots', read)
    monkeypatch.setattr('earthship_energy.scheduled.build_ac_ui_payload',
                        lambda base, *, policy, ac_rows: calls.append(('project', base['schema'], ac_rows))
                        or {'schema': 'earthship-energy-ui/v4'})
    def publish(payload, **_):
        assert connection.closed
        calls.append(('publish', payload['schema']))
        return {'status': 'published'}
    monkeypatch.setattr('earthship_energy.scheduled.publish_energy_ui_state', publish)
    power = tmp_path/'power.json'
    power.write_text(json.dumps({'version': 1, 'policy': 'qualified_power_evidence_v1',
                     'item_name': 'Power_Evidence_JSON', 'cutover': '2026-09-20T00:00:00Z'}))
    ac = tmp_path/'ac.json'
    ac.write_text(json.dumps({'version': 1, 'policy': 'qualified_inverter_ac_output_v1',
                  'item_name': 'Inverter_AC_Evidence_JSON', 'cutover': '2026-09-23T20:55:12.284Z',
                  'topology': {'basis': 'inverter_only_no_bypass_or_generator',
                               'effective_from': '2026-09-23T20:55:12.284Z',
                               'effective_until': None}}))
    assert main(['energy-ui-publish', '--power-evidence-policy', str(power),
                 '--ac-evidence-policy', str(ac)]) == 0
    assert calls == [('read', '2026-09-23', '2026-09-25', now),
                     ('project', 'earthship-energy-ui/v3', [{'selected': 'revision'}]),
                     'close', ('publish', 'earthship-energy-ui/v4')]


def test_ac_v4_refuses_without_power_policy_before_db(monkeypatch):
    monkeypatch.setattr('earthship_energy.scheduled.connect_read_only',
                        lambda *_: pytest.fail('DB opened'))
    with pytest.raises(ValueError, match='requires qualified power'):
        main(['energy-ui-publish', '--ac-evidence-policy', '/private/ac.json'])


@pytest.mark.parametrize('qualified',[False,True])
def test_energy_ui_publish_closes_read_only_db_before_one_openhab_write(monkeypatch, capsys, tmp_path, qualified):
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
    monkeypatch.setattr("earthship_energy.scheduled.load_source_config", load_source_config)
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

    policy=tmp_path/'power.json'
    policy.write_text(json.dumps({'version':1,'policy':'qualified_power_evidence_v1',
        'item_name':'Power_Evidence_JSON','cutover':'2026-08-18T12:00:00Z'}))
    assert main([
        "energy-ui-publish", "--jdbc-config", "/protected/jdbc.config",
        "--epochs", "/repo/system-epochs.json",
        "--openhab-url", "http://127.0.0.1:8080",
    ] + (['--power-evidence-policy',str(policy)] if qualified else [])) == 0
    build_kwargs=next(c[3] for c in calls if isinstance(c,tuple) and c[0]=='build')
    assert ('power_policy' in build_kwargs) is qualified
    if qualified:
        assert build_kwargs['power_settings']=='settings'
        assert build_kwargs['power_policy'].cutover.isoformat()=='2026-08-18T12:00:00+00:00'
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
    monkeypatch.setattr("earthship_energy.scheduled.load_source_config", load_source_config)
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
