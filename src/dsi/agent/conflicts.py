"""Deterministic conflict detection across sources.

Builds a `ConflictFinding` that PRESERVES each source's position (with its date and
limitations) and flags disagreement --- it never forces consensus or drops evidence.
The classic montelukast case: a FAERS spontaneous-report signal sits next to an
observational study reporting no increased risk, while the label acknowledges the
events but not causation. All three positions are recorded; `unresolved` is set when
a signal indicator and a no-signal indicator co-occur.
"""

from __future__ import annotations

import re

from dsi.analysis.dedup import collapse_to_latest_versions
from dsi.analysis.selectors import adverse_event_reports, label_sections, literature_refs
from dsi.domain.analysis import ConflictFinding, make_provenance_fields
from dsi.domain.evidence import EvidenceRecord

_NO_SIGNAL_RE = re.compile(r"no (increased|elevated) risk|not associated|no association|"
                           r"no significant", re.IGNORECASE)
_SIGNAL_RE = re.compile(r"suicid|case series|associated with|increased risk|signal", re.IGNORECASE)


def detect_conflicts(records: list[EvidenceRecord], investigation_id: str) -> ConflictFinding | None:
    collapsed = collapse_to_latest_versions(records)
    cases = [r for _, r in adverse_event_reports(collapsed)]
    labels = [(h, s) for h, s in label_sections(collapsed)]
    refs = [(h, x) for h, x in literature_refs(collapsed)]

    source_types = sum(bool(x) for x in (cases, labels, refs))
    if source_types < 2:
        return None  # need at least two sources to have a conflict

    positions: list[str] = []
    consumed: list[str] = []

    # FAERS position
    serious = sum(1 for c in cases if c.serious is True)
    if cases:
        positions.append(
            f"FAERS spontaneous reports: {len(cases)} case(s), {serious} flagged serious "
            f"(spontaneous reports cannot establish causation or rates).")
        consumed += [h for h, _ in adverse_event_reports(collapsed)]

    # Label position
    faers_signal = len(cases) > 0
    label_ack = False
    for h, sec in labels:
        positions.append(
            f"Label section '{sec.section.value}'"
            + (f" (effective {sec.effective_date})" if sec.effective_date else "")
            + ": describes the event; label does not assert causation.")
        consumed.append(h)
        label_ack = True

    # Literature positions
    lit_no_signal = lit_signal = False
    for h, ref in refs:
        title = ref.title or ""
        tag = ""
        if _NO_SIGNAL_RE.search(title):
            lit_no_signal = True
            tag = " [reports no increased risk]"
        elif _SIGNAL_RE.search(title):
            lit_signal = True
            tag = " [reports a signal]"
        date_str = f", {ref.pub_date}" if ref.pub_date else ""
        positions.append(f"Literature PMID {ref.pmid}{date_str}: \"{title}\"{tag}.")
        consumed.append(h)

    # Disagreement: a no-signal study alongside a FAERS signal (or a signal study).
    unresolved = lit_no_signal and (faers_signal or lit_signal)
    if unresolved:
        description = ("Sources do not point in the same direction: a spontaneous-report "
                       "signal and/or case reports coexist with an observational study "
                       "reporting no increased risk. The disagreement is preserved; it is "
                       "not resolved by this system.")
    else:
        description = ("Sources are broadly consistent or incomplete; no direct "
                       "contradiction detected, but see individual source limitations.")

    body = {"description": description, "positions": positions, "unresolved": unresolved}
    prov = make_provenance_fields(consumed, body)
    return ConflictFinding(investigation_id=investigation_id, description=description,
                           positions=positions, unresolved=unresolved, **prov)
