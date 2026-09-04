"""Shared helpers for the challenge scenarios: rehydrating a run's analyses and
reading model-token totals from the trace spine."""

from __future__ import annotations

from dsi.agent.graph import RunContext
from dsi.analysis.normalize import normalize
from dsi.domain.analysis import (
    AggregationResult,
    DedupResult,
    MissingnessSummary,
    NormalizationResult,
    SeriousnessSummary,
    TemporalComparison,
)
from dsi.domain.investigation import Investigation
from dsi.trace.models import TraceKind

_BY_KIND = {
    "normalization": NormalizationResult, "aggregation": AggregationResult,
    "seriousness": SeriousnessSummary, "missingness": MissingnessSummary,
    "dedup": DedupResult, "temporal": TemporalComparison,
}


def load_run_analyses(ctx: RunContext, inv: Investigation, run_id: str) -> dict:
    """Rehydrate a run's analysis results into a {kind: result} dict."""
    out: dict = {}
    for row in ctx.analyses.get_raw_for_run(inv.investigation_id, run_id):
        cls = _BY_KIND.get(row["kind"])
        if cls is not None:
            out[row["kind"]] = cls.model_validate_json(row["result_json"])
    out.setdefault("normalization", normalize(inv.drug, inv.event, inv.investigation_id))
    return out


def model_tokens_for_run(ctx: RunContext, inv: Investigation, run_id: str) -> int:
    """Total model tokens spent in a run (from the trace spine)."""
    return sum(e.tokens_total or 0
               for e in ctx.spine.events_for(inv.investigation_id, run_id)
               if e.kind is TraceKind.MODEL_CALL)
