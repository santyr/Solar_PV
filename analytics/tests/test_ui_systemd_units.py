from pathlib import Path


UNIT_DIR = Path(__file__).resolve().parents[2] / "deploy" / "systemd" / "user"


def test_energy_ui_publisher_unit_is_hardened_and_observational():
    service = (UNIT_DIR / "energy-ui-publish.service").read_text()
    timer = (UNIT_DIR / "energy-ui-publish.timer").read_text()
    assert "Type=oneshot" in service
    assert "WorkingDirectory=/home/sat/Solar_PV/analytics" in service
    assert "PYTHONPATH=/home/sat/Solar_PV/analytics/src" in service
    assert "/usr/bin/flock --nonblock %t/energy-ui-publish.lock" in service
    assert "earthship_energy.scheduled energy-ui-publish" in service
    assert "EnvironmentFile=-%h/.config/hex/openhab.env" in service
    assert "OPENHAB_TOKEN" not in service
    assert "NoNewPrivileges=true" in service
    assert "ProtectSystem=strict" in service
    assert "ProtectHome=read-only" in service
    assert "curl" not in service
    assert "codex" not in service.lower()
    assert "OnCalendar=*-*-* *:0/5:00" in timer
    assert "Persistent=true" in timer
    assert "WantedBy=timers.target" in timer
