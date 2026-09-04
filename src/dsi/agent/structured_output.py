"""Structured output with a bounded re-ask and a deterministic fallback.

Local models emit unreliable JSON. Every model output that must be structured goes
through here: call the model, extract and validate JSON against a Pydantic model;
on failure, re-ask ONCE with a terse error hint; if it still fails, return a
deterministic fallback and record the outcome as `invalid`. A malformed model
response therefore never crashes the graph and never passes through unchecked.

Every call is wrapped in a `model_call` span so tokens/latency/outcome land in the
trace spine, and the token counts are returned so the caller can update the budget.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

from dsi.agent.llm import LLMClient
from dsi.trace.models import Outcome, TraceKind
from dsi.trace.spine import TraceSpine

T = TypeVar("T", bound=BaseModel)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> dict | None:
    """Pull the first {...} object out of a model response (tolerates chatter around it)."""
    match = _JSON_RE.search(text)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except (ValueError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


@dataclass
class StructuredResult:
    value: BaseModel
    used_fallback: bool
    tokens_in: int
    tokens_out: int


def generate_structured(
    llm: LLMClient,
    spine: TraceSpine,
    *,
    model_cls: type[T],
    prompt: str,
    fallback: Callable[[], T],
    name: str,
    investigation_id: str,
    run_id: str,
    context_size_tokens: int | None = None,
    temperature: float = 0.0,
) -> StructuredResult:
    """Return a validated `model_cls` instance (or the fallback), plus token counts."""
    tokens_in = tokens_out = 0
    attempts = [prompt, prompt + "\n\nYour previous reply was not valid JSON matching the "
                                 "required schema. Reply with ONLY the JSON object."]
    with spine.span(TraceKind.MODEL_CALL, name, investigation_id, run_id,
                    context_size_tokens=context_size_tokens) as rec:
        for i, p in enumerate(attempts):
            resp = llm.complete(p, temperature=temperature)
            tokens_in += resp.tokens_in
            tokens_out += resp.tokens_out
            rec.retry_count = i
            obj = extract_json(resp.text)
            if obj is not None:
                try:
                    value = model_cls.model_validate(obj)
                    rec.set_tokens(tokens_in, tokens_out)
                    return StructuredResult(value, False, tokens_in, tokens_out)
                except ValidationError:
                    pass  # fall through to re-ask or fallback
        # both attempts failed -> deterministic fallback
        rec.set_tokens(tokens_in, tokens_out)
        rec.outcome = Outcome.INVALID
        return StructuredResult(fallback(), True, tokens_in, tokens_out)
