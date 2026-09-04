"""Small helpers to pull typed payloads (and their content hashes) out of a mixed
list of evidence records. Keeps every analysis function from re-writing the same
filter/zip and guarantees `consumed_evidence_hashes` is derived consistently.
"""

from __future__ import annotations

from dsi.domain.evidence import (
    AdverseEventReport,
    EvidenceRecord,
    LabelSection,
    LiteratureReference,
)


def adverse_event_reports(records: list[EvidenceRecord]) -> list[tuple[str, AdverseEventReport]]:
    """Return (content_hash, report) for each FAERS evidence record."""
    return [(r.content_hash, r.payload) for r in records
            if isinstance(r.payload, AdverseEventReport)]


def label_sections(records: list[EvidenceRecord]) -> list[tuple[str, LabelSection]]:
    return [(r.content_hash, r.payload) for r in records
            if isinstance(r.payload, LabelSection)]


def literature_refs(records: list[EvidenceRecord]) -> list[tuple[str, LiteratureReference]]:
    return [(r.content_hash, r.payload) for r in records
            if isinstance(r.payload, LiteratureReference)]
