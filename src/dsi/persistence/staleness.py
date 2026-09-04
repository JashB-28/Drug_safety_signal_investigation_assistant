"""Staleness / cache-invalidation triggers.

The assessment asks us to be explicit about *when* cached evidence or memory
becomes stale and *how* it is invalidated. There are three triggers:

  1. Query change     -- a different query is a different cache key (free; see cache.py).
  2. Source-snapshot  -- the underlying source was re-issued (new `source_version`
                         or a differing content hash for the same query).
  3. Label version    -- the product label changed (new SPL version / effective date).

This module provides the deterministic change-detection primitive the dependency
graph consumes. Phase 5's analysis-level staleness builds on `detect_changes`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChangeSet:
    """Which logical evidence slots were added / changed / removed between two snapshots.

    Keys are stable logical identifiers (e.g. 'label:boxed_warning', 'faers:R123');
    values are content hashes.
    """

    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)

    @property
    def any(self) -> bool:
        return bool(self.added or self.changed or self.removed)

    def affected_keys(self) -> list[str]:
        return sorted(set(self.added) | set(self.changed) | set(self.removed))


def detect_changes(old: dict[str, str], new: dict[str, str]) -> ChangeSet:
    """Compare two {logical_key -> content_hash} snapshots.

    'changed' means the same key now maps to a different content hash --- exactly
    the signal that a corrected report or updated label section arrived.
    """
    old_keys, new_keys = set(old), set(new)
    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed = sorted(k for k in (old_keys & new_keys) if old[k] != new[k])
    return ChangeSet(added=added, changed=changed, removed=removed)


def snapshot_is_stale(old_version: str | None, new_version: str | None) -> bool:
    """True when a source snapshot version differs (None vs a value counts as changed)."""
    return old_version != new_version
