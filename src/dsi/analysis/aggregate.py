"""Report aggregation --- descriptive counts over the FAERS reports.

Counts only. These are tallies of spontaneous reports, never rates or incidence.
"""

from __future__ import annotations

from collections import Counter

from dsi.domain.analysis import AggregationResult, make_provenance_fields
from dsi.domain.evidence import EvidenceRecord
from dsi.analysis.selectors import adverse_event_reports


def aggregate_reports(records: list[EvidenceRecord], investigation_id: str) -> AggregationResult:
    pairs = adverse_event_reports(records)
    hashes = [h for h, _ in pairs]
    reports = [r for _, r in pairs]

    by_year: Counter[str] = Counter()
    by_reaction: Counter[str] = Counter()
    by_seriousness: Counter[str] = Counter()

    for rep in reports:
        year = str(rep.receive_date.year) if rep.receive_date else "unknown"
        by_year[year] += 1
        for reaction in rep.reactions:
            by_reaction[reaction.term] += 1
        if rep.serious is True:
            by_seriousness["serious"] += 1
        elif rep.serious is False:
            by_seriousness["non_serious"] += 1
        else:
            by_seriousness["unknown"] += 1

    body = {
        "total_reports": len(reports),
        "by_year": dict(sorted(by_year.items())),
        "by_reaction_term": dict(sorted(by_reaction.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_seriousness": dict(sorted(by_seriousness.items())),
    }
    prov = make_provenance_fields(hashes, body)
    return AggregationResult(investigation_id=investigation_id, **body, **prov)
