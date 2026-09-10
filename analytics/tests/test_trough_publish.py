from copy import deepcopy
from datetime import datetime, timedelta
import json
from urllib.error import HTTPError

import pytest

from earthship_energy import trough_publish as publisher
from test_trough_projection import pair, project
from test_trough_runtime import report


def completed(empty=False):
    projection = project([] if empty else [pair()])
    value = report()
    value.update(projection=projection)
    for key in ("generated_at", "target_start_day", "target_end_day_exclusive"):
        value[key] = projection[key]
    return value


class Response:
    status = 204
    def __enter__(self): return self
    def __exit__(self, *_): return False


@pytest.mark.parametrize("empty,state,count", [(False, b"10.0", 1), (True, b"UNDEF", 0)])
def test_exact_single_observational_put(empty, state, count):
    value = completed(empty)
    original = deepcopy(value)
    calls = []
    def send(request, *, timeout):
        calls.append(request)
        assert request.full_url == "http://127.0.0.1:8080/rest/items/Forecast_Trough_Error_7d/state"
        assert request.method == "PUT" and request.data == state
        assert request.get_header("Authorization") == "Bearer test-token"
        assert timeout == 5
        return Response()
    result = publisher.publish_trough_diagnostic(value, token="test-token",
        now=datetime.fromisoformat(value["generated_at"]), opener=send)
    assert len(calls) == 1 and result["status"] == "accepted"
    assert result["sample_count"] == count and value == original
    assert "test-token" not in json.dumps(result)


@pytest.mark.parametrize("field,bad", [("item_value", 99), ("sample_count", True),
    ("sample_count", 7), ("mean_absolute_error_pct_points", float("nan")),
    ("bandit_eligible", True), ("schema_version", True), ("status", "unavailable"),
    ("diagnostic_version", "legacy"), ("generated_at", "2000-01-01T00:00:00Z")])
def test_invalid_projection_never_reaches_transport(field, bad):
    value = completed(); value["projection"][field] = bad
    with pytest.raises(ValueError, match="invalid completed"):
        publisher.publish_trough_diagnostic(value, token="token",
            now=datetime.fromisoformat(value["generated_at"]),
            opener=lambda *_a, **_k: pytest.fail("network called"))


@pytest.mark.parametrize("field,bad", [("coverage", .89), ("coverage", True),
    ("evidence_digest", "bad"), ("decision_id", "bad"),
    ("signed_residual_pct_points", float("inf")), ("prediction_day", "2000-01-01")])
def test_invalid_sample_is_rejected(field, bad):
    value = completed(); value["projection"]["samples"][0][field] = bad
    with pytest.raises(ValueError):
        publisher.diagnostic_state(value, now=datetime.fromisoformat(value["generated_at"]))


@pytest.mark.parametrize("seconds", [-1, 301])
def test_future_or_stale_report_is_rejected(seconds):
    value = completed()
    with pytest.raises(ValueError):
        publisher.diagnostic_state(value, now=datetime.fromisoformat(value["generated_at"])+timedelta(seconds=seconds))


@pytest.mark.parametrize("status", ["disabled", "unavailable", "time_budget_exhausted", "decision_limit_exceeded"])
def test_noncomplete_report_is_not_publishable(status):
    value = completed(); value["status"] = status
    with pytest.raises(ValueError):
        publisher.diagnostic_state(value, now=datetime.fromisoformat(value["generated_at"]))


def test_duplicate_or_overlapping_dates_are_rejected():
    value = completed()
    value["projection"]["missing_outcome_dates"] = [value["projection"]["samples"][0]["prediction_day"]]
    with pytest.raises(ValueError):
        publisher.diagnostic_state(value, now=datetime.fromisoformat(value["generated_at"]))


@pytest.mark.parametrize("failure", [TimeoutError("PRIVATE"), OSError("PRIVATE"),
    HTTPError(publisher.STATE_URL, 302, "PRIVATE", {}, None)])
def test_failure_is_sanitized_and_never_retried(failure):
    value = completed(); calls = []
    def send(*args, **kwargs):
        calls.append(1)
        raise failure
    with pytest.raises(RuntimeError, match="^trough diagnostic publication failed$"):
        publisher.publish_trough_diagnostic(value, token="token",
            now=datetime.fromisoformat(value["generated_at"]), opener=send)
    assert len(calls) == 1


def test_transport_disables_proxy_and_redirect_handlers(monkeypatch):
    import urllib.request
    calls = []
    class Opener:
        def open(self, request, *, timeout):
            calls.append((request, timeout))
            return "response"
    def build(*handlers):
        assert len(handlers) == 2
        assert isinstance(handlers[0], urllib.request.ProxyHandler)
        assert handlers[0].proxies == {}
        assert handlers[1].redirect_request(None, None, 302, "", {}, "https://elsewhere") is None
        return Opener()
    monkeypatch.setattr(publisher, "build_opener", build)
    assert publisher._send("request", timeout=5) == "response"
    assert calls == [("request", 5)]


@pytest.mark.parametrize("token", ["", "   ", "token\r\nInjected: yes"])
def test_invalid_token_never_reaches_transport(token):
    value = completed()
    with pytest.raises(ValueError, match="token"):
        publisher.publish_trough_diagnostic(value, token=token,
            now=datetime.fromisoformat(value["generated_at"]),
            opener=lambda *_a, **_k: pytest.fail("network called"))
