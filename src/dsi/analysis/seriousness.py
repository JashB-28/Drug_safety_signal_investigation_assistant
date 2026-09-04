"""Seriousness and missingness summaries.

Seriousness: how many reports are flagged serious, and by which criteria (death,
hospitalization, ...). Missingness: how complete the reports are --- the fraction
of reports missing key fields. Both are exact counts the memo must cite verbatim,
and both treat an unreported value as unknown (`None`), never as a default.
"""

from __future__ import annotations

from dsi.domain.analysis import MissingnessSummary, SeriousnessSummary, make_provenance_fields
from dsi.domain.evidence import EvidenceRecord
from dsi.analysis.selectors import adverse_event_reports

# The seriousness criteria and the report attribute backing each one.
_CRITERIA = {
    "death": "serious_death",
    "hospitalization": "serious_hospitalization",
    "life_threatening": "serious_life_threatening",
    "disabling": "serious_disabling",
    "congenital_anomaly": "serious_congenital_anomaly",
    "other": "serious_other",
}

# Fields whose absence we track as missingness.
_MISSINGNESS_FIELDS = [
    "patient_age", "patient_sex", "receive_date", "reporter_qualification", "serious",
]


def summarize_seriousness(records: list[EvidenceRecord], investigation_id: str) -> SeriousnessSummary:
    pairs = adverse_event_reports(records)
    hashes = [h for h, _ in pairs]
    reports = [r for _, r in pairs]

    serious = sum(1 for r in reports if r.serious is True)
    non_serious = sum(1 for r in reports if r.serious is False)
    unknown = sum(1 for r in reports if r.serious is None)
    by_criterion = {
        name: sum(1 for r in reports if getattr(r, attr) is True)
        for name, attr in _CRITERIA.items()
    }

    body = {
        "total_reports": len(reports),
        "serious": serious,
        "non_serious": non_serious,
        "seriousness_unknown": unknown,
        "by_criterion": by_criterion,
    }
    prov = make_provenance_fields(hashes, body)
    return SeriousnessSummary(investigation_id=investigation_id, **body, **prov)


def summarize_missingness(records: list[EvidenceRecord], investigation_id: str) -> MissingnessSummary:
    pairs = adverse_event_reports(records)
    hashes = [h for h, _ in pairs]
    reports = [r for _, r in pairs]
    n = len(reports)

    missing_counts: dict[str, int] = {}
    missing_fraction: dict[str, float] = {}
    for field in _MISSINGNESS_FIELDS:
        missing = sum(1 for r in reports if getattr(r, field) is None)
        missing_counts[field] = missing
        missing_fraction[field] = round(missing / n, 4) if n else 0.0

    body = {
        "total_reports": n,
        "missing_counts": missing_counts,
        "missing_fraction": missing_fraction,
    }
    prov = make_provenance_fields(hashes, body)
    return MissingnessSummary(investigation_id=investigation_id, **body, **prov)
