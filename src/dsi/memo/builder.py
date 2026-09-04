"""Deterministic memo assembly.

The memo is built from evidence (a) + analysis (b); the LLM contributes only a
short non-factual framing line. Every FACTUAL claim is generated deterministically
and cited to an analysis result or an evidence record. Raw retrieved text (e.g. a
label body, which may itself contain words like 'incidence') is NOT quoted into
claims; sections are described neutrally and cited by id. This keeps the memo both
citation-complete and safe by construction; the validator (validator.py) is the
independent check.

Phase 6 produces a complete, cited, safe memo. Phase 7 refines wording/templates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dsi.domain.analysis import (
    AggregationResult,
    ConflictFinding,
    DedupResult,
    MissingnessSummary,
    NormalizationResult,
    SeriousnessSummary,
    TemporalComparison,
)
from dsi.domain.evidence import (
    AdverseEventReport,
    EvidenceRecord,
    LabelSection,
    LiteratureReference,
)
from dsi.domain.investigation import Investigation
from dsi.domain.memo import (
    Citation,
    CitationKind,
    Claim,
    Memo,
    MemoSection,
    MemoSectionKind,
)


@dataclass
class MemoInputs:
    investigation: Investigation
    run_id: str
    model_tag: str
    normalization: NormalizationResult
    sufficiency_reasons: list[str]
    framing_text: str  # LLM (validated) or deterministic; NON-factual
    aggregation: AggregationResult | None = None
    seriousness: SeriousnessSummary | None = None
    missingness: MissingnessSummary | None = None
    dedup: DedupResult | None = None
    temporal: TemporalComparison | None = None
    label_records: list[EvidenceRecord] = field(default_factory=list)
    literature_records: list[EvidenceRecord] = field(default_factory=list)
    serious_case_records: list[EvidenceRecord] = field(default_factory=list)
    conflict: ConflictFinding | None = None


def _cite_analysis(result) -> Citation:
    return Citation(kind=CitationKind.ANALYSIS, ref_id=result.result_id)


def _fact(text: str, *citations: Citation) -> Claim:
    return Claim(text=text, material=True, citations=list(citations))


def _quote(text: str, *citations: Citation) -> Claim:
    """A claim that carries verbatim source text (paper title, reaction term). Cited,
    but exempt from the prohibited-CLAIM scan --- it is attributed data, not a system
    assertion. See Claim.quoted."""
    return Claim(text=text, material=True, quoted=True, citations=list(citations))


def _note(text: str) -> Claim:
    return Claim(text=text, material=False)


def build_memo(inp: MemoInputs) -> Memo:
    inv = inp.investigation
    sections: list[MemoSection] = []

    # 1. Investigation question
    sections.append(MemoSection(
        kind=MemoSectionKind.INVESTIGATION_QUESTION, title="Investigation question",
        claims=[_note(inv.question or inv.default_question())]))

    # 2. Drug and event (normalized)
    sections.append(MemoSection(
        kind=MemoSectionKind.DRUG_AND_EVENT, title="Drug and event",
        claims=[_fact(
            f"Drug '{inv.drug}' normalized to {inp.normalization.normalized_drug_names}; "
            f"event '{inv.event}' expanded to {inp.normalization.normalized_event_terms}.",
            _cite_analysis(inp.normalization))]))

    # 3. Review period
    sections.append(MemoSection(
        kind=MemoSectionKind.REVIEW_PERIOD, title="Review period",
        claims=[_note(f"Reports reviewed from {inv.review_period.start} to {inv.review_period.end}.")]))

    # 4. Executive summary --- one non-factual framing line + cited headline numbers
    exec_claims: list[Claim] = [_note(inp.framing_text)]
    if inp.seriousness:
        exec_claims.append(_fact(
            f"{inp.seriousness.serious} of {inp.seriousness.total_reports} distinct case(s) "
            f"were flagged serious; {inp.seriousness.seriousness_unknown} had unknown seriousness.",
            _cite_analysis(inp.seriousness)))
    if inp.dedup:
        confirmed = sum(1 for g in inp.dedup.groups if g.certainty.value == "confirmed")
        likely = sum(1 for g in inp.dedup.groups if g.certainty.value == "likely")
        exec_claims.append(_fact(
            f"{inp.dedup.unique_report_count} distinct case(s) after resolving "
            f"{confirmed} confirmed version chain(s)/duplicate(s); {likely} likely-duplicate "
            f"group(s) were flagged for human review, not merged.", _cite_analysis(inp.dedup)))
    sections.append(MemoSection(
        kind=MemoSectionKind.EXECUTIVE_SUMMARY, title="Executive summary", claims=exec_claims))

    # 5. Adverse-event evidence (aggregation + inspected serious cases)
    ae_claims: list[Claim] = []
    if inp.aggregation:
        top = list(inp.aggregation.by_reaction_term.items())[:5]
        ae_claims.append(_quote(  # embeds verbatim reported reaction terms
            f"{inp.aggregation.total_reports} report record(s) retrieved; most frequent reported "
            f"reactions: {top}.", _cite_analysis(inp.aggregation)))
    for rec in inp.serious_case_records:
        rep = rec.payload
        if not isinstance(rep, AdverseEventReport):
            continue
        reactions = ", ".join(x.term for x in rep.reactions) or "unspecified"
        ae_claims.append(_quote(  # embeds verbatim reported reaction terms
            f"Serious case {rep.report_id}: reactions=[{reactions}]; "
            f"death={'yes' if rep.serious_death else 'no'}.",
            Citation(kind=CitationKind.EVIDENCE, ref_id=rec.evidence_id)))
    if not ae_claims:
        ae_claims.append(_note("No adverse-event reports were retrieved for this query."))
    sections.append(MemoSection(
        kind=MemoSectionKind.ADVERSE_EVENT_EVIDENCE, title="Adverse-event evidence", claims=ae_claims))

    # 6. Temporal pattern (descriptive, not rates)
    if inp.temporal:
        counts = {pc.label: pc.report_count for pc in inp.temporal.period_counts}
        sections.append(MemoSection(
            kind=MemoSectionKind.TEMPORAL_PATTERN, title="Temporal pattern",
            claims=[_fact(
                f"Report counts by year: {counts}; direction: {inp.temporal.direction}. "
                f"These are counts of spontaneous reports, not incidence or rates.",
                _cite_analysis(inp.temporal))]))

    # 7. Seriousness & missingness
    sm_claims: list[Claim] = []
    if inp.seriousness:
        sm_claims.append(_fact(
            f"Seriousness by criterion: {inp.seriousness.by_criterion}.",
            _cite_analysis(inp.seriousness)))
    if inp.missingness:
        sm_claims.append(_fact(
            f"Missingness (fraction of reports missing each field): {inp.missingness.missing_fraction}.",
            _cite_analysis(inp.missingness)))
    if sm_claims:
        sections.append(MemoSection(
            kind=MemoSectionKind.SERIOUSNESS_MISSINGNESS, title="Seriousness and missingness",
            claims=sm_claims))

    # 8. Label evidence (described neutrally, cited by id --- raw text not quoted)
    label_claims: list[Claim] = []
    for rec in inp.label_records:
        sec = rec.payload
        if isinstance(sec, LabelSection):
            eff = f" (effective {sec.effective_date})" if sec.effective_date else ""
            label_claims.append(_fact(
                f"Label section '{sec.section.value}'{eff} addresses the event; "
                f"the label does not assert causation.",
                Citation(kind=CitationKind.LABEL_SECTION, ref_id=rec.evidence_id)))
    if not label_claims:
        label_claims.append(_note("No label section was retrieved."))
    sections.append(MemoSection(
        kind=MemoSectionKind.LABEL_EVIDENCE, title="Label evidence", claims=label_claims))

    # 9. External evidence (literature)
    lit_claims: list[Claim] = []
    for rec in inp.literature_records:
        ref = rec.payload
        if isinstance(ref, LiteratureReference):
            date_str = f", {ref.pub_date}" if ref.pub_date else ""
            lit_claims.append(_quote(  # verbatim paper title
                f"PMID {ref.pmid}{date_str}: \"{ref.title}\".",
                Citation(kind=CitationKind.EVIDENCE, ref_id=rec.evidence_id)))
    if not lit_claims:
        lit_claims.append(_note("No external literature was retrieved."))
    sections.append(MemoSection(
        kind=MemoSectionKind.EXTERNAL_EVIDENCE, title="External evidence", claims=lit_claims))

    # 10. Conflicting evidence (disagreement preserved)
    conflict_claims: list[Claim] = []
    if inp.conflict:
        # description is SYSTEM-authored prose (scanned); positions quote source text.
        conflict_claims.append(_fact(inp.conflict.description, _cite_analysis(inp.conflict)))
        for pos in inp.conflict.positions:
            conflict_claims.append(_quote(pos, _cite_analysis(inp.conflict)))
    else:
        conflict_claims.append(_note("Fewer than two source types were available to compare."))
    sections.append(MemoSection(
        kind=MemoSectionKind.CONFLICTING_EVIDENCE, title="Conflicting evidence", claims=conflict_claims))

    # 11. Limitations
    lim_claims = [
        _note("Spontaneous adverse-event reports cannot establish that the drug caused the "
              "event, and cannot be used to compute incidence or occurrence rates."),
        _note("Public reports may be incomplete, duplicated, or unverified."),
    ]
    for reason in inp.sufficiency_reasons:
        lim_claims.append(_note(reason))
    sections.append(MemoSection(
        kind=MemoSectionKind.LIMITATIONS, title="Limitations", claims=lim_claims))

    # 12. Unresolved questions
    sections.append(MemoSection(
        kind=MemoSectionKind.UNRESOLVED_QUESTIONS, title="Unresolved questions", claims=[
            _note("Do the likely-duplicate groups represent the same case? (requires manual review)"),
            _note("What is the clinical context of the serious cases (confounders, comorbidity)?")]))

    # 13. Human-review considerations
    sections.append(MemoSection(
        kind=MemoSectionKind.HUMAN_REVIEW_CONSIDERATIONS, title="Human-review considerations", claims=[
            _note("This memo is advisory. A human safety professional must review the individual "
                  "serious cases and decide whether deeper evaluation is warranted.")]))

    # 14. Source references
    ref_claims: list[Claim] = []
    for rec in inp.label_records + inp.literature_records + inp.serious_case_records:
        p = rec.provenance
        ref_claims.append(_note(
            f"{rec.evidence_id}: {p.source} | query='{p.query}' | retrieved {p.retrieved_at.date()}"))
    if not ref_claims:
        ref_claims.append(_note("No source records were cited."))
    sections.append(MemoSection(
        kind=MemoSectionKind.SOURCE_REFERENCES, title="Source references", claims=ref_claims))

    _attach_consumed_hashes(inp, sections)
    return Memo(investigation_id=inv.investigation_id, run_id=inp.run_id,
                model_tag=inp.model_tag, sections=sections)


def _attach_consumed_hashes(inp: MemoInputs, sections: list[MemoSection]) -> None:
    """Record, per section, the content/output hashes it was built from --- resolved
    from each claim's citations. This is what lets the dependency graph mark exactly
    the sections that consumed changed evidence as stale (Scenario A)."""
    analysis_hash: dict[str, str] = {}
    for res in (inp.normalization, inp.aggregation, inp.seriousness, inp.missingness,
                inp.dedup, inp.temporal, inp.conflict):
        if res is not None:
            analysis_hash[res.result_id] = res.output_hash
    evidence_hash: dict[str, str] = {}
    for rec in inp.label_records + inp.literature_records + inp.serious_case_records:
        evidence_hash[rec.evidence_id] = rec.content_hash

    for section in sections:
        hashes: set[str] = set()
        for claim in section.claims:
            for cit in claim.citations:
                if cit.ref_id in analysis_hash:
                    hashes.add(analysis_hash[cit.ref_id])
                elif cit.ref_id in evidence_hash:
                    hashes.add(evidence_hash[cit.ref_id])
        section.consumed_output_hashes = sorted(hashes)
