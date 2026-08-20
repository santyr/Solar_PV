from pathlib import Path


UNIT_DIR = Path(__file__).resolve().parents[2] / "deploy" / "systemd" / "user"
JOBS = (
    "energy-data-quality",
    "energy-forecast-snapshot",
    "energy-daily-aggregate",
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
    bodies = "\n".join(path.read_text() for path in UNIT_DIR.glob("energy-*"))
    assert "codex exec" not in bodies.lower()
    assert "/rest/items/" not in bodies
    assert "curl" not in bodies
    assert "systemctl restart openhab" not in bodies.lower()


def test_backup_unit_names_the_verified_same_host_manifest():
    body = (UNIT_DIR / "energy-backup-check.service").read_text()
    assert "/home/sat/backups/earthship-energy/2026-08-20/backup-manifest.json" in body
