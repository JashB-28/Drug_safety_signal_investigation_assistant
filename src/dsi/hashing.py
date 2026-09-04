"""Deterministic content hashing --- the backbone of dedup, caching, and the
selective-recompute dependency graph.

Two rules make these hashes trustworthy:
  1. Canonical JSON: keys sorted, no insignificant whitespace, UTF-8. The same
     logical content always serializes to the same bytes.
  2. Content only: callers hash the *content* of an evidence record, never its
     retrieval timestamp, so re-fetching identical content yields the same hash
     (that is how we detect "nothing actually changed").

This lives at package root (not in the Phase-5 analysis package) because both
the evidence layer (Phase 3) and the analysis layer (Phase 5) depend on it.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def _to_jsonable(data: Any) -> Any:
    """Convert Pydantic models to plain JSON-able structures; pass through the rest."""
    if isinstance(data, BaseModel):
        # mode="json" renders datetimes/enums/etc. to stable primitive forms.
        return data.model_dump(mode="json")
    return data


def canonical_json(data: Any) -> str:
    """Serialize to canonical JSON (sorted keys, compact separators, UTF-8)."""
    return json.dumps(
        _to_jsonable(data),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def canonical_hash(data: Any) -> str:
    """SHA-256 hex digest of the canonical JSON of ``data``.

    Deterministic across processes and machines for equal content.
    """
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def hash_of_hashes(hashes: list[str]) -> str:
    """Combine many content hashes into one stable input fingerprint.

    Order-independent (hashes are sorted first) so an analysis that consumes the
    same set of evidence records produces the same ``inputs_hash`` regardless of
    the order they were gathered in.
    """
    joined = "\n".join(sorted(hashes))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
