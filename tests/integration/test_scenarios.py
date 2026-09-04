"""The three mandatory challenge scenarios, automated and offline."""

from __future__ import annotations

from datetime import date

from dsi.agent.graph import RunContext
from dsi.agent.llm import ScriptedLLM
from dsi.domain.state import Budget
from dsi.mcp_server.server import ToolClients
from dsi.scenarios import (
    corrected_version_record,
    run_scenario_a,
    run_scenario_b,
    run_scenario_c,
)


def _clients(http):
    return ToolClients(
        openfda=http.Routed({"/drug/event": [http.ok(http.faers())],
                             "/drug/label": [http.ok(http.label())]}),
        pubmed=http.Routed({"/esearch": [http.ok(http.esearch())],
                            "/esummary": [http.ok(http.esummary())]}),
    )


# --- Scenario A: evidence update / selective recompute --------------------- #
def test_scenario_a_selective_recompute_and_preservation(db, investigation, http):
    ctx = RunContext(db=db, llm=ScriptedLLM(), tool_clients=_clients(http))
    # a corrected later version of US-002 that flips it to serious (date kept stable)
    correction = corrected_version_record("US-002", version=2, serious=True,
                                          reactions=["Suicidal ideation"],
                                          receive_date=date(2020, 8, 20))
    res = run_scenario_a(ctx, investigation, correction)

    assert res.run1_preserved is True and res.run2_id != res.run1_id
    # before: 1 serious (US-001); after: 2 serious (US-002 now serious)
    assert res.seriousness_before[1] == 1
    assert res.seriousness_after[1] == 2

    # affected analyses recomputed; an unaffected one short-circuits (unchanged output)
    assert "analysis:seriousness" in res.recomputed_nodes
    assert "analysis:dedup" in res.recomputed_nodes
    assert "analysis:temporal" in res.short_circuited_nodes      # dates/counts unchanged

    # affected memo sections recomputed; unrelated ones reused verbatim
    assert "memo:seriousness_missingness" in res.recomputed_nodes
    assert "memo:label_evidence" in res.reused_nodes
    assert "memo:external_evidence" in res.reused_nodes
    assert "memo:temporal_pattern" in res.reused_nodes           # downstream of short-circuit

    # the before/after memo actually differs in the seriousness section
    def _serious_text(memo):
        sec = next(s for s in memo.sections if s.kind.value == "seriousness_missingness")
        return " ".join(c.text for c in sec.claims)
    assert _serious_text(res.memo_before) != _serious_text(res.memo_after)


# --- Scenario B: conflicting evidence -------------------------------------- #
def test_scenario_b_preserves_disagreement(db, investigation, http):
    ctx = RunContext(db=db, llm=ScriptedLLM(), tool_clients=_clients(http))
    res = run_scenario_b(ctx, investigation)

    assert res.conflict is not None
    assert res.unresolved is True                     # not forced into consensus
    joined = " ".join(res.positions).lower()
    assert "faers" in joined                          # FAERS position preserved
    assert "no increased risk" in joined              # the discordant study preserved
    assert "suicidality" in joined or "case series" in joined  # the signal side too
    assert any("label" in p.lower() for p in res.positions)    # label position present
    # dates preserved on at least one literature position
    assert any("2019" in p or "2021" in p for p in res.positions)
    assert res.conflict_section_claim_count >= 3      # all positions carried into the memo


# --- Scenario C: constrained run ------------------------------------------- #
def test_scenario_c_cheaper_run_holds_quality_floor(db, investigation, http):
    def make_ctx(constrained: bool, budget: Budget | None) -> RunContext:
        ctx = RunContext(db=db, llm=ScriptedLLM(), tool_clients=_clients(http),
                         deterministic_framing=constrained)
        return ctx

    res = run_scenario_c(make_ctx, investigation, reduction_target=0.5, constrained_top_n=2)

    assert res.baseline_tokens > 0
    assert res.constrained_tokens < res.baseline_tokens
    assert res.reduction_pct >= 40.0                  # >=40% fewer model tokens
    assert res.floor_ok is True, res.floor_details    # quality floor held
    assert res.floor_details["seriousness_exact"] is True
    assert res.floor_details["safety_gates_pass"] is True
    assert res.first_failure_mode                     # documented
