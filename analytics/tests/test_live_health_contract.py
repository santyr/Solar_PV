from datetime import datetime, timezone
from types import SimpleNamespace

from earthship_energy.config import load_source_config, live_health_source_config
from earthship_energy import scheduled


def test_live_contract_preserves_old_policy_without_changing_history_config():
    history = load_source_config()
    live = live_health_source_config(history)
    before = next(s for s in history.sources if s.canonical_name == "battery.soc_pct")
    after = next(s for s in live.sources if s.canonical_name == "battery.soc_pct")
    assert before.stale_policy == "atomic_bms_evidence"
    assert before.freshness_item == "BMS_SOC_Evidence_JSON"
    assert after.stale_policy == "status_must_equal_OK"
    assert after.freshness_item == "BMS_Comms_Status"
    assert [s for s in history.sources if s.canonical_name != "battery.soc_pct"] == [
        s for s in live.sources if s.canonical_name != "battery.soc_pct"]
    assert live_health_source_config(live) == live


def test_both_scheduled_consumers_resolve_the_explicit_live_contract(monkeypatch, tmp_path):
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def execute(self, *_): pass
        def fetchone(self): return (None,)
    connection = SimpleNamespace(cursor=Cursor, close=lambda: None)
    monkeypatch.setattr(scheduled, "parse_openhab_jdbc_config", lambda *_: None)
    monkeypatch.setattr(scheduled, "connect_read_only", lambda *_: connection)
    monkeypatch.setattr(scheduled, "fetch_inventory", lambda *_: ([], set()))
    seen = []
    def resolve(config, *_):
        soc = next(s for s in config.sources if s.canonical_name == "battery.soc_pct")
        assert soc.freshness_item == "BMS_Comms_Status"
        assert soc.stale_policy == "status_must_equal_OK"
        seen.append(config)
        return []
    monkeypatch.setattr(scheduled, "resolve_sources", resolve)
    monkeypatch.setattr(scheduled, "_live_sources_ok", lambda *_: True)
    scheduled.read_quality_state("unused", datetime.now(timezone.utc))
    monkeypatch.setattr(scheduled, "fetch_live_subsystem_health", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(scheduled, "build_energy_ui_snapshot", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(scheduled, "publish_energy_ui_state", lambda *_args, **_kwargs: {"status":"stub_only"})
    assert scheduled.main(["energy-ui-publish"]) == 0
    assert len(seen) == 2
