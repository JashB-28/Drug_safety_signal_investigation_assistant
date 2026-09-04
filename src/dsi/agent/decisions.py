"""The agentic decision: choose the next action from the current investigation state.

Genuine agency, bounded by determinism:
  * `available_actions` computes the LEGAL next actions from state (you cannot write
    a memo before analysis exists, cannot re-fetch a source already gathered, etc.).
  * The LLM CHOOSES among those legal actions and gives a rationale --- this is the
    real decision, logged with the exact state it saw.
  * If the model returns junk, `deterministic_policy` picks a sensible legal action.

The decision prompt contains only our own compact state SUMMARY (counts), never raw
retrieved text --- so it is small (context control) and carries no injection surface.
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from dsi.agent.llm import LLMClient
from dsi.agent.structured_output import generate_structured
from dsi.domain.state import ActionType, Decision
from dsi.trace.spine import TraceSpine

# Priority used by the deterministic fallback / policy.
_PRIORITY = [
    ActionType.RETRIEVE_FAERS, ActionType.RETRIEVE_LABEL, ActionType.RETRIEVE_LITERATURE,
    ActionType.RUN_ANALYSIS, ActionType.CHECK_SUFFICIENCY, ActionType.DETECT_CONFLICTS,
    ActionType.GENERATE_MEMO, ActionType.STOP,
]

_SOURCE_ACTION = {
    "faers": ActionType.RETRIEVE_FAERS,
    "label": ActionType.RETRIEVE_LABEL,
    "literature": ActionType.RETRIEVE_LITERATURE,
}


class DecisionOutput(BaseModel):
    action: str
    rationale: str = ""


def available_actions(
    *,
    pending_sources: set[str],
    have_evidence: bool,
    analyses_done: bool,
    sufficiency_checked: bool,
    sufficient: bool | None,
    conflicts_done: bool,
) -> list[ActionType]:
    acts: list[ActionType] = []
    for source in ("faers", "label", "literature"):
        if source in pending_sources:
            acts.append(_SOURCE_ACTION[source])
    # Analyze once we have some evidence, or once retrieval is exhausted (so an
    # empty-evidence run still reaches sufficiency and documents WHY it stopped).
    if not analyses_done and (have_evidence or not pending_sources):
        acts.append(ActionType.RUN_ANALYSIS)
    if analyses_done and not sufficiency_checked:
        acts.append(ActionType.CHECK_SUFFICIENCY)
    if analyses_done and not conflicts_done:
        acts.append(ActionType.DETECT_CONFLICTS)
    if analyses_done and sufficiency_checked:
        if sufficient:
            acts.append(ActionType.GENERATE_MEMO)
        acts.append(ActionType.STOP)
    if not acts:
        acts.append(ActionType.STOP)
    return acts


def deterministic_policy(available: list[ActionType]) -> ActionType:
    """Pick the highest-priority legal action (used as the model's fallback)."""
    for action in _PRIORITY:
        if action in available:
            return action
    return ActionType.STOP


def decide(
    *,
    llm: LLMClient,
    spine: TraceSpine,
    investigation_id: str,
    run_id: str,
    step_index: int,
    observed_state: dict,
    available: list[ActionType],
) -> tuple[Decision, int, int]:
    """Ask the model to choose; validate; fall back deterministically. Returns the
    logged Decision plus (tokens_in, tokens_out) for budget accounting."""
    available_values = [a.value for a in available]
    instruction = (
        "Decide the single next action for this drug-safety investigation, based on "
        "the STATE below. Choose exactly one action from AVAILABLE_ACTIONS.\n"
        f"STATE = {json.dumps(observed_state)}\n"
        f"AVAILABLE_ACTIONS = {available_values}\n"
        'Reply with ONLY JSON: {"action": "<one of AVAILABLE_ACTIONS>", "rationale": "<why>"}.'
    )
    fallback_action = deterministic_policy(available)
    result = generate_structured(
        llm, spine,
        model_cls=DecisionOutput, prompt=instruction,
        fallback=lambda: DecisionOutput(action=fallback_action.value,
                                        rationale="deterministic fallback (model output invalid)"),
        name="decide_next_action", investigation_id=investigation_id, run_id=run_id,
    )
    chosen = result.value.action
    try:
        action = ActionType(chosen)
    except ValueError:
        action = fallback_action
    if action not in available:  # model picked an illegal action -> constrain
        action = fallback_action

    decision = Decision(
        step_index=step_index,
        observed_state=observed_state,
        chosen_action=action,
        rationale=result.value.rationale or "",
        alternatives_considered=available,
    )
    return decision, result.tokens_in, result.tokens_out
