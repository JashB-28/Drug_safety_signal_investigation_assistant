"""Snapshot cache for tool responses.

Two jobs:
  1. Reproducibility: once a tool response is snapshotted, the eval/demo replays
     it offline --- no live API dependence.
  2. Avoid redundant reads: on resume, a repeated tool request is a cache hit, so
     the (expensive) fetch function is never called again.

The cache key is a hash of (tool_name + canonical request), so a *different query*
is automatically a different key (query-change invalidation is free). Source-side
staleness (a label was re-issued, a new FAERS snapshot) is handled explicitly via
`invalidate()` / comparing `source_version` --- documented in staleness.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel

from dsi.common import utcnow
from dsi.hashing import canonical_hash
from dsi.persistence.db import Database


def make_cache_key(tool_name: str, request: BaseModel) -> str:
    """Stable key for a tool request. Same tool + same params => same key."""
    return canonical_hash({"tool": tool_name, "request": request.model_dump(mode="json")})


@dataclass
class CacheOutcome:
    """Result of a cache lookup/fetch, including whether it was a hit."""

    response_json: str
    cache_hit: bool
    content_hash: str


class SnapshotCache:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self, cache_key: str) -> CacheOutcome | None:
        row = self.db.conn.execute(
            "SELECT response_json, content_hash FROM snapshot_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if row is None:
            return None
        return CacheOutcome(response_json=row["response_json"], cache_hit=True,
                            content_hash=row["content_hash"])

    def put(self, cache_key: str, tool_name: str, request: BaseModel, response: BaseModel,
            source_version: str | None = None, retrieved_at: str | None = None) -> str:
        response_json = response.model_dump_json()
        content_hash = canonical_hash(response.model_dump(mode="json"))
        now = utcnow().isoformat()
        with self.db.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO snapshot_cache "
                "(cache_key, tool_name, request_json, response_json, source_version, "
                " content_hash, retrieved_at, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    cache_key, tool_name, request.model_dump_json(), response_json,
                    source_version, content_hash, retrieved_at or now, now,
                ),
            )
        return content_hash

    def invalidate(self, cache_key: str) -> None:
        """Explicitly drop a cache entry (e.g. a known source update / Scenario A)."""
        with self.db.transaction() as c:
            c.execute("DELETE FROM snapshot_cache WHERE cache_key = ?", (cache_key,))

    def get_or_fetch(
        self,
        tool_name: str,
        request: BaseModel,
        fetch_fn: Callable[[], BaseModel],
        response_type: type[BaseModel],
        source_version: str | None = None,
        cache_if: Callable[[BaseModel], bool] | None = None,
    ) -> tuple[BaseModel, bool]:
        """Return (response, cache_hit). Calls `fetch_fn` only on a cache miss.

        This is the primitive that makes resume cheap: the same request after a
        restart returns the snapshot without re-calling the tool. `cache_if` gates
        whether a fresh response is persisted --- e.g. don't cache a tool failure, so
        a later attempt actually retries instead of replaying the error.
        """
        key = make_cache_key(tool_name, request)
        hit = self.get(key)
        if hit is not None:
            return response_type.model_validate_json(hit.response_json), True
        response = fetch_fn()
        if cache_if is None or cache_if(response):
            self.put(key, tool_name, request, response, source_version=source_version)
        return response, False
