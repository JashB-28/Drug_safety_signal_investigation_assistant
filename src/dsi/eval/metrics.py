"""Aggregate the trace spine into the assessment's required measurements.

Everything here READS `trace_events` --- the spine is the single source of truth, so
these numbers cannot drift from what actually happened. Where a metric cannot be
measured reliably (e.g. VRAM on CPU-only), we say so explicitly rather than
fabricate a value.
"""

from __future__ import annotations

from statistics import median

from dsi.agent.graph import RunContext
from dsi.domain.investigation import Investigation
from dsi.trace.models import Outcome, TraceKind


def percentile(values: list[float], p: float) -> float | None:
    """Simple nearest-rank percentile (p in [0,1]); None if no data."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    k = max(0, min(len(ordered) - 1, int(round(p * (len(ordered) - 1)))))
    return round(ordered[k], 2)


def latency_summary(latencies_ms: list[float]) -> dict:
    return {
        "n": len(latencies_ms),
        "p50_ms": percentile(latencies_ms, 0.50),
        "p90_ms": percentile(latencies_ms, 0.90),
        "p95_ms": percentile(latencies_ms, 0.95),
        "min_ms": round(min(latencies_ms), 2) if latencies_ms else None,
        "max_ms": round(max(latencies_ms), 2) if latencies_ms else None,
    }


def compute_run_metrics(ctx: RunContext, inv: Investigation, run_id: str) -> dict:
    """Token, tool-call, cache, and I/O metrics for a single run, from the spine."""
    events = ctx.spine.events_for(inv.investigation_id, run_id)
    model = [e for e in events if e.kind is TraceKind.MODEL_CALL]
    tool = [e for e in events if e.kind is TraceKind.TOOL_CALL]

    tokens_in = sum(e.tokens_in or 0 for e in model)
    tokens_out = sum(e.tokens_out or 0 for e in model)
    retry_tokens = sum(e.tokens_total or 0 for e in model if e.retry_count > 0)

    def count(events_, **pred) -> int:
        return sum(1 for e in events_ if all(getattr(e, k) == v for k, v in pred.items()))

    return {
        "model_calls": len(model),
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "tokens_total": tokens_in + tokens_out,
        "context_size_max": max((e.context_size_tokens or 0 for e in model), default=0),
        "retry_tokens": retry_tokens,
        "tool_calls_attempted": len(tool),
        "tool_calls_succeeded": count(tool, outcome=Outcome.OK),
        "tool_calls_failed": count(tool, outcome=Outcome.ERROR),
        "tool_calls_empty": count(tool, outcome=Outcome.EMPTY),
        "tool_calls_retried": sum(1 for e in tool if e.retry_count > 0),
        "model_calls_invalid": count(model, outcome=Outcome.INVALID),
        "cache_hits": sum(1 for e in events if e.cache_hit),
        "records_read": sum(e.records_read for e in events),
        "records_written": sum(e.records_written for e in events),
        "bytes_read": sum(e.bytes_read for e in events),
        "bytes_written": sum(e.bytes_written for e in events),
    }


def peak_memory_mb() -> float:
    """Process resident set size in MB (peak proxy). VRAM is reported separately."""
    import psutil
    return round(psutil.Process().memory_info().rss / (1024 * 1024), 1)
