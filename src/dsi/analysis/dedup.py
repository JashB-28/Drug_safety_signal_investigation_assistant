"""Duplicate and version resolution.

Public reports are noisy: a case can have follow-up versions, and separate
submissions can describe the same event. We distinguish two certainty levels and
NEVER assert a merge we cannot prove:

  * CONFIRMED --- records that share a FAERS `report_id`. Same id = same case, so
    multiple versions are a follow-up chain and a repeated (id, version) is an
    exact duplicate. This is certain.
  * LIKELY    --- records with DIFFERENT ids that nonetheless share a distinctive
    fingerprint (sex + age + reactions + date + country). Plausibly the same case,
    but not certain, so it is flagged for human review, not merged.

`unique_report_count` counts distinct `report_id`s (confirmed identity only).
Likely duplicates are surfaced but deliberately do not reduce that count.

Identifier note (the FAERS trap): `report_id` maps to openFDA `safetyreportid`,
which is the CASE-level id (FAERS CASEID), stable across follow-ups; the version is
`report_version` (safetyreportversion). The canonical FAERS reduction is therefore
"keep the latest version per case" --- `collapse_to_latest_versions` below. COUNT
analyses (aggregation, seriousness, missingness, temporal) must run on that
collapsed set, or a followed-up case is counted once per version.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from dsi.domain.analysis import (
    DedupResult,
    DuplicateGroup,
    DuplicateGroupCertainty,
    make_provenance_fields,
)
from dsi.domain.evidence import AdverseEventReport, EvidenceRecord


def _version_key(rep: AdverseEventReport) -> tuple[int, date]:
    """Ordering used to pick the newest version of a case: highest version, then
    latest receive date. Missing values sort lowest so a real value always wins."""
    return (rep.report_version if rep.report_version is not None else -1,
            rep.receive_date or date.min)


def collapse_to_latest_versions(records: list[EvidenceRecord]) -> list[EvidenceRecord]:
    """The canonical FAERS reduction: one record per case (highest version).

    Non-FAERS records pass through unchanged. Returns a deterministically ordered
    list so downstream hashes are stable.
    """
    best: dict[str, EvidenceRecord] = {}
    passthrough: list[EvidenceRecord] = []
    for r in records:
        if not isinstance(r.payload, AdverseEventReport):
            passthrough.append(r)
            continue
        case_id = r.payload.report_id
        current = best.get(case_id)
        if current is None or _version_key(r.payload) > _version_key(current.payload):
            best[case_id] = r
    collapsed = sorted(best.values(), key=lambda r: r.payload.report_id)
    passthrough.sort(key=lambda r: r.evidence_id)
    return collapsed + passthrough


def _report_records(records: list[EvidenceRecord]):
    for r in records:
        if isinstance(r.payload, AdverseEventReport):
            yield r.evidence_id, r.content_hash, r.payload


def _likely_key(rep: AdverseEventReport) -> tuple | None:
    """A distinctive fingerprint, or None when there is too little to compare."""
    reactions = frozenset(x.term.lower() for x in rep.reactions)
    if rep.patient_sex is None or rep.patient_age is None or not reactions:
        return None  # not enough signal to even suspect a duplicate
    return (
        rep.patient_sex,
        rep.patient_age,
        rep.receive_date.isoformat() if rep.receive_date else None,
        rep.occur_country,
        reactions,
    )


def resolve_duplicates(records: list[EvidenceRecord], investigation_id: str) -> DedupResult:
    by_id: dict[str, list[tuple[str, int | None]]] = defaultdict(list)  # report_id -> [(evid, version)]
    id_of_evid: dict[str, str] = {}
    reps: dict[str, AdverseEventReport] = {}

    for evid, _hash, rep in _report_records(records):
        by_id[rep.report_id].append((evid, rep.report_version))
        id_of_evid[evid] = rep.report_id
        reps[evid] = rep

    groups: list[DuplicateGroup] = []

    # --- CONFIRMED: same report_id (version chain and/or exact duplicate) ---
    for report_id, members in by_id.items():
        if len(members) < 2:
            continue
        versions = [v for _, v in members]
        evids = [e for e, _ in members]
        if len(set(versions)) < len(versions):
            reason = f"same report_id {report_id} with a repeated version (exact duplicate)"
        else:
            shown = "->".join(str(v) for v in sorted(versions, key=lambda x: (x is None, x)))
            reason = f"same report_id {report_id}, version chain {shown}"
        groups.append(DuplicateGroup(
            certainty=DuplicateGroupCertainty.CONFIRMED, evidence_ids=sorted(evids), reason=reason))

    # --- LIKELY: different report_ids sharing a distinctive fingerprint ---
    by_key: dict[tuple, list[str]] = defaultdict(list)
    for evid, rep in reps.items():
        key = _likely_key(rep)
        if key is not None:
            by_key[key].append(evid)
    for evids in by_key.values():
        distinct_ids = {id_of_evid[e] for e in evids}
        if len(distinct_ids) >= 2:  # only across different cases
            groups.append(DuplicateGroup(
                certainty=DuplicateGroupCertainty.LIKELY, evidence_ids=sorted(evids),
                reason="different report_ids sharing sex/age/reactions/date/country"))

    unique_report_count = len(by_id)  # confirmed identity only

    body = {
        "groups": [g.model_dump(mode="json") for g in groups],
        "unique_report_count": unique_report_count,
    }
    prov = make_provenance_fields([h for _, h, _ in _report_records(records)], body)
    return DedupResult(investigation_id=investigation_id, groups=groups,
                       unique_report_count=unique_report_count, **prov)
