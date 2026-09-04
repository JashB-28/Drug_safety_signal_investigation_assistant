"""Scenario B --- evidence conflicts.

Run an investigation where the FAERS report pattern, the label, and an external
PubMed source do NOT point in the same direction (a spontaneous-report signal +
case-series vs. an observational study reporting no increased risk). Confirm the
system preserves the disagreement --- each source's position with its date and
limitations --- and does not force a single confident answer or drop evidence.

Uses the normal agent run; the conflict is produced by the deterministic
`detect_conflicts` step, so this scenario just runs the agent and inspects the
preserved `ConflictFinding` and the memo's conflicting-evidence section.
"""

from __future__ import annotations

from dataclasses import dataclass

from dsi.agent.graph import RunContext, run_investigation
from dsi.domain.analysis import ConflictFinding
from dsi.domain.investigation import Investigation
from dsi.domain.memo import Memo, MemoSectionKind


@dataclass
class ScenarioBResult:
    run_id: str
    conflict: ConflictFinding | None
    unresolved: bool
    positions: list[str]
    memo: Memo
    conflict_section_claim_count: int


def run_scenario_b(ctx: RunContext, investigation: Investigation) -> ScenarioBResult:
    result = run_investigation(ctx, investigation)
    run_id = result.state.run_id
    memo = ctx.memos.get_for_run(investigation.investigation_id, run_id)

    # rehydrate the conflict finding persisted during the run
    conflict = None
    for row in ctx.analyses.get_raw_for_run(investigation.investigation_id, run_id):
        if row["kind"] == "conflict":
            conflict = ConflictFinding.model_validate_json(row["result_json"])
            break

    section = next(s for s in memo.sections if s.kind is MemoSectionKind.CONFLICTING_EVIDENCE)
    return ScenarioBResult(
        run_id=run_id, conflict=conflict,
        unresolved=bool(conflict and conflict.unresolved),
        positions=list(conflict.positions) if conflict else [],
        memo=memo, conflict_section_claim_count=len(section.claims))
