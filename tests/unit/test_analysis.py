"""Deterministic analysis: normalization, aggregation, seriousness/missingness,
dedup (confirmed vs likely), temporal comparison, and dependency tracking."""

from __future__ import annotations

from datetime import date, datetime, timezone

from dsi.analysis import (
    aggregate_reports,
    canonical_drug,
    collapse_to_latest_versions,
    compare_periods,
    expand_drug,
    expand_event,
    normalize,
    resolve_duplicates,
    summarize_missingness,
    summarize_seriousness,
)
from dsi.domain.analysis import DuplicateGroupCertainty
from dsi.domain.evidence import AdverseEventReport, EvidenceRecord, ReactionEntry
from dsi.domain.investigation import ReviewPeriod
from dsi.domain.provenance import Provenance, SourceType

INV = "inv_1"


def rec(report_id, version=1, serious=None, death=None, age=None, sex=None,
        rdate=None, reactions=(), country=None) -> EvidenceRecord:
    payload = AdverseEventReport(
        report_id=report_id, report_version=version, serious=serious, serious_death=death,
        patient_age=age, patient_sex=sex, receive_date=rdate, occur_country=country,
        reactions=[ReactionEntry(term=t) for t in reactions],
    )
    prov = Provenance(source_type=SourceType.FAERS, source="openFDA/drug/event",
                      query="montelukast", retrieved_at=datetime.now(timezone.utc))
    return EvidenceRecord.create(payload, prov)


# --- normalization --------------------------------------------------------- #
def test_drug_normalization_strips_salt_and_expands_synonyms():
    assert canonical_drug("MONTELUKAST SODIUM") == "montelukast"
    assert expand_drug("Singulair") == ["montelukast", "singulair"]
    assert expand_drug("montelukast sodium") == ["montelukast", "singulair"]
    assert expand_drug("aspirin") == ["aspirin"]  # unknown -> itself


def test_event_normalization_expands_and_falls_back():
    terms = expand_event("neuropsychiatric events")
    assert "depression" in terms and "suicidal ideation" in terms
    assert expand_event("rash") == ["rash"]


def test_normalization_result_is_hashed_and_query_driven():
    res = normalize("montelukast sodium", "neuropsychiatric events", INV)
    assert res.normalized_drug_names == ["montelukast", "singulair"]
    assert res.consumed_evidence_hashes == []      # query-driven, consumes no evidence
    assert len(res.output_hash) == 64


# --- aggregation ----------------------------------------------------------- #
def test_aggregation_counts_year_reaction_seriousness():
    records = [
        rec("R1", serious=True, rdate=date(2020, 1, 1), reactions=["Depression"]),
        rec("R2", serious=False, rdate=date(2020, 6, 1), reactions=["Depression", "Anxiety"]),
        rec("R3", serious=None, rdate=date(2021, 2, 1), reactions=["Aggression"]),
    ]
    agg = aggregate_reports(records, INV)
    assert agg.total_reports == 3
    assert agg.by_year == {"2020": 2, "2021": 1}
    assert agg.by_reaction_term["Depression"] == 2
    assert agg.by_seriousness == {"non_serious": 1, "serious": 1, "unknown": 1}


# --- seriousness & missingness --------------------------------------------- #
def test_seriousness_summary_counts_and_criteria():
    records = [
        rec("R1", serious=True, death=True),
        rec("R2", serious=True),
        rec("R3", serious=False),
        rec("R4", serious=None),
    ]
    s = summarize_seriousness(records, INV)
    assert (s.total_reports, s.serious, s.non_serious, s.seriousness_unknown) == (4, 2, 1, 1)
    assert s.by_criterion["death"] == 1


def test_missingness_fractions():
    records = [
        rec("R1", age=34, sex="female", rdate=date(2020, 1, 1)),
        rec("R2"),  # age, sex, date all missing
    ]
    m = summarize_missingness(records, INV)
    assert m.total_reports == 2
    assert m.missing_counts["patient_age"] == 1
    assert m.missing_fraction["patient_age"] == 0.5
    assert m.missing_fraction["patient_sex"] == 0.5


