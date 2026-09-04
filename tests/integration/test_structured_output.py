"""Structured output: bounded re-ask then deterministic fallback; never crashes."""

from __future__ import annotations

from pydantic import BaseModel

from dsi.agent.llm import ScriptedLLM
from dsi.agent.structured_output import extract_json, generate_structured
from dsi.trace.models import Outcome
from dsi.trace.spine import TraceSpine


class Out(BaseModel):
    action: str
    rationale: str = ""


def _fallback() -> Out:
    return Out(action="stop", rationale="fallback")


def test_valid_json_first_try(db):
    llm = ScriptedLLM(responses=['{"action": "retrieve_faers", "rationale": "go"}'])
    r = generate_structured(llm, TraceSpine(db), model_cls=Out, prompt="p",
                            fallback=_fallback, name="d", investigation_id="i", run_id="r")
    assert r.value.action == "retrieve_faers"
    assert r.used_fallback is False
    assert len(llm.prompts) == 1


def test_reask_recovers_on_second_try(db):
    llm = ScriptedLLM(responses=["not json at all", '{"action": "stop", "rationale": "ok"}'])
    r = generate_structured(llm, TraceSpine(db), model_cls=Out, prompt="p",
                            fallback=_fallback, name="d", investigation_id="i", run_id="r")
    assert r.value.action == "stop"
    assert r.used_fallback is False
    assert len(llm.prompts) == 2  # one re-ask


def test_two_failures_use_deterministic_fallback(db):
    llm = ScriptedLLM(responses=["garbage", "still garbage"])
    spine = TraceSpine(db)
    r = generate_structured(llm, spine, model_cls=Out, prompt="p",
                            fallback=_fallback, name="d", investigation_id="i", run_id="r")
    assert r.used_fallback is True
    assert r.value.action == "stop"
    # the span records the invalid outcome (not a crash)
    ev = [e for e in spine.events_for("i", "r") if e.name == "d"][0]
    assert ev.outcome is Outcome.INVALID


def test_tokens_are_accumulated(db):
    llm = ScriptedLLM(responses=["bad", '{"action":"stop"}'], tokens_in=7, tokens_out=3)
    r = generate_structured(llm, TraceSpine(db), model_cls=Out, prompt="p",
                            fallback=_fallback, name="d", investigation_id="i", run_id="r")
    assert r.tokens_in == 14 and r.tokens_out == 6  # both attempts counted


def test_extract_json_tolerates_surrounding_text():
    assert extract_json('sure! {"a": 1} done') == {"a": 1}
    assert extract_json("no json here") is None
