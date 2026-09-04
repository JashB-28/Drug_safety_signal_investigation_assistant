"""Scenario C --- constrained second run.

Rerun the same investigation under a tighter model-token budget (target: >=40%
lower) and confirm a pre-declared quality floor still holds. The optimizations that
buy the reduction, all explicit:
  * framing moved into deterministic logic (no LLM framing call),
  * smaller context (fewer serious cases carried into any prompt: top_n 5 -> 2),
  * a hard token budget whose guard curtails late agentic decisions (they fall back
    to the deterministic policy instead of a model call).

Quality floor (declared BEFORE the run):
  1. every memo claim still cited (0 uncited material claims),
  2. seriousness & missingness counts identical to baseline (exact),
  3. all safety gates still pass (validator ok),
  4. the top-N most serious individual cases are still inspected.

Reported: baseline vs constrained model tokens, % reduction, whether the floor
held, and the failure mode that appears first as the budget tightens further.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from dsi.agent.graph import RunContext, run_investigation
from dsi.domain.investigation import Investigation
from dsi.domain.memo import MemoSectionKind, MemoValidationStatus
from dsi.domain.state import Budget
from dsi.scenarios._common import load_run_analyses, model_tokens_for_run

# The single documented answer to "which limit fails first as the budget tightens".
FIRST_FAILURE_MODE = (
    "Agentic decision autonomy degrades first: late decisions fall back to the "
    "deterministic policy. Evidence gathering and the deterministic analyses are "
    "preserved longest; only if the budget is cut so far that analysis cannot run "
    "would the exact seriousness/missingness counts (the quality floor) break."
)


@dataclass
class ScenarioCResult:
    baseline_tokens: int
    constrained_tokens: int
    reduction_pct: float
    floor_ok: bool
    floor_details: dict = field(default_factory=dict)
    first_failure_mode: str = FIRST_FAILURE_MODE


def run_scenario_c(make_ctx: Callable[[bool, Budget | None], RunContext],
                   investigation: Investigation, reduction_target: float = 0.4,
                   constrained_top_n: int = 2) -> ScenarioCResult:
    """`make_ctx(constrained, budget)` returns a fresh RunContext (fresh tool clients,
    shared DB). Baseline runs unconstrained; the constrained run applies the budget +
    deterministic framing + smaller context."""
    # --- baseline ---
    base_ctx = make_ctx(False, None)
    base = run_investigation(base_ctx, investigation)
    t_base = model_tokens_for_run(base_ctx, investigation, base.state.run_id)
    base_analyses = load_run_analyses(base_ctx, investigation, base.state.run_id)

    # --- constrained ---
    budget = Budget(max_total_tokens=int(t_base * (1.0 - reduction_target)))
    con_ctx = make_ctx(True, budget)
    con_ctx.top_n_serious = constrained_top_n
    con = run_investigation(con_ctx, investigation, budget=budget)
    t_con = model_tokens_for_run(con_ctx, investigation, con.state.run_id)
    con_analyses = load_run_analyses(con_ctx, investigation, con.state.run_id)
    con_memo = con_ctx.memos.get_for_run(investigation.investigation_id, con.state.run_id)

    reduction = (t_base - t_con) / t_base if t_base else 0.0

    # --- quality floor ---
    floor = _check_floor(base_analyses, con_analyses, con_memo, constrained_top_n)
    return ScenarioCResult(
        baseline_tokens=t_base, constrained_tokens=t_con,
        reduction_pct=round(reduction * 100, 1),
        floor_ok=all(floor.values()), floor_details=floor)


def _pair(analyses: dict, kind: str, *fields: str):
    obj = analyses.get(kind)
    return tuple(getattr(obj, f) for f in fields) if obj else None


def _check_floor(base: dict, con: dict, memo, top_n: int) -> dict:
    from dsi.memo.validator import validate_memo
    # 1. citation completeness
    cited = memo.uncited_material_claims() == []
    # 2. seriousness & missingness identical to baseline
    ser_exact = _pair(base, "seriousness", "total_reports", "serious", "non_serious",
                      "seriousness_unknown") == _pair(con, "seriousness", "total_reports",
                      "serious", "non_serious", "seriousness_unknown")
    miss_base = base.get("missingness"); miss_con = con.get("missingness")
    miss_exact = bool(miss_base and miss_con and
                      miss_base.missing_counts == miss_con.missing_counts)
    # 3. safety gates pass
    safety = validate_memo(memo).ok and memo.validation_status is MemoValidationStatus.PASSED
    # 4. top-N most serious cases still inspected
    ae = next(s for s in memo.sections if s.kind is MemoSectionKind.ADVERSE_EVENT_EVIDENCE)
    serious_case_claims = sum(1 for c in ae.claims if c.text.startswith("Serious case "))
    ser = con.get("seriousness")
    expected = min(top_n, ser.serious if ser else 0)
    top_n_ok = serious_case_claims >= expected
    return {"claims_cited": cited, "seriousness_exact": ser_exact,
            "missingness_exact": miss_exact, "safety_gates_pass": safety,
            "top_n_inspected": top_n_ok}
