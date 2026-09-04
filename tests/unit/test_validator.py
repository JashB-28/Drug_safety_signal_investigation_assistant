"""The deterministic safety validator: prohibited patterns, negation-awareness, and
citation completeness."""

from __future__ import annotations

from dsi.domain.memo import Citation, CitationKind, Claim, Memo, MemoSection, MemoSectionKind
from dsi.memo.validator import scan_text, validate_memo


def test_causal_assertion_flagged_but_negation_allowed():
    assert any(v["code"] == "causal_claim" for v in scan_text("The drug caused the event."))
    # the memo is EXPECTED to say this and it must pass:
    assert scan_text("The data cannot establish that the drug caused the event.") == []
    assert scan_text("A causal relationship has not been established.") == []


def test_rate_and_incidence_always_flagged():
    assert any(v["code"] == "incidence_language" for v in scan_text("The incidence was high."))
    assert any(v["code"] == "prevalence_language" for v in scan_text("Prevalence in the population."))
    assert any(v["code"] == "rate_language" for v in scan_text("The occurrence rate rose."))
    assert any(v["code"] == "rate_percent" for v in scan_text("3.2% of patients were affected."))


def test_negated_incidence_rate_disclaimer_passes():
    # the memo's own disclaimers use these words in negated form and must pass
    assert scan_text("These are counts of spontaneous reports, not incidence or rates.") == []
    assert scan_text("Spontaneous reports cannot be used to compute incidence or occurrence "
                     "rates.") == []


def test_treatment_recommendation_flagged():
    assert any(v["code"] == "treatment_recommendation"
               for v in scan_text("Patients should discontinue the drug."))
    assert any(v["code"] == "treatment_recommendation"
               for v in scan_text("We recommend switching therapy."))


def test_false_certainty_flagged_but_negation_allowed():
    assert any(v["code"] == "false_certainty" for v in scan_text("This proves the association."))
    assert scan_text("This cannot be proven from spontaneous reports.") == []


def test_validate_memo_flags_uncited_material_claim():
    memo = Memo(investigation_id="i", run_id="r", model_tag="m", sections=[
        MemoSection(kind=MemoSectionKind.EXECUTIVE_SUMMARY, title="Sum", claims=[
            Claim(text="12 reports were serious.", material=True)])])  # no citation
    report = validate_memo(memo)
    assert report.ok is False
    assert "12 reports were serious." in report.uncited_claims


def test_quoted_source_claim_is_exempt_from_prohibited_scan():
    # a real paper title contains 'drug-induced'/'prevalence'; quoting it (cited) is
    # not the SYSTEM asserting causation, so it must not fail the run.
    memo = Memo(investigation_id="i", run_id="r", model_tag="m", sections=[
        MemoSection(kind=MemoSectionKind.EXTERNAL_EVIDENCE, title="External", claims=[
            Claim(text='PMID 1: "Drug-induced psychiatric disorders: prevalence update".',
                  material=True, quoted=True,
                  citations=[Citation(kind=CitationKind.EVIDENCE, ref_id="evd_1")])])])
    assert validate_memo(memo).ok is True
    # but the same words in a NON-quoted (system-authored) claim still fail
    memo.sections[0].claims[0].quoted = False
    assert validate_memo(memo).ok is False


def test_validate_memo_clean_passes():
    memo = Memo(investigation_id="i", run_id="r", model_tag="m", sections=[
        MemoSection(kind=MemoSectionKind.LIMITATIONS, title="Lim", claims=[
            Claim(text="Spontaneous reports cannot establish that the drug caused the event.",
                  material=False)])])
    report = validate_memo(memo)
    assert report.ok is True
    assert report.violations == [] and report.uncited_claims == []
