"""Bounded HTTP client: timeout + bounded retries with backoff, and conversion of
every failure into a structured `ToolError` (never an exception that escapes).

Retry policy (deliberately small and explicit --- exactly three triggers):
  * timeout / connection error -> retry, exponential backoff.
  * HTTP 5xx                    -> retry; honor `Retry-After` if the server sends
                                   one (503 sometimes does), else exponential.
  * HTTP 429 (rate limited)     -> retry, but honor the server's `Retry-After`
                                   header when present, else exponential. Both
                                   openFDA and NCBI eutils return timing hints on
                                   throttling; backing off on our own curve and
                                   ignoring the header is how you get throttled
                                   harder, so we prefer the header.
  * HTTP 404                    -> terminal (openFDA uses it to mean "no matches").
  * any other 4xx              -> terminal (a bad request will not fix itself).

`Retry-After` is capped by `max_retry_after` so a hostile/huge value cannot stall
the run. All sleeping goes through an injectable `sleep_fn` so tests run instantly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Callable, Protocol

import httpx

from dsi.common import utcnow
from dsi.domain.tools import ToolError, ToolErrorCode


@dataclass
class HttpOutcome:
    """The result of one (retried) HTTP GET."""

    ok: bool
    status_code: int | None
    json: dict | None
    error: ToolError | None
    retry_count: int
    latency_ms: float


class HttpClient(Protocol):
    """The minimal surface the tools depend on --- so tests can inject a fake."""

    def get_json(self, path: str, params: dict) -> HttpOutcome: ...


class BoundedHttpClient:
    """Real HTTP client with bounded timeout/retries. `transport` is injectable so
    tests can drive it with `httpx.MockTransport` without touching the network."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        max_retries: int = 2,
        backoff_base: float = 0.2,
        respect_retry_after: bool = True,
        max_retry_after: float = 30.0,
        sleep_fn: Callable[[float], None] = time.sleep,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.respect_retry_after = respect_retry_after
        self.max_retry_after = max_retry_after
        self._sleep = sleep_fn
        self._client = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def get_json(self, path: str, params: dict) -> HttpOutcome:
        start = time.perf_counter()
        attempt = 0
        last_error: ToolError | None = None
        last_status: int | None = None

        while attempt <= self.max_retries:
            retry_after: float | None = None
            try:
                resp = self._client.get(path, params=params)
            except httpx.TimeoutException:
                last_error = ToolError(code=ToolErrorCode.TIMEOUT, message="request timed out",
                                       retryable=True)
            except httpx.HTTPError as exc:
                last_error = ToolError(code=ToolErrorCode.HTTP_ERROR, message=str(exc),
                                       retryable=True)
            else:
                last_status = resp.status_code
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except ValueError:
                        return self._done(False, resp.status_code,
                                          ToolError(code=ToolErrorCode.MALFORMED_RESPONSE,
                                                    message="response body was not valid JSON",
                                                    retryable=False),
                                          attempt, start, json=None)
                    return self._done(True, resp.status_code, None, attempt, start, json=data)
                # non-200 status handling
                code, retryable = self._classify_status(resp.status_code)
                details = {"status": str(resp.status_code)}
                if retryable and self.respect_retry_after:
                    retry_after = self._retry_after_seconds(resp)
                    if retry_after is not None:
                        details["retry_after"] = str(retry_after)
                last_error = ToolError(code=code, message=f"HTTP {resp.status_code}",
                                       retryable=retryable, details=details)
                if not retryable:
                    return self._done(False, resp.status_code, last_error, attempt, start, json=None)

            # retry path (a retryable error occurred): honor Retry-After if given,
            # otherwise exponential backoff.
            if attempt < self.max_retries:
                if retry_after is not None:
                    self._sleep(min(retry_after, self.max_retry_after))
                else:
                    self._sleep(self.backoff_base * (2 ** attempt))
            attempt += 1

        return self._done(False, last_status, last_error, attempt - 1, start, json=None)

    @staticmethod
    def _classify_status(status: int) -> tuple[ToolErrorCode, bool]:
        if status == 429:
            return ToolErrorCode.RATE_LIMITED, True
        if status == 404:
            return ToolErrorCode.NOT_FOUND, False   # source-specific meaning (openFDA: empty)
        if 500 <= status < 600:
            return ToolErrorCode.HTTP_ERROR, True
        return ToolErrorCode.HTTP_ERROR, False

    @staticmethod
    def _retry_after_seconds(resp: httpx.Response) -> float | None:
        """Parse a `Retry-After` header: either delta-seconds or an HTTP-date.
        Returns None if absent/unparseable, or a non-negative float otherwise."""
        raw = resp.headers.get("Retry-After")
        if not raw:
            return None
        raw = raw.strip()
        if raw.isdigit():
            return float(raw)
        try:
            when = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
        if when is None:
            return None
        if when.tzinfo is None:  # RFC dates should be GMT; be safe if tz is missing
            from datetime import timezone
            when = when.replace(tzinfo=timezone.utc)
        delta = (when - utcnow()).total_seconds()
        return max(0.0, delta)

    @staticmethod
    def _done(ok, status, error, retry_count, start, json) -> HttpOutcome:
        return HttpOutcome(
            ok=ok, status_code=status, json=json, error=error,
            retry_count=retry_count, latency_ms=(time.perf_counter() - start) * 1000.0,
        )
