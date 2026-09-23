from datetime import date, datetime, timezone
import json

import pytest

from earthship_energy import cli
from earthship_energy.ac_policy import AcEvidencePolicy


POLICY = AcEvidencePolicy(datetime(2025, 1, 1, tzinfo=timezone.utc),
                          datetime(2025, 1, 1, tzinfo=timezone.utc), None)


class Connection:
    def __init__(self, calls):
        self.calls = calls

    def close(self):
        self.calls.append('close')


def args(mode='--dry-run', day='2025-01-03'):
    return ['ac-day', '--date', day, '--ac-evidence-policy', '/private/ac.json',
            '--power-evidence-policy', '/private/power.json', mode]


def setup(monkeypatch, calls):
    monkeypatch.setattr(cli, 'load_ac_policy', lambda _: POLICY)
    monkeypatch.setattr(cli, 'load_power_policy', lambda _: object())
    monkeypatch.setattr(cli, 'parse_openhab_jdbc_config', lambda _: object())
    monkeypatch.setattr(cli, 'connect_read_only', lambda _: calls.append('read-connect') or Connection(calls))
    monkeypatch.setattr(cli, 'connect_write', lambda _: calls.append('write-connect') or Connection(calls))
    monkeypatch.setattr(cli, 'fetch_inventory', lambda _: ([(653, 'Inverter_AC_Evidence_JSON')], {'item0653'}))
    monkeypatch.setattr(cli, 'read_ac_day_accounting', lambda *a, **k:
                        calls.append('source-read') or {'local_date': k['local_date'].isoformat(),
                                                        'observed_ac_load_kwh': 12.0})
    monkeypatch.setattr(cli, 'get_applied_migrations', lambda _: {})
    monkeypatch.setattr(cli, 'plan_migrations', lambda *_: [])
    monkeypatch.setattr(cli, 'discover_migrations', lambda: [])


def test_dry_run_never_opens_writer_or_stores(monkeypatch, capsys):
    calls = []
    setup(monkeypatch, calls)
    monkeypatch.setattr(cli, 'store_ac_snapshot', lambda *a: pytest.fail('dry run wrote'))
    assert cli.main(args()) == 0
    output = json.loads(capsys.readouterr().out)
    assert output['mode'] == 'read_only_dry_run'
    assert output['observed_ac_load_kwh'] == 12.0
    assert calls == ['read-connect', 'source-read', 'close']


def test_apply_requires_current_schema_and_rereads_topology(monkeypatch, capsys):
    calls = []
    setup(monkeypatch, calls)
    monkeypatch.setattr(cli, 'store_ac_snapshot', lambda *a: calls.append('store') or
                        {'snapshot_id': 1, 'inserted': True})
    assert cli.main(args('--apply')) == 0
    assert json.loads(capsys.readouterr().out)['mode'] == 'materialized'
    assert calls == ['write-connect', 'source-read', 'store', 'close']


def test_pending_migration_refuses_before_source_read(monkeypatch, capsys):
    calls = []
    setup(monkeypatch, calls)
    monkeypatch.setattr(cli, 'plan_migrations', lambda *_: [object()])
    assert cli.main(args('--apply')) == 2
    assert calls == ['write-connect', 'close']
    assert 'pending migrations' in capsys.readouterr().err


def test_changed_policy_refuses_before_store(monkeypatch, capsys):
    calls = []
    setup(monkeypatch, calls)
    policies = iter([POLICY, AcEvidencePolicy(POLICY.cutover, POLICY.topology_from,
                   datetime(2025, 1, 5, tzinfo=timezone.utc))])
    monkeypatch.setattr(cli, 'load_ac_policy', lambda _: next(policies))
    monkeypatch.setattr(cli, 'store_ac_snapshot', lambda *a: pytest.fail('changed policy wrote'))
    assert cli.main(args('--apply')) == 2
    assert calls == ['write-connect', 'source-read', 'close']
    assert 'changed during observation' in capsys.readouterr().err


@pytest.mark.parametrize('day', ['20250103', '2025-01-03-extra', '2050-01-01'])
def test_noncanonical_or_unfinished_day_refused_before_db(monkeypatch, capsys, day):
    calls = []
    setup(monkeypatch, calls)
    assert cli.main(args(day=day)) == 2
    assert calls == []
    assert capsys.readouterr().out == ''
