from pathlib import Path


UNIT_DIR = Path(__file__).resolve().parents[2] / "deploy" / "systemd" / "user"
JOBS = (
    "energy-data-quality",
    "energy-forecast-snapshot",
    "energy-daily-aggregate",
    "energy-ac-day",
    "energy-backup-check",
    "energy-monthly-report",
)


def test_required_user_units_are_complete_and_hardened():
    for job in JOBS:
        service = (UNIT_DIR / f"{job}.service").read_text()
        timer = (UNIT_DIR / f"{job}.timer").read_text()
        assert "Type=oneshot" in service
        assert "WorkingDirectory=/home/sat/Solar_PV/analytics" in service
        assert "PYTHONPATH=/home/sat/Solar_PV/analytics/src" in service
        assert "/usr/bin/flock --nonblock %t/" in service
        assert "NoNewPrivileges=true" in service
        assert "UMask=0077" in service
        assert "TimeoutStartSec=" in service
        assert "Persistent=true" in timer
        assert "WantedBy=timers.target" in timer


def test_routine_units_never_invoke_codex_or_change_openhab():
    paths = [path for path in UNIT_DIR.rglob('*')
             if path.is_file() and path.relative_to(UNIT_DIR).parts[0].startswith('energy-')]
    assert UNIT_DIR / 'energy-monthly-report.service.d' / 'qualified-power.conf' in paths
    bodies = "\n".join(path.read_text() for path in paths)
    assert "codex exec" not in bodies.lower()
    assert "/rest/items/" not in bodies
    assert "curl" not in bodies
    assert "systemctl restart openhab" not in bodies.lower()


def test_backup_unit_names_the_verified_same_host_manifest():
    body = (UNIT_DIR / "energy-backup-check.service").read_text()
    assert "/home/sat/backups/earthship-energy/full-restore-volep77n/backup-manifest.json" in body


def test_ac_day_unit_is_scoped_to_restricted_writer_and_never_publishes():
    service = (UNIT_DIR / "energy-ac-day.service").read_text()
    timer = (UNIT_DIR / "energy-ac-day.timer").read_text()
    assert "energy-power-writer.jdbc" in service
    assert "--power-evidence-policy /home/sat/Solar_PV/analytics/config/power-evidence.json" in service
    assert "--ac-evidence-policy /home/sat/Solar_PV/analytics/config/ac-evidence.json" in service
    assert "earthship_energy.scheduled ac-day" in service
    assert "OPENHAB_TOKEN" not in service
    assert "energy-ui-publish" not in service
    assert "OnCalendar=*-*-* 00:40:00" in timer


def test_staged_switch_quality_dropin_preserves_current_daily_sources():
    body = (UNIT_DIR / 'energy-daily-aggregate.service.d' / 'zz-qualified-switch.conf').read_text()
    assert 'STAGED ONLY' in body
    assert 'ExecStart=' in body
    assert '--jdbc-config /home/sat/.config/hex/energy-power-writer.jdbc' in body
    assert '--power-evidence-policy /home/sat/Solar_PV/analytics/config/power-evidence.json' in body
    assert '--temperature-evidence-policy /home/sat/.config/hex/weather-temperature-policy.json' in body
    assert '--temperature-evidence-db-config /home/sat/.config/hex/weather-temperature-db.json' in body
    assert '--switch-evidence-policy /home/sat/Solar_PV/analytics/config/switch-evidence.json' in body
    assert '--switch-evidence-db-config /home/sat/.config/hex/energy-power-reader.jdbc' in body
    assert '--bms-aux-evidence-policy /home/sat/Solar_PV/analytics/config/bms-aux-evidence.json' in body
    assert '--bms-aux-evidence-db-config /home/sat/.config/hex/energy-power-reader.jdbc' in body
    assert 'PYTHONPATH=/home/sat/Solar_PV/analytics/src:/home/sat/earthship-ui/openhab/scripts' in body
    assert 'OPENHAB_TOKEN' not in body


def test_staged_supporting_quality_command_preserves_all_paired_flags(monkeypatch):
    import shlex
    from datetime import datetime, timezone
    import earthship_energy.scheduled as scheduled

    body = (UNIT_DIR / 'energy-daily-aggregate.service.d' / 'zz-qualified-switch.conf').read_text()
    commands = [line.removeprefix('ExecStart=') for line in body.splitlines()
                if line.startswith('ExecStart=')]
    assert len(commands) == 2 and commands[0] == ''
    argv = shlex.split(commands[1])
    assert argv[:6] == ['/usr/bin/flock', '--nonblock', '%t/energy-daily-aggregate.lock',
                       '/usr/bin/python3', '-m', 'earthship_energy.scheduled']
    assert argv[6] == 'daily-aggregate'
    calls = []
    monkeypatch.setattr(scheduled, 'utc_now', lambda: datetime(2026, 10, 3, 6, 30, tzinfo=timezone.utc))
    monkeypatch.setattr(scheduled.energy_cli, 'main', lambda args: calls.append(args) or 0)
    assert scheduled.main(argv[6:]) == 0
    assert calls == [['aggregate', '--date', '2026-10-02', '--apply', *argv[7:]]]
    pairs = dict(zip(argv[7::2], argv[8::2]))
    assert set(pairs) == {'--jdbc-config', '--power-evidence-policy',
        '--temperature-evidence-policy', '--temperature-evidence-db-config',
        '--switch-evidence-policy', '--switch-evidence-db-config',
        '--bms-aux-evidence-policy', '--bms-aux-evidence-db-config'}
    assert pairs['--jdbc-config'].endswith('energy-power-writer.jdbc')
    assert pairs['--switch-evidence-db-config'] == pairs['--bms-aux-evidence-db-config']
    assert not {'--openhab-url', '--dry-run', '--ac-evidence-policy'} & pairs.keys()
