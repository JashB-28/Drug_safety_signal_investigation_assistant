"""Persistence layer: SQLite storage, snapshot cache, and the dependency graph."""

from dsi.persistence.cache import SnapshotCache, make_cache_key
from dsi.persistence.db import Database
from dsi.persistence.depgraph import (
    DependencyGraph,
    DepGraphRepo,
    DepNode,
    RecomputeReport,
)
from dsi.persistence.repositories import (
    AnalysisRepo,
    EvidenceRepo,
    InvestigationRepo,
    MemoRepo,
    StateRepo,
)
from dsi.persistence.staleness import ChangeSet, detect_changes, snapshot_is_stale

__all__ = [
    "Database",
    "InvestigationRepo", "EvidenceRepo", "AnalysisRepo", "MemoRepo", "StateRepo",
    "SnapshotCache", "make_cache_key",
    "DependencyGraph", "DepNode", "DepGraphRepo", "RecomputeReport",
    "ChangeSet", "detect_changes", "snapshot_is_stale",
]
