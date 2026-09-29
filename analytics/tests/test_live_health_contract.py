from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace

from earthship_energy.config import load_source_config, live_health_source_config
from earthship_energy import scheduled
from earthship_energy.ui_reader import fetch_live_subsystem_health


def test_live_contract_uses_atomic_soc_policy_without_changing_history_config():
    history = load_source_config()
    live = live_health_source_config(history)
    before = next(s for s in history.sources if s.canonical_name == "battery.soc_pct")
    after = next(s for s in live.sources if s.canonical_name == "battery.soc_pct")
    assert before.stale_policy == "atomic_bms_evidence"
    assert before.freshness_item == "BMS_SOC_Evidence_JSON"
    assert after.stale_policy == "atomic_bms_evidence"
    assert after.freshness_item == "BMS_SOC_Evidence_JSON"
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
        assert soc.freshness_item == "BMS_SOC_Evidence_JSON"
        assert soc.stale_policy == "atomic_bms_evidence"
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


def test_both_live_consumers_expire_atomic_soc_even_when_last_row_is_unchanged():
    now = datetime(2026, 9, 28, 22, 0, tzinfo=timezone.utc)
    observed = now - timedelta(seconds=30)
    millis = lambda at: int(at.timestamp() * 1000)
    receipt = json.dumps({
        "version": 1, "streamEpoch": "00000000-0000-0000-0000-000000000001",
        "recordedAt": millis(observed), "status": "valid", "reason": "ok",
        "observedAt": millis(observed), "scaleObservedAt": millis(observed),
        "validUntil": millis(observed + timedelta(seconds=120)), "soc": 71,
    })
    persisted = now - timedelta(seconds=29)

    class Connection:
        def __init__(self, raw):
            self.raw = raw
            self.queries = []

        def cursor(self):
            outer = self
            class Cursor:
                def __enter__(self): return self
                def __exit__(self, *_): return False
                def execute(self, sql, params): outer.queries.append((sql, params))
                def fetchone(self): return (persisted, outer.raw)
            return Cursor()

    config = live_health_source_config(load_source_config())
    soc = next(source for source in config.sources if source.canonical_name == "battery.soc_pct")
    config = SimpleNamespace(sources=(soc,))
    resolved = (SimpleNamespace(canonical_name="battery.soc_pct", required=True,
                                status="ok", freshness_table_name="item0001"),)
    healthy = Connection(receipt)
    assert scheduled._live_sources_ok(healthy, config, resolved, now)
    assert fetch_live_subsystem_health(
        healthy, config, resolved, generated_at=now)["bms"] == "ok"
    assert all("SELECT time, value" in sql for sql, _ in healthy.queries)

    expired_at = now + timedelta(seconds=91)
    stale = Connection(receipt)
    assert not scheduled._live_sources_ok(stale, config, resolved, expired_at)
    assert fetch_live_subsystem_health(
        stale, config, resolved, generated_at=expired_at)["bms"] == "fault"
    fault = Connection(json.dumps({**json.loads(receipt), "status": "unavailable",
                                   "reason": "input_stale", "observedAt": None,
                                   "scaleObservedAt": None, "validUntil": None,
                                   "soc": None}))
    assert not scheduled._live_sources_ok(fault, config, resolved, now)
    assert fetch_live_subsystem_health(
        fault, config, resolved, generated_at=now)["bms"] == "fault"
