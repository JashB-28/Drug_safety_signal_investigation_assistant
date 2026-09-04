"""Generate the before/after evidence-update trace artifact (assessment Scenario A / §11).

Runs one investigation on the pinned offline snapshot, introduces ONE corrected
report version, recomputes selectively, and writes a human-readable Markdown trace
showing: the change, what was reused vs. recomputed (and short-circuited), the
before/after memo difference, and proof the prior run is preserved.

Fully offline and deterministic (scripted model + network guard), so it regenerates
the same way every time.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from dsi.agent.graph import RunContext
from dsi.agent.llm import ScriptedLLM
from dsi.domain.memo import Memo, MemoSectionKind
from dsi.eval.fixtures import EVAL_INVESTIGATION
from dsi.eval.seed import OfflineGuardClient, seed_cache
from dsi.mcp_server.server import ToolClients
from dsi.memo.render import render_memo
from dsi.persistence.db import Database
from dsi.scenarios.a_evidence_update import ScenarioAResult, corrected_version_record, run_scenario_a


def generate_trace(out_dir: str | Path = "data/outputs") -> Path:
    db = Database.create(":memory:")
    seed_cache(db, EVAL_INVESTIGATION)
    ctx = RunContext(db=db, llm=ScriptedLLM(),
                     tool_clients=ToolClients(OfflineGuardClient(), OfflineGuardClient()))
    # The change: a corrected follow-up version of case EV-002 that flips it to serious.
    correction = corrected_version_record("EV-002", version=2, serious=True,
                                          reactions=["Insomnia", "Depression"],
                                          receive_date=date(2019, 7, 15))
    result = run_scenario_a(ctx, EVAL_INVESTIGATION, correction)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "evidence_update_trace.md"
    path.write_text(_render(result), encoding="utf-8")
    return path


def _section_text(memo: Memo, kind: MemoSectionKind) -> str:
    for s in memo.sections:
        if s.kind is kind:
            return "\n".join(f"  - {c.text}" for c in s.claims)
    return "  (section not present)"


def _status_of(kind: MemoSectionKind, res: ScenarioAResult) -> str:
    node = f"memo:{kind.value}"
    if node in res.recomputed_nodes:
        return "RECOMPUTED"
    if node in res.reused_nodes:
        return "reused"
    return "-"


def _render(res: ScenarioAResult) -> str:
    L: list[str] = []
    L.append("# Before / After — Evidence-Update Trace")
    L.append("")
    L.append("_Scenario A: evidence changes after the first run. The system detects what became "
             "stale, recomputes ONLY the affected work, and preserves the prior run. Generated "
             "offline from the pinned snapshot; deterministic._")
    L.append("")

    # 1. the change
    L.append("## 1. The change introduced")
    L.append(f"- Investigation: **{EVAL_INVESTIGATION.drug} / {EVAL_INVESTIGATION.event}** "
             f"({EVAL_INVESTIGATION.review_period.start} to {EVAL_INVESTIGATION.review_period.end})")
    L.append("- One corrected follow-up version of case **EV-002** arrived and flips it to **serious**.")
    L.append("- This is a *new row* (a later version), not an edit — original evidence is immutable.")
    L.append(f"- New evidence id: `{res.changed_evidence_id}`")
    L.append("")

    # 2. headline effect
    L.append("## 2. Effect on the numbers")
    tb, sb = res.seriousness_before
    ta, sa = res.seriousness_after
    L.append(f"- Serious cases: **{sb} → {sa}**  (out of {tb} → {ta} distinct cases)")
    L.append("")

    # 3. reused vs recomputed
    L.append("## 3. Work reused vs. recomputed (from the dependency graph)")
    L.append(f"- **Recomputed ({len(res.recomputed_nodes)})**: {', '.join(res.recomputed_nodes)}")
    L.append(f"- **Reused, untouched ({len(res.reused_nodes)})**: {', '.join(res.reused_nodes)}")
    L.append(f"- **Short-circuited** (recomputed but output unchanged → downstream reused): "
             f"{', '.join(res.short_circuited_nodes) or 'none'}")
    L.append("")
    L.append("> Only the parts that actually depend on the changed case were redone. An analysis "
             "whose output did not change stops the cascade, so its memo section is reused verbatim.")
    L.append("")

    # 4. per-section status
    L.append("## 4. Memo sections — changed vs. reused")
    L.append("")
    L.append("| Section | Status |")
    L.append("|---|---|")
    for kind in MemoSectionKind:
        L.append(f"| {kind.value} | {_status_of(kind, res)} |")
    L.append("")

    # 5. the section that changed, before vs after
    L.append("## 5. What actually changed in the memo")
    changed_kinds = [k for k in MemoSectionKind if f"memo:{k.value}" in res.recomputed_nodes]
    for kind in changed_kinds:
        L.append(f"### {kind.value}")
        L.append("**Before:**")
        L.append("```")
        L.append(_section_text(res.memo_before, kind))
        L.append("```")
        L.append("**After:**")
        L.append("```")
        L.append(_section_text(res.memo_after, kind))
        L.append("```")
        L.append("")

    # 6. preservation
    L.append("## 6. Prior run preserved (audit trail)")
    L.append(f"- Run 1 id: `{res.run1_id}`  (still in the database: **{res.run1_preserved}**)")
    L.append(f"- Run 2 id: `{res.run2_id}`  (the recomputed run)")
    L.append("- Both runs' memos, analyses, and dependency graphs are kept — nothing overwritten.")
    L.append("")

    # 7. full memos
    L.append("---")
    L.append("## Appendix A — Full memo BEFORE the change (run 1)")
    L.append("")
    L.append(render_memo(res.memo_before))
    L.append("")
    L.append("---")
    L.append("## Appendix B — Full memo AFTER the change (run 2)")
    L.append("")
    L.append(render_memo(res.memo_after))
    return "\n".join(L) + "\n"
