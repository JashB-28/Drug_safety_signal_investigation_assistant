"""End-to-end agent: happy path, empty-evidence safe stop, tool-failure retry,
agentic decisions, and full-trace persistence. Runs offline with a scripted LLM."""

from __future__ import annotations

from dsi.agent.graph import RunContext, run_investigation
from dsi.agent.llm import ScriptedLLM
from dsi.domain.memo import MemoSectionKind, MemoValidationStatus
from dsi.domain.state import ActionType, InvestigationStatus
from dsi.mcp_server.server import ToolClients
from dsi.trace.models import Outcome, TraceKind


def _clients(http, *, faers=None, label=None, event_extra=None):
    """openFDA (event+label) and PubMed (esearch+esummary) routed by path."""
    return ToolClients(
        openfda=http.Routed({
            "/drug/event": (event_extra or [http.ok(http.faers())]),
            "/drug/label": [http.ok(label if label is not None else http.label())],
        }),
        pubmed=http.Routed({
            "/esearch": [http.ok(http.esearch())],
            "/esummary": [http.ok(http.esummary())],
        }),
    )


def test_happy_path_produces_valid_complete_memo(db, investigation, http):
    ctx = RunContext(db=db, llm=ScriptedLLM(), tool_clients=_clients(http))
    result = run_investigation(ctx, investigation)

    assert result.state.status is InvestigationStatus.COMPLETED
    memo = ctx.memos.get_for_run(investigation.investigation_id, result.state.run_id)
    assert memo is not None
    assert memo.validation_status is MemoValidationStatus.PASSED
    assert {s.kind for s in memo.sections} == set(MemoSectionKind)   # all required sections
    assert memo.uncited_material_claims() == []                      # citation completeness

    events = ctx.spine.events_for(investigation.investigation_id, result.state.run_id)
    assert any(e.kind is TraceKind.TOOL_CALL for e in events)        # full trace persisted
    assert any(e.kind is TraceKind.MODEL_CALL for e in events)
    assert ctx.evidence.count_for(investigation.investigation_id) >= 2


def test_empty_evidence_stops_safely_and_documents_it(db, investigation, http):
    clients = ToolClients(
        openfda=http.Routed({"/drug/event": [http.empty404()], "/drug/label": [http.empty404()]}),
        pubmed=http.Routed({"/esearch": [http.ok(http.esearch(ids=[]))]}),
    )
    ctx = RunContext(db=db, llm=ScriptedLLM(), tool_clients=clients)
    result = run_investigation(ctx, investigation)

    assert result.state.status is InvestigationStatus.HALTED_INSUFFICIENT_EVIDENCE
    memo = ctx.memos.get_for_run(investigation.investigation_id, result.state.run_id)
    assert memo is not None and memo.validation_status is MemoValidationStatus.PASSED
    limitations = next(s for s in memo.sections if s.kind is MemoSectionKind.LIMITATIONS)
    assert any("No adverse-event reports" in c.text for c in limitations.claims)


def test_tool_failure_retries_then_succeeds(db, investigation, http):
    # first FAERS call times out (retryable), second succeeds
    clients = _clients(http, event_extra=[http.timeout(), http.ok(http.faers())])
    ctx = RunContext(db=db, llm=ScriptedLLM(), tool_clients=clients)
    result = run_investigation(ctx, investigation)

    assert result.state.status is InvestigationStatus.COMPLETED
    faers_events = [e for e in ctx.spine.events_for(investigation.investigation_id, result.state.run_id)
                    if e.name == "faers_search"]
    assert len(faers_events) == 2                       # retried at the agent level
    assert faers_events[0].outcome is Outcome.ERROR
    assert faers_events[1].outcome is Outcome.OK
    assert result.state.retry_counts.get("tool:faers") == 1


def test_decisions_are_agentic_and_logged(db, investigation, http):
    # the model chooses to fetch the label first; the agent honors that legal choice
    llm = ScriptedLLM(routes=[("AVAILABLE_ACTIONS",
                               '{"action": "retrieve_label", "rationale": "label first"}')])
    ctx = RunContext(db=db, llm=llm, tool_clients=_clients(http))
    result = run_investigation(ctx, investigation)

    first = result.state.decisions[0]
    assert first.chosen_action is ActionType.RETRIEVE_LABEL     # LLM decision used
    assert first.rationale == "label first"
    assert "pending_sources" in first.observed_state           # decided from real state
    assert result.state.status is InvestigationStatus.COMPLETED


def test_model_and_tool_calls_all_recorded(db, investigation, http):
    ctx = RunContext(db=db, llm=ScriptedLLM(), tool_clients=_clients(http))
    result = run_investigation(ctx, investigation)
    events = ctx.spine.events_for(investigation.investigation_id, result.state.run_id)
    names = {e.name for e in events}
    assert "decide_next_action" in names        # model decisions traced
    assert "faers_search" in names              # tool calls traced
    # every event carries an outcome
    assert all(e.outcome is not None for e in events)
