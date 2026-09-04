"""The metrics/trace spine: every call recorded, errors re-raised not swallowed,
cold/warm distinguished, token counts captured."""

from __future__ import annotations

import pytest

from dsi.trace.models import Outcome, TraceKind
from dsi.trace.spine import TraceSpine


def test_span_records_ok_event_with_fields(db):
    spine = TraceSpine(db)
    with spine.span(TraceKind.TOOL_CALL, "faers_search", "inv_1", "run_1") as rec:
        rec.cache_hit = True
        rec.records_read = 7
    events = spine.events_for("inv_1", "run_1")
    assert len(events) == 1
    e = events[0]
    assert e.name == "faers_search"
    assert e.outcome is Outcome.OK
    assert e.cache_hit is True
    assert e.records_read == 7
    assert e.latency_ms is not None and e.latency_ms >= 0


def test_model_call_captures_tokens(db):
    spine = TraceSpine(db)
    with spine.span(TraceKind.MODEL_CALL, "decide_next_action", "inv_1", "run_1",
                    context_size_tokens=512) as rec:
        rec.set_tokens(tokens_in=100, tokens_out=25)
    e = spine.events_for("inv_1", "run_1")[0]
    assert e.tokens_in == 100 and e.tokens_out == 25 and e.tokens_total == 125
    assert e.context_size_tokens == 512


def test_exception_is_recorded_and_reraised(db):
    spine = TraceSpine(db)
    with pytest.raises(ValueError):
        with spine.span(TraceKind.TOOL_CALL, "boom", "inv_1", "run_1"):
            raise ValueError("kaboom")
    e = spine.events_for("inv_1", "run_1")[0]
    assert e.outcome is Outcome.ERROR          # recorded
    assert e.error_type == "ValueError"        # not swallowed


def test_first_call_of_a_kind_is_cold_then_warm(db):
    spine = TraceSpine(db)
    with spine.span(TraceKind.MODEL_CALL, "m1", "inv_1", "run_1"):
        pass
    with spine.span(TraceKind.MODEL_CALL, "m2", "inv_1", "run_1"):
        pass
    events = spine.events_for("inv_1", "run_1")
    assert events[0].cold is True    # first model call = cold
    assert events[1].cold is False   # subsequent = warm
