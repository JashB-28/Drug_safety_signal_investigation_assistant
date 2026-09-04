"""Deterministic sufficiency check.

Decides whether the gathered evidence is adequate to write a substantive memo, or
whether the agent should stop safely and say so. This is plain rules, not an LLM
judgment: zero adverse-event reports is the hard 'insufficient' case (the safe-stop
path); a small number is 'limited' but still workable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dsi.analysis.dedup import collapse_to_latest_versions
from dsi.analysis.selectors import adverse_event_reports, label_sections, literature_refs
from dsi.domain.evidence import EvidenceRecord

_LIMITED_THRESHOLD = 3  # fewer distinct cases than this is workable but explicitly "limited"


@dataclass
class SufficiencyVerdict:
    sufficient: bool
    case_count: int
    label_section_count: int
    literature_count: int
    reasons: list[str] = field(default_factory=list)


def check_sufficiency(records: list[EvidenceRecord]) -> SufficiencyVerdict:
    collapsed = collapse_to_latest_versions(records)
    cases = adverse_event_reports(collapsed)
    labels = label_sections(collapsed)
    lit = literature_refs(collapsed)

    reasons: list[str] = []
    sufficient = True
    if not cases:
        sufficient = False
        reasons.append("No adverse-event reports were found for this drug/event/period.")
    elif len(cases) < _LIMITED_THRESHOLD:
        reasons.append(f"Only {len(cases)} distinct case(s) found; evidence is limited.")
    if not labels:
        reasons.append("No label section was retrieved; label context is missing.")
    if not lit:
        reasons.append("No external literature was retrieved.")

    return SufficiencyVerdict(
        sufficient=sufficient,
        case_count=len(cases),
        label_section_count=len(labels),
        literature_count=len(lit),
        reasons=reasons,
    )
