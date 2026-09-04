"""BoundedHttpClient: timeout, bounded retries with backoff, and error mapping.
Driven by httpx.MockTransport --- no network."""

from __future__ import annotations

import httpx

from dsi.domain.tools import ToolErrorCode
from dsi.mcp_server.http_client import BoundedHttpClient


def _client(handler, sleeps: list | None = None, **kw) -> BoundedHttpClient:
    sink = sleeps if sleeps is not None else []
    return BoundedHttpClient(
        base_url="http://test", transport=httpx.MockTransport(handler),
        sleep_fn=sink.append, **kw,
    )


def test_success_returns_json():
    client = _client(lambda req: httpx.Response(200, json={"hello": "world"}))
    out = client.get_json("/x", {})
    assert out.ok and out.json == {"hello": "world"}
    assert out.retry_count == 0


def test_retries_on_500_then_succeeds():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(200, json={"ok": 1}) if calls["n"] >= 2 else httpx.Response(500)

    client = _client(handler, max_retries=2)
    out = client.get_json("/x", {})
    assert out.ok is True
    assert calls["n"] == 2
    assert out.retry_count == 1  # one retry before success


def test_timeout_exhausts_retries_and_maps_to_timeout_error():
    def handler(req):
        raise httpx.TimeoutException("slow")

    client = _client(handler, max_retries=2)
    out = client.get_json("/x", {})
    assert out.ok is False
    assert out.error.code is ToolErrorCode.TIMEOUT
    assert out.retry_count == 2  # tried initial + 2 retries


def test_malformed_json_maps_to_malformed_error():
    client = _client(lambda req: httpx.Response(200, content=b"not json{{"))
    out = client.get_json("/x", {})
    assert out.ok is False
    assert out.error.code is ToolErrorCode.MALFORMED_RESPONSE
    assert out.error.retryable is False


def test_404_is_not_retried():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(404, json={"error": "NOT_FOUND"})

    client = _client(handler, max_retries=3)
    out = client.get_json("/x", {})
    assert out.status_code == 404
    assert out.error.code is ToolErrorCode.NOT_FOUND
    assert calls["n"] == 1  # 404 short-circuits, no retries


def test_429_is_retried():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(429)

    client = _client(handler, max_retries=1)
    out = client.get_json("/x", {})
    assert out.error.code is ToolErrorCode.RATE_LIMITED
    assert calls["n"] == 2  # initial + 1 retry


# --- Retry-After: 429/503 honor the server's timing hint over our own curve --- #
def test_429_honors_retry_after_seconds():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "5"})
        return httpx.Response(200, json={"ok": 1})

    sleeps: list[float] = []
    out = _client(handler, sleeps=sleeps, max_retries=2, backoff_base=0.2).get_json("/x", {})
    assert out.ok is True
    assert sleeps == [5.0]          # honored the header, NOT the 0.2 exponential curve


def test_retry_after_is_capped():
    def handler(req):
        return httpx.Response(429, headers={"Retry-After": "9999"})

    sleeps: list[float] = []
    _client(handler, sleeps=sleeps, max_retries=1, max_retry_after=2.0).get_json("/x", {})
    assert sleeps == [2.0]          # a hostile/huge value cannot stall the run


def test_429_without_retry_after_falls_back_to_exponential():
    def handler(req):
        return httpx.Response(429)

    sleeps: list[float] = []
    _client(handler, sleeps=sleeps, max_retries=1, backoff_base=0.2).get_json("/x", {})
    assert sleeps == [0.2]          # no header -> our exponential backoff


def test_5xx_uses_exponential_backoff():
    def handler(req):
        return httpx.Response(503)

    sleeps: list[float] = []
    _client(handler, sleeps=sleeps, max_retries=2, backoff_base=0.2).get_json("/x", {})
    assert sleeps == [0.2, 0.4]     # 0.2*2^0, 0.2*2^1


def test_503_with_retry_after_is_honored():
    def handler(req):
        return httpx.Response(503, headers={"Retry-After": "3"})

    sleeps: list[float] = []
    _client(handler, sleeps=sleeps, max_retries=1).get_json("/x", {})
    assert sleeps == [3.0]          # 503 can carry Retry-After too


def test_retry_after_http_date_is_honored():
    from datetime import timedelta
    from email.utils import format_datetime

    from dsi.common import utcnow

    future = format_datetime(utcnow() + timedelta(seconds=10))

    def handler(req):
        return httpx.Response(429, headers={"Retry-After": future})

    sleeps: list[float] = []
    _client(handler, sleeps=sleeps, max_retries=1, max_retry_after=60).get_json("/x", {})
    assert len(sleeps) == 1
    assert 5.0 <= sleeps[0] <= 10.5  # ~10s in the future (allow small timing slack)
