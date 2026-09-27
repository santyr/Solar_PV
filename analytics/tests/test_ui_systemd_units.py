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
    assert "--ac-evidence-policy" not in service
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


def test_v4_ac_dropin_is_explicit_and_does_not_change_base_unit():
    dropin = (UNIT_DIR / "energy-ui-publish.service.d" /
              "zz-qualified-ac.conf").read_text()
    assert "ExecStart=\nExecStart=/usr/bin/flock" in dropin
    assert "--jdbc-config /home/sat/.config/hex/energy-power-reader.jdbc" in dropin
    assert "--power-evidence-policy /home/sat/Solar_PV/analytics/config/power-evidence.json" in dropin
    assert "--ac-evidence-policy /home/sat/Solar_PV/analytics/config/ac-evidence.json" in dropin
    assert "OPENHAB_TOKEN" not in dropin
    assert "--dry-run" not in dropin
