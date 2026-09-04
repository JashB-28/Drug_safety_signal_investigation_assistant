"""Agent state --- the working memory the LangGraph agent carries between nodes.

Two things here are load-bearing for the assessment:

  * `Decision` records the *observed state the choice was based on* alongside the
    chosen action. This is how we demonstrate genuine agentic behavior: the trace
    shows the agent decided X because the state looked like Y, not because a script
    said so.

  * `Budget` makes the constrained run (Scenario C) a first-class concept. Token
    accounting lives here so the agent can notice it is approaching a limit and
    replan (summarize, drop context, stop) rather than blowing the budget.

The state deliberately holds *ids and small summaries*, not the full evidence
payloads. Full evidence lives in SQLite (Phase 3); the context builder (Phase 6)
selects a bounded slice for each model call. This keeps model context small.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from dsi.common import new_id, utcnow
from dsi.domain.investigation import ReviewPeriod


class InvestigationStatus(str, Enum):
    INITIALIZED = "initialized"
    GATHERING = "gathering"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    HALTED_INSUFFICIENT_EVIDENCE = "halted_insufficient_evidence"
    FAILED = "failed"


class ActionType(str, Enum):
    """The next actions the agent may choose among."""

    RETRIEVE_FAERS = "retrieve_faers"
    RETRIEVE_LABEL = "retrieve_label"
    RETRIEVE_LITERATURE = "retrieve_literature"
    RUN_ANALYSIS = "run_analysis"
    CHECK_SUFFICIENCY = "check_sufficiency"
    DETECT_CONFLICTS = "detect_conflicts"
    GENERATE_MEMO = "generate_memo"
    STOP = "stop"


class Decision(BaseModel):
    """One agentic decision, logged with the state it was based on."""

    decision_id: str = Field(default_factory=lambda: new_id("dec"))
    step_index: int
    observed_state: dict = Field(
        description="Compact snapshot of the state the agent saw when deciding (for the trace)."
    )
    chosen_action: ActionType
    rationale: str = Field(description="The agent's stated reason (LLM prose).")
    alternatives_considered: list[ActionType] = Field(default_factory=list)
    decided_at: datetime = Field(default_factory=utcnow)


class Budget(BaseModel):
    """Token / context budget for a run. The constrained run tightens these."""

    max_total_tokens: int | None = None
    max_context_tokens: int | None = None
    total_tokens_used: int = 0
    context_tokens_peak: int = 0

    def total_exceeded(self) -> bool:
        return self.max_total_tokens is not None and self.total_tokens_used >= self.max_total_tokens

    def remaining_total(self) -> int | None:
        if self.max_total_tokens is None:
            return None
        return max(0, self.max_total_tokens - self.total_tokens_used)


class AgentState(BaseModel):
    """The full state persisted per run so an investigation can resume after restart.

    Holds references (ids) and small summaries, not bulk evidence. `retry_counts`
    is keyed by action name so bounded-retry logic survives a restart.
    """

    investigation_id: str
    run_id: str = Field(default_factory=lambda: new_id("run"))
    status: InvestigationStatus = InvestigationStatus.INITIALIZED

    drug: str
    event: str
    review_period: ReviewPeriod

    # Normalized forms (filled by the normalization analysis; kept separate from raw).
    normalized_drug_names: list[str] = Field(default_factory=list)
    normalized_event_terms: list[str] = Field(default_factory=list)

    # References into persistent storage --- not the payloads themselves.
    evidence_ids: list[str] = Field(default_factory=list)
    analysis_result_ids: list[str] = Field(default_factory=list)

    decisions: list[Decision] = Field(default_factory=list)
    retry_counts: dict[str, int] = Field(default_factory=dict)
    next_action: ActionType | None = None

    budget: Budget = Field(default_factory=Budget)
    step_index: int = 0
    updated_at: datetime = Field(default_factory=utcnow)

    def record_decision(self, decision: Decision) -> None:
        """Append a decision and advance the step counter (used by the agent nodes)."""
        self.decisions.append(decision)
        self.next_action = decision.chosen_action
        self.step_index += 1
        self.updated_at = utcnow()
