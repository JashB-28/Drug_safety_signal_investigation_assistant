"""Tests for evidence records, provenance, and the content-only hashing rule."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from dsi.domain.evidence import (
    AdverseEventReport,
    DrugEntry,
    DrugRole,
    EvidenceRecord,
    LabelSection,
    LabelSectionName,
    LiteratureReference,
    ReactionEntry,
)
from dsi.domain.provenance import Provenance, SourceType


def _prov(ts: datetime, source_type: SourceType = SourceType.FAERS) -> Provenance:
    return Provenance(
        source_type=source_type,
        source="openFDA/drug/event",
        query="montelukast+neuropsychiatric",
        retrieved_at=ts,
    )


def test_create_computes_id_and_hash():
    report = AdverseEventReport(report_id="R1", report_version=1)
    rec = EvidenceRecord.create(report, _prov(datetime(2026, 1, 1, tzinfo=timezone.utc)))
    assert rec.evidence_id.startswith("evd_")
    assert rec.content_hash == rec.recompute_hash()


def test_content_hash_ignores_retrieval_timestamp():
    """Same content retrieved at two different times must hash identically."""
    report = AdverseEventReport(report_id="R1", report_version=1)
    a = EvidenceRecord.create(report, _prov(datetime(2026, 1, 1, tzinfo=timezone.utc)))
    b = EvidenceRecord.create(report, _prov(datetime(2026, 6, 30, tzinfo=timezone.utc)))
    assert a.content_hash == b.content_hash  # detects "nothing actually changed"


def test_content_hash_changes_when_payload_changes():
    a = EvidenceRecord.create(AdverseEventReport(report_id="R1", report_version=1), _prov(datetime.now(timezone.utc)))
    b = EvidenceRecord.create(AdverseEventReport(report_id="R1", report_version=2), _prov(datetime.now(timezone.utc)))
    assert a.content_hash != b.content_hash


def test_missingness_is_none_not_invented():
    report = AdverseEventReport(report_id="R1")
    assert report.patient_age is None
    assert report.serious is None
    assert report.reactions == []


def test_discriminated_union_roundtrip():
    """A record with each payload kind serializes and reloads to the right type."""
    payloads = [
        AdverseEventReport(report_id="R1", drugs=[DrugEntry(name="Singulair", role=DrugRole.PRIMARY_SUSPECT)],
                           reactions=[ReactionEntry(term="Depression")]),
        LabelSection(drug_name="montelukast", section=LabelSectionName.BOXED_WARNING, text="..."),
        LiteratureReference(pmid="12345", title="A study"),
    ]
    for p in payloads:
        rec = EvidenceRecord.create(p, _prov(datetime.now(timezone.utc)))
        dumped = rec.model_dump_json()
        loaded = EvidenceRecord.model_validate_json(dumped)
        assert type(loaded.payload) is type(p)
        assert loaded.content_hash == rec.content_hash


def test_provenance_is_frozen():
    p = _prov(datetime.now(timezone.utc))
    with pytest.raises(ValidationError):
        p.query = "changed"  # provenance must not mutate after capture


def test_synthetic_flag_defaults_false_and_can_be_set():
    assert _prov(datetime.now(timezone.utc)).is_synthetic is False
    synth = Provenance(
        source_type=SourceType.SYNTHETIC,
        source="fixture",
        query="edge-case",
        retrieved_at=datetime.now(timezone.utc),
        is_synthetic=True,
    )
    assert synth.is_synthetic is True


def test_label_section_carries_version_fields():
    sec = LabelSection(
        drug_name="montelukast",
        section=LabelSectionName.BOXED_WARNING,
        text="Serious neuropsychiatric events...",
        spl_set_id="set-123",
        spl_version="7",
        effective_date=date(2020, 3, 4),
    )
    assert sec.spl_version == "7"
    assert sec.effective_date == date(2020, 3, 4)
