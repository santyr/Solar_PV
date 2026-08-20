from datetime import timezone
import json
from urllib.error import HTTPError

import pytest

from earthship_energy.ui_publish import ITEM_NAME, STATE_PATH, publish_energy_ui_state


UTC = timezone.utc


def valid_payload():
    from test_ui_payload import payload
    return payload()


class Response:
    status = 204

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _limit=-1):
        return b""


def test_publisher_puts_one_exact_validated_state_with_bearer_auth():
    calls = []

    def opener(request, *, timeout):
        calls.append((request, timeout))
        return Response()

    result = publish_energy_ui_state(
        valid_payload(), base_url="http://127.0.0.1:8080",
        token="secret-test-token", opener=opener,
    )

    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.full_url == f"http://127.0.0.1:8080{STATE_PATH}"
    assert request.method == "PUT"
    assert request.get_header("Content-type") == "text/plain; charset=utf-8"
    assert request.get_header("Authorization") == "Bearer secret-test-token"
    assert json.loads(request.data) == valid_payload()
    assert timeout == 20
    assert result == {
        "schema": "earthship-energy-ui-publication/v1",
        "status": "published", "item": ITEM_NAME,
        "generatedAt": "2026-08-20T18:00:00+00:00",
        "bytes": len(request.data), "sha256": result["sha256"],
    }
    assert len(result["sha256"]) == 64
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize("base_url", [
    "ftp://127.0.0.1:8080",
    "http://user:pass@127.0.0.1:8080",
    "http://127.0.0.1:8080/rest",
    "http://127.0.0.1:8080?x=1",
])
def test_publisher_rejects_ambiguous_base_urls_without_network(base_url):
    with pytest.raises(ValueError, match="base URL"):
        publish_energy_ui_state(
            valid_payload(), base_url=base_url, token="token",
            opener=lambda *_args, **_kwargs: pytest.fail("network called"),
        )


def test_publisher_requires_token_and_valid_payload_before_network():
    with pytest.raises(ValueError, match="token"):
        publish_energy_ui_state(valid_payload(), token="")
    malformed = valid_payload()
    malformed["schema"] = "wrong"
    with pytest.raises(ValueError, match="schema"):
        publish_energy_ui_state(
            malformed, token="token",
            opener=lambda *_args, **_kwargs: pytest.fail("network called"),
        )


def test_publisher_sanitizes_non_success_response():
    def opener(request, *, timeout):
        raise HTTPError(request.full_url, 503, "contains upstream detail", {}, None)

    with pytest.raises(RuntimeError, match="HTTP 503") as error:
        publish_energy_ui_state(valid_payload(), token="token", opener=opener)
    assert "upstream detail" not in str(error.value)