# --- dedup ----------------------------------------------------------------- #
def test_confirmed_version_chain():
    # A two-version case (same CASEID/report_id, versions 1 and 2) is ONE case.
    records = [rec("R1", version=1), rec("R1", version=2)]  # same case, follow-up
    d = resolve_duplicates(records, INV)
    assert d.unique_report_count == 1                       # the FAERS trap: must be 1, not 2
    assert len(d.groups) == 1
    assert d.groups[0].certainty is DuplicateGroupCertainty.CONFIRMED
    assert "version chain" in d.groups[0].reason


def test_collapse_keeps_only_latest_version_per_case():
    records = [rec("R1", version=1, serious=False), rec("R1", version=2, serious=True),
               rec("R2", version=1, serious=False)]
    collapsed = collapse_to_latest_versions(records)
    assert len(collapsed) == 2                              # R1 collapsed to one
    r1 = next(r for r in collapsed if r.payload.report_id == "R1")
    assert r1.payload.report_version == 2                   # newest version kept
    assert r1.payload.serious is True


def test_count_analyses_on_collapsed_set_count_a_case_once():
    # Without collapsing, R1's two versions would inflate the serious count.
    records = [rec("R1", version=1, serious=True), rec("R1", version=2, serious=True)]
    collapsed = collapse_to_latest_versions(records)
    s = summarize_seriousness(collapsed, INV)
    assert s.total_reports == 1 and s.serious == 1          # one case, not two


def test_confirmed_exact_duplicate_same_id_and_version():
    # same id+version but a differing field -> different content hash, still same case
    records = [rec("R1", version=1, country="US"), rec("R1", version=1, country="GB")]
    d = resolve_duplicates(records, INV)
    assert d.groups[0].certainty is DuplicateGroupCertainty.CONFIRMED
    assert "exact duplicate" in d.groups[0].reason


def test_likely_duplicate_across_different_ids_not_merged():
    common = dict(sex="female", age=40.0, rdate=date(2020, 3, 1), reactions=["Depression"], country="US")
    records = [rec("R1", **common), rec("R2", **common)]  # different ids, same fingerprint
    d = resolve_duplicates(records, INV)
    likely = [g for g in d.groups if g.certainty is DuplicateGroupCertainty.LIKELY]
    assert len(likely) == 1
    assert d.unique_report_count == 2  # NOT merged: uncertain -> flagged only


def test_sparse_reports_are_not_flagged_as_likely_duplicates():
    records = [rec("R1"), rec("R2")]  # too little info to even suspect
    d = resolve_duplicates(records, INV)
    assert all(g.certainty is not DuplicateGroupCertainty.LIKELY for g in d.groups)


# --- temporal -------------------------------------------------------------- #
def _period():
    return ReviewPeriod(start=date(2019, 1, 1), end=date(2021, 12, 31))


def test_temporal_increase():
    records = [rec("R1", rdate=date(2019, 5, 1))] + \
              [rec(f"S{i}", rdate=date(2021, 5, i + 1)) for i in range(3)]
    t = compare_periods(records, _period(), INV)
    assert t.direction == "increase"
    assert {pc.label: pc.report_count for pc in t.period_counts} == {"2019": 1, "2020": 0, "2021": 3}
    assert "not incidence" in t.note.lower()


def test_temporal_insufficient_data_with_one_year():
    records = [rec("R1", rdate=date(2020, 5, 1))]
    t = compare_periods(records, _period(), INV)
    assert t.direction == "insufficient_data"


# --- dependency tracking (feeds selective recompute) ----------------------- #
def test_output_hash_stable_and_consumed_hashes_sorted():
    records = [rec("R2", serious=True), rec("R1", serious=False)]
    a = summarize_seriousness(records, INV)
    b = summarize_seriousness(records, INV)
    assert a.output_hash == b.output_hash                 # deterministic
    assert a.consumed_evidence_hashes == sorted(a.consumed_evidence_hashes)


def test_output_hash_changes_when_evidence_changes():
    base = [rec("R1", serious=True)]
    changed = [rec("R1", serious=False)]
    assert summarize_seriousness(base, INV).output_hash != \
           summarize_seriousness(changed, INV).output_hash
