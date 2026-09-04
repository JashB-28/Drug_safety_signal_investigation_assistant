"""Kill-mid-investigation / resume.

Simulates a crash after the first gather step by reopening the SQLite file in a
fresh connection (a new 'process') and resuming the SAME run. The resume must not:
  * re-fetch the tool  (cache hit),
  * re-run the model   (normalized names already persisted in state),
  * duplicate evidence (content-hash dedup).

`fetch_calls` and `model_calls` are process-lifetime counters for *actual work*;
the assertions prove the second pass does zero additional work.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from dsi.domain.evidence import AdverseEventReport, EvidenceRecord
from dsi.domain.investigation import ReviewPeriod
from dsi.domain.provenance import Provenance, SourceType
from dsi.domain.state import AgentState, InvestigationStatus
from dsi.domain.tools import FaersSearchData, FaersSearchRequest
from dsi.persistence.cache import SnapshotCache
from dsi.persistence.db import Database
from dsi.persistence.repositories import EvidenceRepo, InvestigationRepo, StateRepo
from dsi.trace.models import TraceKind
from dsi.trace.spine import TraceSpine

INV_ID = "inv_test"
RUN_ID = "run_1"

fetch_calls = {"n": 0}
model_calls = {"n": 0}


def _prov() -> Provenance:
    return Provenance(
        source_type=SourceType.FAERS, source="openFDA/drug/event",
        query="montelukast+depression", retrieved_at=datetime.now(timezone.utc),
    )


def _fetch() -> FaersSearchData:
    fetch_calls["n"] += 1
    return FaersSearchData(
        reports=[AdverseEventReport(report_id="R1"), AdverseEventReport(report_id="R2")],
        total_matched=2, returned=2,
    )


def _gather(database: Database) -> AgentState:
    """One gather step, written to be safely re-runnable (idempotent)."""
    cache = SnapshotCache(database)
    ev_repo = EvidenceRepo(database)
    state_repo = StateRepo(database)
    spine = TraceSpine(database)

    state = state_repo.load(INV_ID, RUN_ID) or AgentState(
        investigation_id=INV_ID, run_id=RUN_ID, drug="montelukast",
        event="neuropsychiatric events",
        review_period=ReviewPeriod(start=date(2019, 1, 1), end=date(2021, 12, 31)),
    )

    req = FaersSearchRequest(drug="montelukast", event="depression")
    with spine.span(TraceKind.TOOL_CALL, "faers_search", INV_ID, RUN_ID) as rec:
        resp, hit = cache.get_or_fetch("faers_search", req, _fetch, FaersSearchData)
        rec.cache_hit = hit
        rec.records_read = resp.returned

    for report in resp.reports:
        record = EvidenceRecord.create(report, _prov())
        if ev_repo.save(INV_ID, record):        # False (no-op) if already stored
            state.evidence_ids.append(record.evidence_id)

    # A model call that must not repeat once its result is persisted in state.
    if not state.normalized_drug_names:
        with spine.span(TraceKind.MODEL_CALL, "normalize", INV_ID, RUN_ID) as mrec:
            model_calls["n"] += 1
            mrec.set_tokens(10, 5)
            state.normalized_drug_names = ["montelukast", "singulair"]

    state.status = InvestigationStatus.GATHERING
    state_repo.save(state)
    return state


def test_resume_does_no_redundant_work(tmp_path):
    fetch_calls["n"] = 0
    model_calls["n"] = 0
    db_path = tmp_path / "resume.sqlite"

    # --- first run, then "crash" (close the connection) ---
    db1 = Database.create(db_path)
    InvestigationRepo(db1).save(_investigation())
    _gather(db1)
    assert fetch_calls["n"] == 1
    assert model_calls["n"] == 1
    assert EvidenceRepo(db1).count_for(INV_ID) == 2
    db1.close()  # simulate process death

    # --- resume in a fresh connection ('new process') on the same file ---
    db2 = Database(db_path)  # schema already present
    resumed = _gather(db2)

    assert fetch_calls["n"] == 1        # cache hit -> NO re-fetch
    assert model_calls["n"] == 1        # persisted normalization -> NO re-run
    assert EvidenceRepo(db2).count_for(INV_ID) == 2  # dedup -> NO duplicate evidence
    assert resumed.normalized_drug_names == ["montelukast", "singulair"]

    # The trace shows the second tool call as a cache hit.
    spine = TraceSpine(db2)
    tool_events = [e for e in spine.events_for(INV_ID, RUN_ID) if e.name == "faers_search"]
    assert len(tool_events) == 2
    assert tool_events[0].cache_hit is False   # first: miss
    assert tool_events[1].cache_hit is True    # resume: hit
    db2.close()


def _investigation():
    from dsi.domain.investigation import Investigation
    return Investigation(
        investigation_id=INV_ID, drug="montelukast", event="neuropsychiatric events",
        review_period=ReviewPeriod(start=date(2019, 1, 1), end=date(2021, 12, 31)),
    )
