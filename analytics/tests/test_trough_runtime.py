import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from earthship_energy import trough_runtime as runtime


def env(**changes):
    values = dict(ADVISORY_ASSESS_ENABLED="1", ADVISORY_ASSESS_DSN="PRIVATE-DSN-SENTINEL",
                  ADVISORY_ASSESS_BANK_EPOCH="test_bank", ADVISORY_ASSESS_CUTOVER_AT="2026-09-10T00:00:00Z",
                  ADVISORY_ASSESS_TIMEZONE="America/Denver", OPENHAB_TOKEN="PRIVATE-TOKEN-SENTINEL")
    values.update(changes)
    return values


def report():
    return dict(status="complete", generated_at="2026-09-11T17:00:00Z",
        target_start_day="2026-08-12", target_end_day_exclusive="2026-09-11", decisions=0,
        processed=0, inserted=0, replayed=0, measured=0, insufficient=0, unpersistable=0,
        expired_unscored=0, projection=None, causal_reward_proven=False)


@pytest.mark.parametrize("enabled", [None, "", "0", "true", "yes"])
def test_disabled_runtime_does_not_launch_or_require_configuration(monkeypatch, enabled):
    monkeypatch.setattr(runtime.subprocess, "run", lambda *_a, **_kw: pytest.fail("child launched"))
    assert runtime.run_assessment_process({"ADVISORY_ASSESS_ENABLED":enabled}) == {"status":"disabled"}


def test_exact_child_command_deadline_and_minimal_environment(monkeypatch):
    expected = report()
    def launch(command, **kwargs):
        assert command == [sys.executable, "-m", "earthship_energy.trough_worker"]
        assert kwargs["timeout"] == 40
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert "OPENHAB_TOKEN" not in kwargs["env"]
        assert "NOTIFY_KEY" not in kwargs["env"]
        assert kwargs["env"]["ADVISORY_ASSESS_DSN"] == "PRIVATE-DSN-SENTINEL"
        return SimpleNamespace(returncode=0, stdout=json.dumps(expected).encode())
    monkeypatch.setattr(runtime.subprocess, "run", launch)
    assert runtime.run_assessment_process(env(NOTIFY_KEY="secret")) == expected


@pytest.mark.parametrize("failure", [OSError("PRIVATE-ERROR"),
                                    subprocess.TimeoutExpired("worker", 40, output=b"PRIVATE-OUTPUT")])
def test_process_errors_never_echo_private_details(monkeypatch, failure):
    def launch(*args, **kwargs): raise failure
    monkeypatch.setattr(runtime.subprocess, "run", launch)
    output = runtime.run_assessment_process(env())
    assert output["status"] == "unavailable"
    assert "PRIVATE" not in json.dumps(output)


@pytest.mark.parametrize("stdout", [b"PRIVATE-INVALID", b"x"*16385,
                                  b'{"status":"complete","status":"complete"}', b'[]'])
def test_malformed_or_oversized_child_report_is_not_accepted(monkeypatch, stdout):
    monkeypatch.setattr(runtime.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(returncode=0, stdout=stdout))
    assert runtime.run_assessment_process(env()) == {"status":"unavailable", "reason":"assessment_report_invalid"}


def test_partial_report_cannot_include_projection(monkeypatch):
    value = report(); value.update(status="time_budget_exhausted", projection={"item_value":2})
    monkeypatch.setattr(runtime.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(returncode=0, stdout=json.dumps(value).encode()))
    assert runtime.run_assessment_process(env())["reason"] == "assessment_report_invalid"


def test_actual_timed_out_child_is_killed_and_reaped(monkeypatch):
    original_run, original_popen = subprocess.run, subprocess.Popen
    children = []
    def popen(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        children.append(process)
        return process
    def launch(command, **kwargs):
        return original_run([sys.executable, "-c", "import time; time.sleep(10)"], **kwargs)
    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(subprocess, "run", launch)
    monkeypatch.setattr(runtime, "HARD_TIMEOUT_SECONDS", 0.1)
    result = runtime.run_assessment_process(env())
    assert result["reason"] == "assessment_hard_timeout"
    assert len(children) == 1 and children[0].poll() is not None


def test_worker_disabled_entry_has_no_optional_imports(monkeypatch, capsys):
    from earthship_energy import trough_worker
    monkeypatch.delenv("ADVISORY_ASSESS_ENABLED", raising=False)
    assert trough_worker.main() == 0
    assert json.loads(capsys.readouterr().out) == {"status":"disabled"}


def test_actual_worker_failure_is_sanitized():
    options = env(PYTHONPATH=os.environ["PYTHONPATH"])
    result = runtime.run_assessment_process(options)
    assert result == {"status":"unavailable", "reason":"assessment_process_failed"}
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("key", runtime.REQUIRED_ENV)
@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_configuration_never_launches(monkeypatch, key, value):
    monkeypatch.setattr(runtime.subprocess, "run", lambda *_a, **_kw: pytest.fail("child launched"))
    assert runtime.run_assessment_process(env(**{key: value}))["reason"] == "assessment_configuration_missing"


@pytest.mark.parametrize("key", ["PGSERVICE", "PGSERVICEFILE"])
def test_ambient_database_service_is_rejected(monkeypatch, key):
    monkeypatch.setattr(runtime.subprocess, "run", lambda *_a, **_kw: pytest.fail("child launched"))
    assert runtime.run_assessment_process(env(**{key: "private"}))["reason"] == "assessment_configuration_invalid"


@pytest.mark.parametrize("change", [dict(causal_reward_proven=True), dict(processed=True),
    dict(inserted=-1), dict(measured=1.5), dict(status=[]), dict(extra="field")])
def test_invalid_report_contract_is_rejected(monkeypatch, change):
    value = report(); value.update(change)
    monkeypatch.setattr(runtime.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(returncode=0, stdout=json.dumps(value).encode()))
    assert runtime.run_assessment_process(env())["reason"] == "assessment_report_invalid"


def test_nonzero_exit_never_accepts_report_or_echoes_errors(monkeypatch):
    monkeypatch.setattr(runtime.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(
        returncode=1, stdout=json.dumps(report()).encode(), stderr=b"PRIVATE-DRIVER-ERROR"))
    assert runtime.run_assessment_process(env()) == {"status":"unavailable", "reason":"assessment_process_failed"}


def test_worker_cleanup_error_cannot_escape_sanitized_failure(monkeypatch, capsys):
    import psycopg2
    from earthship_energy import advisory_store, materialize, trough_worker
    class BrokenConnection:
        def cursor(self):
            raise RuntimeError("PRIVATE-QUERY-ERROR")
        def close(self):
            raise RuntimeError("PRIVATE-CLEANUP-ERROR")
    for key, value in env().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(advisory_store, "AdvisoryStore", lambda _: SimpleNamespace(_dsn="private", _hostaddr="127.0.0.1"))
    monkeypatch.setattr(materialize, "load_epoch_config", lambda: [SimpleNamespace(epoch_id="test_bank", current_analytics=True)])
    monkeypatch.setattr(psycopg2, "connect", lambda *_a, **_kw: BrokenConnection())
    assert trough_worker.main() == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"status":"unavailable", "reason":"assessment_worker_failed"}
    assert not captured.err
