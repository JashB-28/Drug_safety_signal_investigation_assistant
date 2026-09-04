"""The trace spine: a `span()` context manager that records one row per call.

Usage (the single pattern used everywhere):

    with spine.span(TraceKind.TOOL_CALL, "faers_search", inv_id, run_id) as rec:
        result = do_the_call()
        rec.cache_hit = result.cache_hit
        rec.retry_count = result.retry_count
        rec.records_read = len(result.data.reports)
        if not result.ok:
            rec.outcome = Outcome.ERROR
            rec.error_type = result.error.code.value

On exit the span computes latency, marks cold vs warm (first call of a kind in
this process is cold), and writes the row. An exception inside the block is
recorded as `outcome=error` and re-raised (never swallowed). Phase 4/6 wrap the
tool and model clients so *every* such call flows through here.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field

from dsi.common import new_id, utcnow
from dsi.persistence.db import Database
from dsi.trace.models import Outcome, TraceEvent, TraceKind


@dataclass
class SpanRecorder:
    """Mutable handle the caller fills in during a span."""

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
    attributes: dict = field(default_factory=dict)

    def set_tokens(self, tokens_in: int, tokens_out: int) -> None:
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.tokens_total = tokens_in + tokens_out


class TraceSpine:
    """Writes trace events to SQLite. One instance per process is typical."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self._warm_kinds: set[str] = set()  # first call of a kind is "cold"

    @contextmanager
    def span(
        self,
        kind: TraceKind,
        name: str,
        investigation_id: str | None = None,
        run_id: str | None = None,
        parent_span_id: str | None = None,
        context_size_tokens: int | None = None,
    ) -> Generator[SpanRecorder, None, None]:
        rec = SpanRecorder(context_size_tokens=context_size_tokens)
        span_id = new_id("span")
        ts_start = utcnow()
        cold = kind.value not in self._warm_kinds
        self._warm_kinds.add(kind.value)
        start_perf = time.perf_counter()
        error: BaseException | None = None
        try:
            yield rec
        except BaseException as exc:  # record, then re-raise --- never swallow
            error = exc
            rec.outcome = Outcome.ERROR
            rec.error_type = type(exc).__name__
        finally:
            latency_ms = (time.perf_counter() - start_perf) * 1000.0
            if rec.outcome is None:
                rec.outcome = Outcome.OK
            if rec.tokens_total is None and (rec.tokens_in is not None or rec.tokens_out is not None):
                rec.tokens_total = (rec.tokens_in or 0) + (rec.tokens_out or 0)
            event = TraceEvent(
                event_id=new_id("evt"),
                investigation_id=investigation_id,
                run_id=run_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                kind=kind,
                name=name,
                ts_start=ts_start,
                ts_end=utcnow(),
                latency_ms=latency_ms,
                tokens_in=rec.tokens_in,
                tokens_out=rec.tokens_out,
                tokens_total=rec.tokens_total,
                context_size_tokens=rec.context_size_tokens,
                retry_count=rec.retry_count,
                cache_hit=rec.cache_hit,
                outcome=rec.outcome,
                error_type=rec.error_type,
                bytes_read=rec.bytes_read,
                bytes_written=rec.bytes_written,
                records_read=rec.records_read,
                records_written=rec.records_written,
                cold=cold,
                attributes=rec.attributes,
            )
            self._write(event)
        if error is not None:
            raise error

    def _write(self, e: TraceEvent) -> None:
        import json
        with self.db.transaction() as c:
            c.execute(
                "INSERT INTO trace_events ("
                "event_id, investigation_id, run_id, span_id, parent_span_id, kind, name, "
                "ts_start, ts_end, latency_ms, tokens_in, tokens_out, tokens_total, "
                "context_size_tokens, retry_count, cache_hit, outcome, error_type, "
                "bytes_read, bytes_written, records_read, records_written, cold, attributes_json"
                ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    e.event_id, e.investigation_id, e.run_id, e.span_id, e.parent_span_id,
                    e.kind.value, e.name, e.ts_start.isoformat(),
                    e.ts_end.isoformat() if e.ts_end else None, e.latency_ms,
                    e.tokens_in, e.tokens_out, e.tokens_total, e.context_size_tokens,
                    e.retry_count, int(e.cache_hit), e.outcome.value if e.outcome else None,
                    e.error_type, e.bytes_read, e.bytes_written, e.records_read,
                    e.records_written, int(e.cold), json.dumps(e.attributes),
                ),
            )

    # -- read side (used by the eval in Phase 9) ---------------------------- #
    def events_for(self, investigation_id: str, run_id: str | None = None) -> list[TraceEvent]:
        import json
        sql = "SELECT * FROM trace_events WHERE investigation_id = ?"
        params: list = [investigation_id]
        if run_id is not None:
            sql += " AND run_id = ?"
            params.append(run_id)
        sql += " ORDER BY ts_start"
        rows = self.db.conn.execute(sql, params).fetchall()
        out: list[TraceEvent] = []
        for r in rows:
            d = dict(r)
            d["cache_hit"] = bool(d["cache_hit"])
            d["cold"] = bool(d["cold"])
            d["attributes"] = json.loads(d.pop("attributes_json") or "{}")
            out.append(TraceEvent.model_validate(d))
        return out
