"""Trace event schema --- one row per instrumented call.

Mirrors the `trace_events` table. The eval (Phase 9) reads these rows to compute
every measurement, so the fields here ARE the metric surface.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TraceKind(str, Enum):
    NODE = "node"
    TOOL_CALL = "tool_call"
    MODEL_CALL = "model_call"
    ANALYSIS = "analysis"


class Outcome(str, Enum):
    OK = "ok"
    ERROR = "error"
    EMPTY = "empty"
    INVALID = "invalid"
    REDUNDANT = "redundant"


class TraceEvent(BaseModel):
    """A single recorded span. Optional fields are populated where meaningful
    (tokens only for model calls, bytes/records for tool/IO calls, etc.)."""

    event_id: str
    investigation_id: str | None = None
    run_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None

    kind: TraceKind
    name: str
    ts_start: datetime
    ts_end: datetime | None = None
    latency_ms: float | None = None

    tokens_in: int | None = None
    tokens_out: int | None = None
    tokens_total: int | None = None
    context_size_tokens: int | None = None

    retry_count: int = 0
    cache_hit: bool = False
    outcome: Outcome | None = None
    error_type: str | None = None

    bytes_read: int = 0
    bytes_written: int = 0
    records_read: int = 0
    records_written: int = 0
    cold: bool = False

    attributes: dict = Field(default_factory=dict)
