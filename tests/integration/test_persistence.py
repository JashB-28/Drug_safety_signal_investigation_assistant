"""Persistence round-trips and the evidence-immutability guarantee."""

from __future__ import annotations

import sqlite3

import pytest

from dsi.domain.memo import Claim, Citation, CitationKind, Memo, MemoSection, MemoSectionKind
from dsi.domain.analysis import SeriousnessSummary
from dsi.persistence.repositories import (
    AnalysisRepo,
    EvidenceRepo,
    InvestigationRepo,
    MemoRepo,
    StateRepo,
)
from dsi.domain.state import AgentState
from dsi.domain.investigation import ReviewPeriod
from datetime import date


def test_investigation_roundtrip(db, investigation):
    repo = InvestigationRepo(db)
    repo.save(investigation)
    loaded = repo.get(investigation.investigation_id)
    assert loaded is not None
    assert loaded.drug == "montelukast"
    assert loaded.review_period.start == date(2019, 1, 1)


def test_evidence_roundtrip_and_provenance_preserved(db, investigation, make_report):
    InvestigationRepo(db).save(investigation)
    repo = EvidenceRepo(db)
    rec = make_report("R1", serious=True)
    assert repo.save(investigation.investigation_id, rec) is True
    loaded = repo.get(rec.evidence_id)
    assert loaded is not None
    assert loaded.content_hash == rec.content_hash
    assert loaded.provenance.source == "openFDA/drug/event"
    assert loaded.payload.report_id == "R1"


def test_duplicate_content_hash_is_noop_write(db, investigation, make_report):
    """Re-saving identical content returns False and does not duplicate --- this is
    what lets resume avoid redundant writes."""
    InvestigationRepo(db).save(investigation)
    repo = EvidenceRepo(db)
    rec = make_report("R1")
    assert repo.save(investigation.investigation_id, rec) is True
    # A different EvidenceRecord object but identical payload content:
    same_content = make_report("R1")
    assert same_content.content_hash == rec.content_hash
    assert repo.save(investigation.investigation_id, same_content) is False
    assert repo.count_for(investigation.investigation_id) == 1


def test_evidence_is_immutable_update_blocked(db, investigation, make_report):
    InvestigationRepo(db).save(investigation)
    repo = EvidenceRepo(db)
    rec = make_report("R1")
    repo.save(investigation.investigation_id, rec)
    with pytest.raises(sqlite3.IntegrityError):
        with db.transaction() as c:
            c.execute("UPDATE evidence SET payload_json = '{}' WHERE evidence_id = ?",
                      (rec.evidence_id,))


def test_evidence_is_immutable_delete_blocked(db, investigation, make_report):
    InvestigationRepo(db).save(investigation)
    repo = EvidenceRepo(db)
    rec = make_report("R1")
    repo.save(investigation.investigation_id, rec)
    with pytest.raises(sqlite3.IntegrityError):
        with db.transaction() as c:
            c.execute("DELETE FROM evidence WHERE evidence_id = ?", (rec.evidence_id,))


def test_analysis_result_roundtrip(db, investigation):
    InvestigationRepo(db).save(investigation)
    res = SeriousnessSummary(
        investigation_id=investigation.investigation_id,
        inputs_hash="ih", output_hash="oh", total_reports=5, serious=3,
    )
    AnalysisRepo(db).save(investigation.investigation_id, "run_1", res)
    rows = AnalysisRepo(db).get_raw_for_run(investigation.investigation_id, "run_1")
    assert len(rows) == 1
    assert rows[0]["kind"] == "seriousness"
    assert rows[0]["output_hash"] == "oh"


def test_memo_versions_preserved(db, investigation):
    InvestigationRepo(db).save(investigation)
    repo = MemoRepo(db)
    for run in ("run_1", "run_2"):
        memo = Memo(
            investigation_id=investigation.investigation_id, run_id=run, model_tag="mistral:7b-instruct",
            sections=[MemoSection(kind=MemoSectionKind.EXECUTIVE_SUMMARY, title="Summary",
                                  claims=[Claim(text="x", citations=[
                                      Citation(kind=CitationKind.ANALYSIS, ref_id="ana_1")])])],
        )
        repo.save(memo)
    assert repo.count_for(investigation.investigation_id) == 2
    assert repo.get_for_run(investigation.investigation_id, "run_2") is not None


def test_state_save_and_latest_run(db, investigation):
    InvestigationRepo(db).save(investigation)
    repo = StateRepo(db)
    st = AgentState(
        investigation_id=investigation.investigation_id, run_id="run_1",
        drug="montelukast", event="neuropsychiatric events",
        review_period=ReviewPeriod(start=date(2019, 1, 1), end=date(2021, 12, 31)),
        evidence_ids=["evd_1", "evd_2"],
    )
    repo.save(st)
    loaded = repo.load(investigation.investigation_id, "run_1")
    assert loaded is not None and loaded.evidence_ids == ["evd_1", "evd_2"]
    assert repo.latest_run(investigation.investigation_id).run_id == "run_1"
