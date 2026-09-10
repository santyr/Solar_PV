"""Single observational Item publisher; no forecast or notification execution."""
from datetime import date, datetime
import math
import re
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import UUID

from .trough_runtime import REPORT_FIELDS
from .trough_selection import SELECTION_VERSION
from .trough_assessment import ASSESSMENT_VERSION

ITEM_NAME = "Forecast_Trough_Error_7d"
STATE_URL = "http://127.0.0.1:8080/rest/items/Forecast_Trough_Error_7d/state"
PROJECTION_FIELDS = frozenset(("schema_version", "diagnostic_version", "assessment_version",
    "bank_epoch", "generated_at", "target_start_day", "target_end_day_exclusive", "status",
    "sample_count", "mean_absolute_error_pct_points", "item_value", "samples",
    "missing_outcome_dates", "insufficient_dates", "pending_dates", "bandit_eligible"))
SAMPLE_FIELDS = frozenset(("prediction_day", "decision_id", "evidence_digest", "coverage",
                           "signed_residual_pct_points"))


class _RefuseRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _send(request, *, timeout):
    # Never forward credentials through ambient proxies or redirect destinations.
    return build_opener(ProxyHandler({}), _RefuseRedirects()).open(request, timeout=timeout)


def _number(value, low, high):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def diagnostic_state(report, *, now):
    """Validate the completed report and derive state from its distinct samples."""
    try:
        if (not isinstance(report, dict) or set(report) != REPORT_FIELDS
            or report["status"] != "complete" or report["causal_reward_proven"] is not False):
            raise ValueError()
        for key in ("decisions", "processed", "inserted", "replayed", "measured",
                    "insufficient", "unpersistable", "expired_unscored"):
            if type(report[key]) is not int or report[key] < 0:
                raise ValueError()
        p = report["projection"]
        if (not isinstance(p, dict) or set(p) != PROJECTION_FIELDS
            or type(p["schema_version"]) is not int or p["schema_version"] != 1
            or p["diagnostic_version"] != SELECTION_VERSION
            or p["assessment_version"] != ASSESSMENT_VERSION
            or p["bandit_eligible"] is not False
            or not isinstance(p["bank_epoch"], str) or not p["bank_epoch"]):
            raise ValueError()
        issued = datetime.fromisoformat(report["generated_at"])
        if (now.utcoffset() is None or issued.utcoffset() is None
            or not 0 <= (now-issued).total_seconds() <= 300
            or p["generated_at"] != report["generated_at"]):
            raise ValueError()
        start, end = (date.fromisoformat(report[key]) for key in
                      ("target_start_day", "target_end_day_exclusive"))
        if (not 0 < (end-start).days <= 30 or p["target_start_day"] != start.isoformat()
            or p["target_end_day_exclusive"] != end.isoformat()):
            raise ValueError()
        samples = p["samples"]
        if (not isinstance(samples, list) or not 0 <= len(samples) <= 7
            or type(p["sample_count"]) is not int or p["sample_count"] != len(samples)):
            raise ValueError()
        seen, ordered = set(), []
        for sample in samples:
            if not isinstance(sample, dict) or set(sample) != SAMPLE_FIELDS:
                raise ValueError()
            day = date.fromisoformat(sample["prediction_day"])
            if (not start <= day < end or day in seen
                or not _number(sample["coverage"], .9, 1)
                or not _number(sample["signed_residual_pct_points"], -100, 100)
                or str(UUID(sample["decision_id"])) != sample["decision_id"]
                or not re.fullmatch(r"[0-9a-f]{64}", sample["evidence_digest"])):
                raise ValueError()
            seen.add(day); ordered.append(day)
        if ordered != sorted(ordered):
            raise ValueError()
        for key in ("missing_outcome_dates", "insufficient_dates", "pending_dates"):
            dates = p[key]
            if not isinstance(dates, list) or len(dates) > 30 or dates != sorted(set(dates)):
                raise ValueError()
            for value in dates:
                day = date.fromisoformat(value)
                if not start <= day < end or day in seen:
                    raise ValueError()
                seen.add(day)
        if not samples:
            if p["status"] != "unavailable" or p["item_value"] is not None or p["mean_absolute_error_pct_points"] is not None:
                raise ValueError()
            return "UNDEF"
        mean = sum(abs(s["signed_residual_pct_points"]) for s in samples)/len(samples)
        if (p["status"] != "available" or not _number(p["item_value"], 0, 100)
            or not _number(p["mean_absolute_error_pct_points"], 0, 100)
            or not math.isclose(p["mean_absolute_error_pct_points"], mean, rel_tol=0, abs_tol=1e-9)
            or p["item_value"] != round(mean, 1)):
            raise ValueError()
        return f"{round(mean, 1):.1f}"
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        raise ValueError("invalid completed trough diagnostic") from None


def publish_trough_diagnostic(report, *, token, now, opener=None):
    """One PUT, no retries; only a validated completed report can reach transport."""
    state = diagnostic_state(report, now=now)
    if not isinstance(token, str) or not token.strip() or any(ord(c) < 32 or ord(c) == 127 for c in token):
        raise ValueError("invalid OpenHAB token")
    request = Request(STATE_URL, data=state.encode("ascii"), method="PUT",
        headers={"Authorization": f"Bearer {token.strip()}", "Content-Type": "text/plain; charset=utf-8"})
    try:
        with (opener or _send)(request, timeout=5) as response:
            status = response.status
        if type(status) is not int or not 200 <= status < 300:
            raise RuntimeError()
    except Exception:
        raise RuntimeError("trough diagnostic publication failed") from None
    return {"status": "accepted", "item": ITEM_NAME, "state": state,
            "sample_count": report["projection"]["sample_count"], "generated_at": report["generated_at"]}
