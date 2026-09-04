"""The single investigation agent, orchestrated with LangGraph.

Flow: initialize -> normalize -> (decide -> action)* -> finalize.
`decide` is the agentic node: the LLM chooses the next legal action from the current
state; deterministic guards bound it (step/budget limits, legal-action set, safe
termination). Retrieval nodes handle tool failure (bounded agent-level retry via
re-offering the source), empty results, and caching. Analysis/sufficiency/conflict
nodes are deterministic. `finalize` builds and validates the memo. The full trace is
persisted throughout via the metrics spine, and state is saved so a run can resume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from dsi.agent import conflicts as conflicts_mod
from dsi.agent import sufficiency as sufficiency_mod
from dsi.agent.context_builder import case_line, render_prompt, select_serious_cases
from dsi.agent.decisions import available_actions, decide
from dsi.agent.llm import LLMClient
from dsi.agent.structured_output import generate_structured
from dsi.analysis.aggregate import aggregate_reports
from dsi.analysis.dedup import collapse_to_latest_versions, resolve_duplicates
from dsi.analysis.normalize import normalize
from dsi.analysis.seriousness import summarize_missingness, summarize_seriousness
from dsi.analysis.selectors import adverse_event_reports
from dsi.analysis.temporal import compare_periods
from dsi.common import utcnow
from dsi.config import Settings, get_settings
from dsi.domain.evidence import (
    AdverseEventReport,
    EvidenceRecord,
    LabelSection,
    LiteratureReference,
)
from dsi.domain.investigation import Investigation
from dsi.domain.provenance import Provenance, SourceType
from dsi.domain.state import ActionType, AgentState, Budget, InvestigationStatus
from dsi.domain.tools import (
    FaersSearchData,
    FaersSearchRequest,
    LabelFetchData,
    LabelFetchRequest,
    LiteratureSearchData,
    LiteratureSearchRequest,
    ToolResult,
)
from dsi.mcp_server.openfda import fetch_drug_label, search_adverse_events
from dsi.mcp_server.pubmed import search_literature
from dsi.mcp_server.server import ToolClients
from dsi.agent.assemble import build_memo_from_parts
from dsi.memo.validator import scan_text, validate_memo
from dsi.persistence.cache import SnapshotCache
from dsi.persistence.db import Database
from dsi.persistence.depgraph import DependencyGraph, DepGraphRepo, DepNode
from dsi.persistence.repositories import (
    AnalysisRepo,
    EvidenceRepo,
    InvestigationRepo,
    MemoRepo,
    StateRepo,
)
from dsi.hashing import canonical_hash, hash_of_hashes
from dsi.trace.models import Outcome, TraceKind
from dsi.trace.spine import TraceSpine
from pydantic import BaseModel


@dataclass
class RunContext:
    """All dependencies for one investigation run. Injectable for tests."""

    db: Database
    llm: LLMClient
    tool_clients: ToolClients
    settings: Settings = field(default_factory=get_settings)
    investigation: Investigation | None = None
    max_steps: int = 24
    max_tool_retries: int = 2
    top_n_serious: int = 5
    deterministic_framing: bool = False  # skip the LLM framing call (constrained run)

    def __post_init__(self) -> None:
        self.spine = TraceSpine(self.db)
        self.cache = SnapshotCache(self.db)
        self.investigations = InvestigationRepo(self.db)
        self.evidence = EvidenceRepo(self.db)
        self.analyses = AnalysisRepo(self.db)
        self.memos = MemoRepo(self.db)
        self.states = StateRepo(self.db)
        self.depgraphs = DepGraphRepo(self.db)


class GraphState(TypedDict, total=False):
    state: AgentState
    pending_sources: set[str]
    have_evidence: bool
    analyses_done: bool
    sufficiency: dict | None
    sufficient: bool | None
    conflicts_done: bool
    results: dict            # kind -> AnalysisResult (in-memory, for finalize)
    conflict: Any
    memo_id: str | None


class _Framing(BaseModel):
    summary: str = ""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _prov(ctx: RunContext, source_type: SourceType, source: str, query: str) -> Provenance:
    return Provenance(source_type=source_type, source=source, query=query,
                      retrieved_at=utcnow())


def _persist_evidence(ctx: RunContext, payload, provenance: Provenance, state: AgentState) -> None:
    record = EvidenceRecord.create(payload, provenance)
    if ctx.evidence.save(state.investigation_id, record):
        state.evidence_ids.append(record.evidence_id)


def _add_budget(state: AgentState, tokens_in: int, tokens_out: int) -> None:
    state.budget.total_tokens_used += tokens_in + tokens_out


# --------------------------------------------------------------------------- #
# Nodes (closures over ctx)
# --------------------------------------------------------------------------- #
def build_graph(ctx: RunContext):
    inv = ctx.investigation
    assert inv is not None, "RunContext.investigation must be set before build_graph"

    def initialize(gs: GraphState) -> dict:
        ctx.investigations.save(inv)
        state = gs["state"]
        state.status = InvestigationStatus.GATHERING
        ctx.states.save(state)
        return {"pending_sources": {"faers", "label", "literature"},
                "have_evidence": False, "analyses_done": False, "sufficiency": None,
                "sufficient": None, "conflicts_done": False, "results": {}, "conflict": None}

    def normalize_node(gs: GraphState) -> dict:
        state = gs["state"]
        res = normalize(inv.drug, inv.event, inv.investigation_id)
        ctx.analyses.save(inv.investigation_id, state.run_id, res)
        state.normalized_drug_names = res.normalized_drug_names
        state.normalized_event_terms = res.normalized_event_terms
        results = dict(gs.get("results", {}))
        results["normalization"] = res
        ctx.states.save(state)
        return {"state": state, "results": results}

    def decide_node(gs: GraphState) -> dict: #important bit 
        state = gs["state"]
        available = available_actions( # computes the legal actions based on the current state. 
            pending_sources=gs.get("pending_sources", set()),
            have_evidence=gs.get("have_evidence", False),
            analyses_done=gs.get("analyses_done", False),
            sufficiency_checked=gs.get("sufficiency") is not None,
            sufficient=gs.get("sufficient"),
            conflicts_done=gs.get("conflicts_done", False),
        )
        observed = {
            "evidence_count": len(state.evidence_ids),
            "pending_sources": sorted(gs.get("pending_sources", set())),
            "analyses_done": gs.get("analyses_done", False),
            "sufficiency_checked": gs.get("sufficiency") is not None,
            "sufficient": gs.get("sufficient"),
            "conflicts_done": gs.get("conflicts_done", False),
            "step": state.step_index,
        }

        # Deterministic guards: step/budget limits force safe termination.
        over_steps = state.step_index >= ctx.max_steps
        over_budget = state.budget.total_exceeded()
        if over_steps or over_budget:
            forced = ActionType.GENERATE_MEMO if gs.get("analyses_done") else ActionType.STOP
            from dsi.domain.state import Decision
            reason = "step limit reached" if over_steps else "token budget reached"
            decision = Decision(step_index=state.step_index, observed_state=observed,
                                chosen_action=forced, rationale=f"deterministic guard: {reason}",
                                alternatives_considered=available)
            state.record_decision(decision)
            ctx.states.save(state)
            return {"state": state}

        decision, ti, to = decide(
            llm=ctx.llm, spine=ctx.spine, investigation_id=inv.investigation_id,
            run_id=state.run_id, step_index=state.step_index,
            observed_state=observed, available=available)
        _add_budget(state, ti, to)
        state.record_decision(decision)
        ctx.states.save(state)
        return {"state": state}

    # -- retrieval nodes ---------------------------------------------------- #
    def _retrieve(gs: GraphState, source: str, tool_name: str, request: BaseModel,
                  response_type, fetch_fn, source_type: SourceType, source_label: str,
                  extract) -> dict:
        state = gs["state"]
        pending = set(gs.get("pending_sources", set()))
        with ctx.spine.span(TraceKind.TOOL_CALL, tool_name, inv.investigation_id,
                            state.run_id) as rec:
            result, hit = ctx.cache.get_or_fetch(
                tool_name, request, fetch_fn, response_type, cache_if=lambda r: r.ok)
            rec.cache_hit = hit
            rec.retry_count = result.retry_count
            if not result.ok:
                rec.outcome = Outcome.ERROR
                rec.error_type = result.error.code.value
            else:
                n = len(extract(result.data))
                rec.records_read = n
                if n == 0:
                    rec.outcome = Outcome.EMPTY

        if not result.ok:
            # agent-level bounded retry: re-offer the source unless retries exhausted
            key = f"tool:{source}"
            state.retry_counts[key] = state.retry_counts.get(key, 0) + 1
            if result.error.retryable and state.retry_counts[key] <= ctx.max_tool_retries:
                pass  # keep source in `pending` so decide re-offers it -> agent-level retry
            else:
                pending.discard(source)  # retries exhausted / non-retryable -> give up
            ctx.states.save(state)
            return {"state": state, "pending_sources": pending}

        # success (may be empty)
        records = extract(result.data)
        for payload in records:
            _persist_evidence(ctx, payload, _prov(ctx, source_type, source_label, result.query), state)
        pending.discard(source)
        have = gs.get("have_evidence", False) or bool(records)
        ctx.states.save(state)
        return {"state": state, "pending_sources": pending, "have_evidence": have}

    def retrieve_faers(gs: GraphState) -> dict:
        req = FaersSearchRequest(drug=inv.drug, event=inv.event,
                                 date_start=inv.review_period.start, date_end=inv.review_period.end)
        return _retrieve(
            gs, "faers", "faers_search", req, ToolResult[FaersSearchData],
            lambda: search_adverse_events(req, ctx.tool_clients.openfda,
                                          ctx.tool_clients.openfda_api_key),
            SourceType.FAERS, "openFDA/drug/event", lambda data: list(data.reports))

    def retrieve_label(gs: GraphState) -> dict:
        req = LabelFetchRequest(drug=inv.drug)
        return _retrieve(
            gs, "label", "label_fetch", req, ToolResult[LabelFetchData],
            lambda: fetch_drug_label(req, ctx.tool_clients.openfda, ctx.tool_clients.openfda_api_key),
            SourceType.DRUG_LABEL, "openFDA/drug/label", lambda data: list(data.sections))

    def retrieve_literature(gs: GraphState) -> dict:
        query = f"{inv.drug} {inv.event}"
        req = LiteratureSearchRequest(query=query)
        return _retrieve(
            gs, "literature", "literature_search", req, ToolResult[LiteratureSearchData],
            lambda: search_literature(req, ctx.tool_clients.pubmed, ctx.tool_clients.pubmed_api_key),
            SourceType.PUBMED, "PubMed", lambda data: list(data.references))

    # -- deterministic analysis nodes --------------------------------------- #
    def run_analysis(gs: GraphState) -> dict:
        state = gs["state"]
        records = ctx.evidence.list_for(inv.investigation_id)
        collapsed = collapse_to_latest_versions(records)
        results = dict(gs.get("results", {}))
        results["aggregation"] = aggregate_reports(collapsed, inv.investigation_id)
        results["seriousness"] = summarize_seriousness(collapsed, inv.investigation_id)
        results["missingness"] = summarize_missingness(collapsed, inv.investigation_id)
        results["dedup"] = resolve_duplicates(records, inv.investigation_id)  # full set: see chains
        results["temporal"] = compare_periods(collapsed, inv.review_period, inv.investigation_id)
        for res in results.values():
            ctx.analyses.save(inv.investigation_id, state.run_id, res)
            if res.result_id not in state.analysis_result_ids:
                state.analysis_result_ids.append(res.result_id)
        _persist_depgraph(ctx, inv.investigation_id, state.run_id, records, results)
        ctx.states.save(state)
        return {"state": state, "results": results, "analyses_done": True}

    def sufficiency_node(gs: GraphState) -> dict:
        records = ctx.evidence.list_for(inv.investigation_id)
        verdict = sufficiency_mod.check_sufficiency(records)
        return {"sufficiency": {"sufficient": verdict.sufficient, "reasons": verdict.reasons,
                                "case_count": verdict.case_count},
                "sufficient": verdict.sufficient}

    def conflicts_node(gs: GraphState) -> dict:
        state = gs["state"]
        records = ctx.evidence.list_for(inv.investigation_id)
        cf = conflicts_mod.detect_conflicts(records, inv.investigation_id)
        if cf is not None:
            ctx.analyses.save(inv.investigation_id, state.run_id, cf)
        return {"conflict": cf, "conflicts_done": True}

    # -- finalize ----------------------------------------------------------- #
    def finalize(gs: GraphState) -> dict:
        state = gs["state"]
        results = gs.get("results", {})
        records = ctx.evidence.list_for(inv.investigation_id)
        collapsed = collapse_to_latest_versions(records)
        ae_records = [r for r in collapsed if isinstance(r.payload, AdverseEventReport)]
        serious_payloads = select_serious_cases([r.payload for r in ae_records], ctx.top_n_serious)
        serious_ids = {p.report_id for p in serious_payloads}
        serious_records = [r for r in ae_records if r.payload.report_id in serious_ids]
        label_records = [r for r in records if isinstance(r.payload, LabelSection)]
        literature_records = [r for r in records if isinstance(r.payload, LiteratureReference)]

        framing = _generate_framing(ctx, inv, state, serious_records)

        suff = gs.get("sufficiency") or {"reasons": []}
        analyses = dict(results)
        analyses.setdefault("normalization", normalize(inv.drug, inv.event, inv.investigation_id))

        def _assemble(framing_text: str):
            return build_memo_from_parts(
                investigation=inv, run_id=state.run_id, model_tag=ctx.settings.model_tag,
                analyses=analyses, records=records, conflict=gs.get("conflict"),
                framing=framing_text, sufficiency_reasons=suff.get("reasons", []),
                top_n_serious=ctx.top_n_serious)

        memo = _assemble(framing)
        report = validate_memo(memo)
        if not report.ok:
            # Framing is the only LLM prose; replace it with a safe deterministic line
            # and rebuild. All other claims are deterministic and safe by construction.
            memo = _assemble(_deterministic_framing(gs))
            report = validate_memo(memo)
        from dsi.domain.memo import MemoValidationStatus
        memo.validation_status = MemoValidationStatus.PASSED if report.ok else MemoValidationStatus.FAILED
        ctx.memos.save(memo)
        _persist_memo_depnodes(ctx, inv.investigation_id, state.run_id, memo, records)

        sufficient = gs.get("sufficient")
        state.status = (InvestigationStatus.COMPLETED if sufficient
                        else InvestigationStatus.HALTED_INSUFFICIENT_EVIDENCE)
        ctx.states.save(state)
        return {"state": state, "memo_id": memo.memo_id}

    # -- routing ------------------------------------------------------------ #
    def route_after_decide(gs: GraphState) -> str:
        action = gs["state"].next_action
        return {
            ActionType.RETRIEVE_FAERS: "retrieve_faers",
            ActionType.RETRIEVE_LABEL: "retrieve_label",
            ActionType.RETRIEVE_LITERATURE: "retrieve_literature",
            ActionType.RUN_ANALYSIS: "run_analysis",
            ActionType.CHECK_SUFFICIENCY: "sufficiency",
            ActionType.DETECT_CONFLICTS: "conflicts",
            ActionType.GENERATE_MEMO: "finalize",
            ActionType.STOP: "finalize",
        }[action]

    g = StateGraph(GraphState)
    g.add_node("initialize", initialize)
    g.add_node("normalize", normalize_node)
    g.add_node("decide", decide_node)
    g.add_node("retrieve_faers", retrieve_faers)
    g.add_node("retrieve_label", retrieve_label)
    g.add_node("retrieve_literature", retrieve_literature)
    g.add_node("run_analysis", run_analysis)
    g.add_node("sufficiency", sufficiency_node)
    g.add_node("conflicts", conflicts_node)
    g.add_node("finalize", finalize)

    g.add_edge(START, "initialize")
    g.add_edge("initialize", "normalize")
    g.add_edge("normalize", "decide")
    g.add_conditional_edges("decide", route_after_decide, {
        "retrieve_faers": "retrieve_faers", "retrieve_label": "retrieve_label",
        "retrieve_literature": "retrieve_literature", "run_analysis": "run_analysis",
        "sufficiency": "sufficiency", "conflicts": "conflicts", "finalize": "finalize"})
    for node in ("retrieve_faers", "retrieve_label", "retrieve_literature",
                 "run_analysis", "sufficiency", "conflicts"):
        g.add_edge(node, "decide")
    g.add_edge("finalize", END)
    return g.compile()


# --------------------------------------------------------------------------- #
# Framing (the only LLM prose in the memo) + dependency graph persistence
# --------------------------------------------------------------------------- #
def _deterministic_framing(gs: GraphState) -> str:
    return ("This advisory memo organizes public evidence for human review. It does not "
            "establish causation or rates and is not a treatment recommendation.")


def _generate_framing(ctx: RunContext, inv: Investigation, state: AgentState,
                      serious_records: list[EvidenceRecord]) -> str:
    """Ask the model for a short NON-factual framing sentence. Retrieved case text
    enters ONLY inside a delimited DATA block. Output is scanned; anything unsafe or
    empty falls back to a fixed deterministic line."""
    if ctx.deterministic_framing:  # constrained run: skip the LLM framing call entirely
        return _deterministic_framing({})
    digest = "\n".join(case_line(r.payload) for r in serious_records[:ctx.top_n_serious]) or "none"
    instruction = (
        "Write ONE neutral sentence framing this drug-safety memo for a human reviewer. "
        "Do NOT state causation, rates, or recommendations. "
        'Reply with ONLY JSON: {"summary": "<one sentence>"}.')
    prompt = render_prompt(instruction, [("serious_cases", digest)])
    result = generate_structured(
        ctx.llm, ctx.spine, model_cls=_Framing, prompt=prompt,
        fallback=lambda: _Framing(summary=""),
        name="generate_framing", investigation_id=inv.investigation_id, run_id=state.run_id,
        context_size_tokens=len(prompt) // 4)
    _add_budget(state, result.tokens_in, result.tokens_out)
    text = result.value.summary.strip()
    if not text or scan_text(text):        # empty or unsafe -> deterministic fallback
        return ("This advisory memo organizes public evidence for human review. It does not "
                "establish causation or rates and is not a treatment recommendation.")
    return text


def _persist_depgraph(ctx: RunContext, investigation_id: str, run_id: str,
                      records: list[EvidenceRecord], results: dict) -> None:
    """Persist a basic evidence->analysis dependency graph for this run (memo-section
    nodes are added in later phases). Evidence 'slot' nodes are grouped by source."""
    graph = DependencyGraph()
    groups: dict[str, list[str]] = {"faers": [], "label": [], "literature": []}
    for r in records:
        if isinstance(r.payload, AdverseEventReport):
            groups["faers"].append(r.content_hash)
        elif isinstance(r.payload, LabelSection):
            groups["label"].append(r.content_hash)
        elif isinstance(r.payload, LiteratureReference):
            groups["literature"].append(r.content_hash)
    for slot, hashes in groups.items():
        graph.add_node(DepNode(node_id=f"evidence:{slot}", node_type="evidence",
                               content_hash=hash_of_hashes(hashes) if hashes else "empty"))
    consumes = {
        "aggregation": ["faers"], "seriousness": ["faers"], "missingness": ["faers"],
        "dedup": ["faers"], "temporal": ["faers"],
    }
    for kind, res in results.items():
        if kind == "normalization":
            continue
        graph.add_node(DepNode(node_id=f"analysis:{kind}", node_type="analysis",
                               output_hash=res.output_hash))
        for slot in consumes.get(kind, []):
            graph.add_edge(f"evidence:{slot}", f"analysis:{kind}")
    graph.initialize_input_hashes()
    ctx.depgraphs.save_graph(investigation_id, run_id, graph)


def _persist_memo_depnodes(ctx: RunContext, investigation_id: str, run_id: str,
                           memo, records: list[EvidenceRecord]) -> None:
    """Extend the run's dependency graph with a node per memo section, linked to the
    analysis nodes (by matching output hash) and evidence slots it consumed. This
    completes evidence -> analysis -> memo_section so a later evidence change marks
    exactly the affected sections stale (Scenario A)."""
    graph = ctx.depgraphs.load_graph(run_id)
    # analysis output_hash -> node_id, for matching a section's consumed hashes
    analysis_by_output = {n.output_hash: n.node_id for n in graph.nodes.values()
                          if n.node_type == "analysis" and n.output_hash}
    # evidence_id -> slot, so a section citing a record links to its source slot
    slot_of: dict[str, str] = {}
    for r in records:
        if isinstance(r.payload, AdverseEventReport):
            slot_of[r.evidence_id] = "evidence:faers"
        elif isinstance(r.payload, LabelSection):
            slot_of[r.evidence_id] = "evidence:label"
        elif isinstance(r.payload, LiteratureReference):
            slot_of[r.evidence_id] = "evidence:literature"

    for section in memo.sections:
        node_id = f"memo:{section.kind.value}"
        output_hash = canonical_hash([c.text for c in section.claims])
        graph.add_node(DepNode(node_id=node_id, node_type="memo_section", output_hash=output_hash))
        upstreams: set[str] = set()
        for h in section.consumed_output_hashes:
            if h in analysis_by_output:
                upstreams.add(analysis_by_output[h])
        for claim in section.claims:
            for cit in claim.citations:
                if cit.ref_id in slot_of and slot_of[cit.ref_id] in graph.nodes:
                    upstreams.add(slot_of[cit.ref_id])
        for up in upstreams:
            graph.add_edge(up, node_id)

    graph.initialize_input_hashes()
    ctx.depgraphs.save_graph(investigation_id, run_id, graph)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
@dataclass
class RunResult:
    state: AgentState
    memo_id: str | None


def run_investigation(ctx: RunContext, investigation: Investigation,
                      budget: Budget | None = None) -> RunResult:
    """Run one investigation to completion and return the final state + memo id."""
    ctx.investigation = investigation
    app = build_graph(ctx)
    state = AgentState(
        investigation_id=investigation.investigation_id, drug=investigation.drug,
        event=investigation.event, review_period=investigation.review_period,
        budget=budget or Budget())
    initial: GraphState = {"state": state}
    final = app.invoke(initial, config={"recursion_limit": ctx.max_steps * 3 + 20})
    return RunResult(state=final["state"], memo_id=final.get("memo_id"))