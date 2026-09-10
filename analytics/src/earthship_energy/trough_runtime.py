"""Default-off hard deadline for assessment, with no publication authority."""
import json
import os
import subprocess
import sys

HARD_TIMEOUT_SECONDS = 40
MAX_REPORT_BYTES = 16384
REQUIRED_ENV = ("ADVISORY_ASSESS_DSN", "ADVISORY_ASSESS_BANK_EPOCH",
                "ADVISORY_ASSESS_CUTOVER_AT", "ADVISORY_ASSESS_TIMEZONE")
REPORT_FIELDS = frozenset(("status", "generated_at", "target_start_day", "target_end_day_exclusive",
    "decisions", "processed", "inserted", "replayed", "measured", "insufficient",
    "unpersistable", "expired_unscored", "projection", "causal_reward_proven"))


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def run_assessment_process(environ=None):
    """No child/config/DB activity unless enabled exactly; never echo child errors."""
    env = os.environ if environ is None else environ
    if env.get("ADVISORY_ASSESS_ENABLED") != "1":
        return {"status": "disabled"}
    if any(not isinstance(env.get(key), str) or not env[key].strip() for key in REQUIRED_ENV):
        return {"status": "unavailable", "reason": "assessment_configuration_missing"}
    if env.get("PGSERVICE") or env.get("PGSERVICEFILE"):
        return {"status": "unavailable", "reason": "assessment_configuration_invalid"}
    child_env = {key: env[key] for key in REQUIRED_ENV}
    child_env["ADVISORY_ASSESS_ENABLED"] = "1"
    for key in ("PYTHONPATH", "LANG", "LC_ALL", "TZ"):
        if key in env:
            child_env[key] = env[key]
    try:
        completed = subprocess.run([sys.executable, "-m", "earthship_energy.trough_worker"],
            env=child_env, stdin=subprocess.DEVNULL, capture_output=True, check=False,
            timeout=HARD_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        # subprocess.run kills and waits for this child before raising.
        return {"status": "unavailable", "reason": "assessment_hard_timeout"}
    except (OSError, ValueError):
        return {"status": "unavailable", "reason": "assessment_process_failed"}
    if completed.returncode != 0:
        return {"status": "unavailable", "reason": "assessment_process_failed"}
    try:
        if len(completed.stdout) > MAX_REPORT_BYTES:
            raise ValueError("report too large")
        report = json.loads(completed.stdout, object_pairs_hook=_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
        if not isinstance(report, dict) or set(report) != REPORT_FIELDS:
            raise ValueError("report shape")
        if report["causal_reward_proven"] is not False:
            raise ValueError("reward claim")
        if report["status"] not in {"complete", "time_budget_exhausted", "decision_limit_exceeded"}:
            raise ValueError("report status")
        for key in ("decisions", "processed", "inserted", "replayed", "measured", "insufficient", "unpersistable", "expired_unscored"):
            if type(report[key]) is not int or report[key] < 0:
                raise ValueError("report count")
        if report["status"] != "complete" and report["projection"] is not None:
            raise ValueError("partial projection")
        return report
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return {"status": "unavailable", "reason": "assessment_report_invalid"}
