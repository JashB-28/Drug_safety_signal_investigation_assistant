"""Deterministic analysis results --- category (b) in the three-way separation.

These are produced by plain, tested Python (Phase 5), never by the LLM. Each
result records exactly which evidence it consumed (`consumed_evidence_hashes`)
and a fingerprint of those inputs (`inputs_hash`) plus its own `output_hash`.
That is what lets the dependency graph (Phase 3) recompute *only* the results
whose inputs changed, and short-circuit when a recomputed output is unchanged.

Phase 2 defines the schemas and the shared provenance base; the computation that
fills them lives in `dsi.analysis` (Phase 5).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from dsi.common import new_id, utcnow
from dsi.hashing import canonical_hash, hash_of_hashes


class AnalysisKind(str, Enum):
    NORMALIZATION = "normalization"
    AGGREGATION = "aggregation"
    SERIOUSNESS = "seriousness"
    MISSINGNESS = "missingness"
    DEDUP = "dedup"
    TEMPORAL = "temporal"
    CONFLICT = "conflict"


class AnalysisResult(BaseModel):
    """Base for every deterministic analysis result.

    Subclasses add a typed `data`-style body; this base carries the identity and
    dependency-tracking fields common to all of them.
    """

    result_id: str = Field(default_factory=lambda: new_id("ana"))
    investigation_id: str
    kind: AnalysisKind
    consumed_evidence_hashes: list[str] = Field(
        default_factory=list,
        description="Content hashes of the evidence records this result consumed (sorted).",
    )
    inputs_hash: str = Field(description="Fingerprint of the consumed inputs (order-independent).")
    output_hash: str = Field(description="Hash of this result's own output body.")
    computed_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------- #
# Concrete result bodies
# --------------------------------------------------------------------------- #
class NormalizationResult(AnalysisResult):
    kind: Literal[AnalysisKind.NORMALIZATION] = AnalysisKind.NORMALIZATION
    raw_drug: str
    normalized_drug_names: list[str] = Field(default_factory=list)
    raw_event: str
    normalized_event_terms: list[str] = Field(default_factory=list)


class AggregationResult(AnalysisResult):
    kind: Literal[AnalysisKind.AGGREGATION] = AnalysisKind.AGGREGATION
    total_reports: int = 0
    by_year: dict[str, int] = Field(default_factory=dict)
    by_reaction_term: dict[str, int] = Field(default_factory=dict)
    by_seriousness: dict[str, int] = Field(default_factory=dict)


class SeriousnessSummary(AnalysisResult):
    kind: Literal[AnalysisKind.SERIOUSNESS] = AnalysisKind.SERIOUSNESS
    total_reports: int = 0
    serious: int = 0
    non_serious: int = 0
    seriousness_unknown: int = 0
    # Counts per specific seriousness criterion (death, hospitalization, ...).
    by_criterion: dict[str, int] = Field(default_factory=dict)


class MissingnessSummary(AnalysisResult):
    kind: Literal[AnalysisKind.MISSINGNESS] = AnalysisKind.MISSINGNESS
    total_reports: int = 0
    # field name -> number of reports missing it.
    missing_counts: dict[str, int] = Field(default_factory=dict)
    # field name -> fraction missing in [0, 1].
    missing_fraction: dict[str, float] = Field(default_factory=dict)


class DuplicateGroupCertainty(str, Enum):
    """Confirmed vs likely --- we never assert a duplicate when certainty is impossible."""

    CONFIRMED = "confirmed"   # same report_id, different versions (a true version chain)
    LIKELY = "likely"         # heuristic match (shared key fields) but not certain


class DuplicateGroup(BaseModel):
    certainty: DuplicateGroupCertainty
    evidence_ids: list[str]
    reason: str = Field(description="Why these were grouped (e.g. 'same report_id v1->v2').")


class DedupResult(AnalysisResult):
    kind: Literal[AnalysisKind.DEDUP] = AnalysisKind.DEDUP
    groups: list[DuplicateGroup] = Field(default_factory=list)
    unique_report_count: int = 0


class PeriodCount(BaseModel):
    label: str = Field(description="Sub-period label, e.g. '2019' or '2020-Q1'.")
    report_count: int


class TemporalComparison(AnalysisResult):
    kind: Literal[AnalysisKind.TEMPORAL] = AnalysisKind.TEMPORAL
    period_counts: list[PeriodCount] = Field(default_factory=list)
    # Descriptive only --- report-count direction, NEVER a rate or incidence.
    direction: Literal["increase", "decrease", "flat", "insufficient_data"] = "insufficient_data"
    note: str = Field(
        default="Counts of spontaneous reports only; not incidence or occurrence rates.",
    )


class ConflictFinding(AnalysisResult):
    kind: Literal[AnalysisKind.CONFLICT] = AnalysisKind.CONFLICT
    description: str = Field(description="What disagrees, stated without forcing consensus.")
    positions: list[str] = Field(
        default_factory=list,
        description="Each source's position, with its date and limitations, preserved separately.",
    )
    unresolved: bool = True


def make_provenance_fields(consumed_hashes: list[str], output_body: Any) -> dict:
    """Helper for Phase-5 compute functions: produce the dependency-tracking fields.

    `output_body` is the *output data only* (a dict or small model of the computed
    values) --- NOT the full `AnalysisResult`, which would be circular because it
    contains `output_hash` itself. Returns a dict with `consumed_evidence_hashes`,
    `inputs_hash`, and `output_hash` ready to splat into an `AnalysisResult`
    subclass constructor.
    """
    sorted_hashes = sorted(consumed_hashes)
    return {
        "consumed_evidence_hashes": sorted_hashes,
        "inputs_hash": hash_of_hashes(sorted_hashes),
        "output_hash": canonical_hash(output_body),
    }
