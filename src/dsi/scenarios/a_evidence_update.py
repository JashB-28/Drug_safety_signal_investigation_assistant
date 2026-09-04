"""Scenario A --- evidence changes after the first run.

Run an investigation, then introduce ONE corrected/added evidence item (here: a
later case version that flips a report to serious). Detect what became stale via
the dependency graph, recompute ONLY the affected work, preserve the prior run, and
report the reused-vs-recomputed breakdown plus the before/after memo.

The selective recompute uses the Phase-3 dependency engine directly:
  * evidence slot hashes are updated to reflect the new evidence,
  * `graph.recompute(fn)` recomputes only nodes whose inputs changed, and
    short-circuits when a recomputed analysis produces an unchanged output (so its
    downstream memo section is reused, not regenerated),
  * memo sections are rebuilt only when their node was actually recomputed; reused
    sections keep the prior run's prose verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dsi.agent.assemble import build_memo_from_parts
from dsi.agent.graph import RunContext, run_investigation
from dsi.analysis.aggregate import aggregate_reports
from dsi.analysis.dedup import collapse_to_latest_versions, resolve_duplicates
from dsi.analysis.normalize import normalize
from dsi.analysis.seriousness import summarize_missingness, summarize_seriousness
from dsi.analysis.temporal import compare_periods
from dsi.common import new_id
from dsi.domain.evidence import (
    AdverseEventReport,
    EvidenceRecord,
    LabelSection,
    LiteratureReference,
)
from dsi.domain.investigation import Investigation
from dsi.domain.memo import Memo, MemoValidationStatus
from dsi.domain.provenance import Provenance, SourceType
from dsi.hashing import canonical_hash, hash_of_hashes
from dsi.memo.validator import validate_memo
from dsi.scenarios._common import load_run_analyses


@dataclass
class ScenarioAResult:
    run1_id: str
    run2_id: str
    memo_before: Memo
    memo_after: Memo
    recomputed_nodes: list[str]
    reused_nodes: list[str]
    short_circuited_nodes: list[str]
    seriousness_before: tuple[int, int]   # (total, serious)
    seriousness_after: tuple[int, int]
    run1_preserved: bool
    changed_evidence_id: str


def _analysis_recompute(kind: str, records: list[EvidenceRecord], inv: Investigation):
    collapsed = collapse_to_latest_versions(records)
    return {
        "aggregation": lambda: aggregate_reports(collapsed, inv.investigation_id),
        "seriousness": lambda: summarize_seriousness(collapsed, inv.investigation_id),
        "missingness": lambda: summarize_missingness(collapsed, inv.investigation_id),
        "dedup": lambda: resolve_duplicates(records, inv.investigation_id),
        "temporal": lambda: compare_periods(collapsed, inv.review_period, inv.investigation_id),
    }[kind]()


def _slot_hashes(records: list[EvidenceRecord]) -> dict[str, str]:
    groups: dict[str, list[str]] = {"faers": [], "label": [], "literature": []}
    for r in records:
        if isinstance(r.payload, AdverseEventReport):
            groups["faers"].append(r.content_hash)
        elif isinstance(r.payload, LabelSection):
            groups["label"].append(r.content_hash)
        elif isinstance(r.payload, LiteratureReference):
            groups["literature"].append(r.content_hash)
    return {slot: (hash_of_hashes(h) if h else "empty") for slot, h in groups.items()}


def _seriousness_pair(analyses: dict) -> tuple[int, int]:
    s = analyses.get("seriousness")
    return (s.total_reports, s.serious) if s else (0, 0)


def run_scenario_a(ctx: RunContext, investigation: Investigation,
                   new_evidence: EvidenceRecord) -> ScenarioAResult:
    # --- run 1 ---
    r1 = run_investigation(ctx, investigation)
    run1 = r1.state.run_id
    memo1 = ctx.memos.get_for_run(investigation.investigation_id, run1)
    graph = ctx.depgraphs.load_graph(run1)

    # capture run-1 analyses (for reused sections + the before/after numbers)
    analyses1 = load_run_analyses(ctx, investigation, run1)
    ser_before = _seriousness_pair(analyses1)

    # --- introduce ONE new/corrected evidence item ---
    ctx.evidence.save(investigation.investigation_id, new_evidence)
    records = ctx.evidence.list_for(investigation.investigation_id)

    # --- update evidence slot hashes; recompute selectively ---
    for slot, h in _slot_hashes(records).items():
        node_id = f"evidence:{slot}"
        if node_id in graph.nodes:
            graph.update_evidence_hash(node_id, h)

    run2 = new_id("run")
    analyses2: dict = dict(analyses1)  # start from run-1 results; overwrite recomputed ones
    rebuilt = {"memo": None}
    recomputed_memo_kinds: set[str] = set()

    def recompute_fn(node) -> str:
        if node.node_type == "analysis":
            kind = node.node_id.split(":", 1)[1]
            res = _analysis_recompute(kind, records, investigation)
            ctx.analyses.save(investigation.investigation_id, run2, res)
            analyses2[kind] = res
            return res.output_hash
        # memo_section: rebuild the whole memo once (with run-2 analyses), memoized
        if rebuilt["memo"] is None:
            rebuilt["memo"] = _rebuild_memo(ctx, investigation, run2, records, analyses2)
        kind = node.node_id.split(":", 1)[1]
        recomputed_memo_kinds.add(kind)
        section = next(s for s in rebuilt["memo"].sections if s.kind.value == kind)
        return canonical_hash([c.text for c in section.claims])

    report = graph.recompute(recompute_fn)

    # --- assemble run-2 memo: reuse run-1 sections except the recomputed ones ---
    memo2 = _stitch_memo(memo1, rebuilt["memo"], recomputed_memo_kinds, run2)
    memo2.validation_status = (MemoValidationStatus.PASSED
                               if validate_memo(memo2).ok else MemoValidationStatus.FAILED)
    ctx.memos.save(memo2)
    ctx.depgraphs.save_graph(investigation.investigation_id, run2, graph)

    run1_preserved = ctx.memos.get_for_run(investigation.investigation_id, run1) is not None
    return ScenarioAResult(
        run1_id=run1, run2_id=run2, memo_before=memo1, memo_after=memo2,
        recomputed_nodes=sorted(report.recomputed), reused_nodes=sorted(report.reused),
        short_circuited_nodes=sorted(report.short_circuited),
        seriousness_before=ser_before, seriousness_after=_seriousness_pair(analyses2),
        run1_preserved=run1_preserved, changed_evidence_id=new_evidence.evidence_id)


# --------------------------------------------------------------------------- #
def _rebuild_memo(ctx: RunContext, inv: Investigation, run2: str,
                  records: list[EvidenceRecord], analyses: dict) -> Memo:
    return build_memo_from_parts(
        investigation=inv, run_id=run2, model_tag=ctx.settings.model_tag,
        analyses=analyses, records=records, conflict=None,
        framing=("This advisory memo organizes public evidence for human review. It does not "
                 "establish causation or rates and is not a treatment recommendation."),
        sufficiency_reasons=[], top_n_serious=ctx.top_n_serious)


def _stitch_memo(memo1: Memo, rebuilt: Memo | None, recomputed_kinds: set[str], run2: str) -> Memo:
    """Run-2 memo = run-1 sections, with only the recomputed sections replaced."""
    sections = []
    rebuilt_by_kind = {s.kind.value: s for s in (rebuilt.sections if rebuilt else [])}
    for sec in memo1.sections:
        if sec.kind.value in recomputed_kinds and sec.kind.value in rebuilt_by_kind:
            sections.append(rebuilt_by_kind[sec.kind.value])
        else:
            sections.append(sec)  # reused verbatim from run 1
    return Memo(investigation_id=memo1.investigation_id, run_id=run2,
                model_tag=memo1.model_tag, sections=sections)


def corrected_version_record(report_id: str, version: int, *, serious: bool,
                             reactions: list[str], receive_date=None) -> EvidenceRecord:
    """Helper: build a later case version of an existing report (Scenario A input).
    Keep `receive_date` equal to the prior version's so the temporal analysis stays
    unchanged --- which lets its output-hash short-circuit be observed."""
    from dsi.domain.evidence import ReactionEntry
    from dsi.common import utcnow
    payload = AdverseEventReport(
        report_id=report_id, report_version=version, serious=serious,
        serious_death=serious or None, receive_date=receive_date,
        reactions=[ReactionEntry(term=t) for t in reactions])
    prov = Provenance(source_type=SourceType.FAERS, source="openFDA/drug/event (follow-up)",
                      query="corrected case version", retrieved_at=utcnow())
    return EvidenceRecord.create(payload, prov)
