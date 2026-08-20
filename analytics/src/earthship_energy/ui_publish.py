"""Exact, non-actuating OpenHAB publication for the Energy UI payload."""

from __future__ import annotations

import hashlib
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .ui_payload import encode_energy_ui_payload


ITEM_NAME = "Energy_Analytics_JSON"
STATE_PATH = f"/rest/items/{ITEM_NAME}/state"
DEFAULT_OPENHAB_URL = "http://127.0.0.1:8080"


class _RefuseRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_no_redirect(request: Request, *, timeout: int):
    return build_opener(_RefuseRedirects()).open(request, timeout=timeout)


def _normalized_base_url(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("OpenHAB base URL is required")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("OpenHAB base URL must be an uncredentialed HTTP origin")
    return value.rstrip("/")


def publish_energy_ui_state(
    payload: object,
    *,
    base_url: str = DEFAULT_OPENHAB_URL,
    token: str,
    opener=None,
) -> dict[str, object]:
    """Validate once and PUT exactly one bounded String Item state."""
    if not isinstance(token, str) or not token.strip():
        raise ValueError("OpenHAB token is required")
    encoded = encode_energy_ui_payload(payload)
    origin = _normalized_base_url(base_url)
    request = Request(
        f"{origin}{STATE_PATH}",
        data=encoded,
        method="PUT",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token.strip()}",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )
    send = opener or _open_no_redirect
    try:
        with send(request, timeout=20) as response:
            status = int(response.status)
            response.read(4096)
    except HTTPError as exc:
        raise RuntimeError(f"OpenHAB analytics publication failed with HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("OpenHAB analytics publication transport failed") from None
    if not 200 <= status < 300:
        raise RuntimeError(f"OpenHAB analytics publication failed with HTTP {status}")
    return {
        "schema": "earthship-energy-ui-publication/v1",
        "status": "published",
        "item": ITEM_NAME,
        "generatedAt": payload["generatedAt"],
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }
