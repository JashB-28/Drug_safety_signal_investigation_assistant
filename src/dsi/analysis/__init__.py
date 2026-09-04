"""Deterministic analysis layer --- plain, tested Python. No LLM, no I/O.

Every function takes evidence records and returns a typed `AnalysisResult` that
records exactly which evidence it consumed (for the dependency graph). Hashing
(`dsi.hashing`) and staleness/change-detection (`dsi.persistence.staleness`) are
re-exported here so the whole analysis surface is reachable from one place.
"""

from dsi.analysis.aggregate import aggregate_reports
from dsi.analysis.dedup import collapse_to_latest_versions, resolve_duplicates
from dsi.analysis.normalize import canonical_drug, expand_drug, expand_event, normalize
from dsi.analysis.seriousness import summarize_missingness, summarize_seriousness
from dsi.analysis.temporal import compare_periods
from dsi.persistence.staleness import ChangeSet, detect_changes, snapshot_is_stale

__all__ = [
    "normalize", "expand_drug", "expand_event", "canonical_drug",
    "aggregate_reports",
    "summarize_seriousness", "summarize_missingness",
    "resolve_duplicates", "collapse_to_latest_versions",
    "compare_periods",
    "detect_changes", "ChangeSet", "snapshot_is_stale",
]
