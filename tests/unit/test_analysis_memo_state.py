"""Tests for analysis-result provenance, memo citation structure, and agent state."""

from __future__ import annotations

from dsi.domain.analysis import (
    AnalysisKind,
    DedupResult,
    DuplicateGroup,
    DuplicateGroupCertainty,
    SeriousnessSummary,
    TemporalComparison,
    make_provenance_fields,
)
from dsi.domain.memo import (
    Citation,
    CitationKind,
    Claim,
    Memo,
    MemoSection,
    MemoSectionKind,
)
from dsi.domain.state import (
    ActionType,
    AgentState,
    Budget,
    Decision,
    InvestigationStatus,
)
from dsi.domain.investigation import ReviewPeriod
from datetime import date


# --- analysis provenance / dependency tracking ----------------------------- #
def test_make_provenance_fields_are_order_independent_and_hash_output():
    body = {"total_reports": 3, "serious": 2}  # output data only, not the full result
    f1 = make_provenance_fields(["hb", "ha"], body)
    f2 = make_provenance_fields(["ha", "hb"], body)
    assert f1["consumed_evidence_hashes"] == ["ha", "hb"]  # sorted
    assert f1["inputs_hash"] == f2["inputs_hash"]           # order independent
    assert len(f1["output_hash"]) == 64                     # sha-256 hex


def test_output_hash_changes_with_output_body():
    a = make_provenance_fields(["h"], {"serious": 1})
    b = make_provenance_fields(["h"], {"serious": 2})
    assert a["output_hash"] != b["output_hash"]


def test_seriousness_summary_kind_is_fixed():
    s = SeriousnessSummary(investigation_id="inv_1", inputs_hash="x", output_hash="y")
    assert s.kind is AnalysisKind.SERIOUSNESS


def test_dedup_distinguishes_confirmed_from_likely():
    groups = [
        DuplicateGroup(certainty=DuplicateGroupCertainty.CONFIRMED, evidence_ids=["e1", "e2"],
                       reason="same report_id v1->v2"),
        DuplicateGroup(certainty=DuplicateGroupCertainty.LIKELY, evidence_ids=["e3", "e4"],
                       reason="shared age/sex/date heuristic"),
    ]
    res = DedupResult(investigation_id="inv_1", inputs_hash="x", output_hash="y", groups=groups)
    confirmed = [g for g in res.groups if g.certainty is DuplicateGroupCertainty.CONFIRMED]
    likely = [g for g in res.groups if g.certainty is DuplicateGroupCertainty.LIKELY]
    assert len(confirmed) == 1 and len(likely) == 1


def test_temporal_default_note_disclaims_rates():
    t = TemporalComparison(investigation_id="inv_1", inputs_hash="x", output_hash="y")
    assert "not incidence" in t.note.lower()
    assert t.direction == "insufficient_data"


# --- memo citation structure ----------------------------------------------- #



def test_fully_cited_memo_has_no_uncited_claims():
    memo = Memo(
        investigation_id="inv_1", run_id="run_1", model_tag="m",
        sections=[
            MemoSection(kind=MemoSectionKind.LABEL_EVIDENCE, title="Label", claims=[
                Claim(text="Boxed warning present.", citations=[
                    Citation(kind=CitationKind.LABEL_SECTION, ref_id="evd_9")]),
            ])
        ],
    )
    assert memo.uncited_material_claims() == []


# --- agent state ----------------------------------------------------------- #
def _state() -> AgentState:
    return AgentState(
        investigation_id="inv_1",
        drug="montelukast",
        event="neuropsychiatric events",
        review_period=ReviewPeriod(start=date(2019, 1, 1), end=date(2021, 12, 31)),
    )


def test_record_decision_advances_step_and_sets_next_action():
    st = _state()
    assert st.step_index == 0 and st.next_action is None
    st.record_decision(Decision(
        step_index=0, observed_state={"evidence": 0},
        chosen_action=ActionType.RETRIEVE_FAERS, rationale="no evidence yet",
    ))
    assert st.step_index == 1
    assert st.next_action is ActionType.RETRIEVE_FAERS
    assert st.decisions[0].observed_state == {"evidence": 0}
    assert st.status is InvestigationStatus.INITIALIZED


def test_budget_limits():
    b = Budget(max_total_tokens=100, total_tokens_used=100)
    assert b.total_exceeded() is True
    assert b.remaining_total() == 0
    b2 = Budget(max_total_tokens=100, total_tokens_used=30)
    assert b2.total_exceeded() is False
    assert b2.remaining_total() == 70
    assert Budget().total_exceeded() is False  # unbounded by default
    assert Budget().remaining_total() is None
