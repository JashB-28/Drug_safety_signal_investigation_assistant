"""Time-period comparison.

Buckets reports by calendar year across the review period and reports the
direction of the *report count* (increase / decrease / flat). This is explicitly
a count trend of spontaneous reports --- NOT incidence, NOT a rate, and NOT
evidence of causation. Reporting can rise for many reasons (media attention, a
label change, stimulated reporting), so the direction is descriptive only and the
result carries that disclaimer.
"""

from __future__ import annotations

from dsi.domain.analysis import PeriodCount, TemporalComparison, make_provenance_fields
from dsi.domain.evidence import EvidenceRecord
from dsi.domain.investigation import ReviewPeriod
from dsi.analysis.selectors import adverse_event_reports

_DISCLAIMER = "Counts of spontaneous reports only; not incidence, rates, or causal evidence."


def compare_periods(
    records: list[EvidenceRecord], review_period: ReviewPeriod, investigation_id: str
) -> TemporalComparison:
    pairs = adverse_event_reports(records)
    hashes = [h for h, _ in pairs]
    reports = [r for _, r in pairs]

    years = list(range(review_period.start.year, review_period.end.year + 1))
    counts = {str(y): 0 for y in years}
    for rep in reports:
        if rep.receive_date and str(rep.receive_date.year) in counts:
            counts[str(rep.receive_date.year)] += 1

    period_counts = [PeriodCount(label=str(y), report_count=counts[str(y)]) for y in years]
    years_with_data = [y for y in years if counts[str(y)] > 0]

    if len(years_with_data) < 2:
        direction = "insufficient_data"
    else:
        first = counts[str(years_with_data[0])]
        last = counts[str(years_with_data[-1])]
        direction = "increase" if last > first else "decrease" if last < first else "flat"

    body = {
        "period_counts": [pc.model_dump() for pc in period_counts],
        "direction": direction,
        "note": _DISCLAIMER,
    }
    prov = make_provenance_fields(hashes, body)
    return TemporalComparison(investigation_id=investigation_id, period_counts=period_counts,
                              direction=direction, note=_DISCLAIMER, **prov)
