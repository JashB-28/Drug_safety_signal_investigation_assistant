"""The three tools against synthetic fixtures: correct parsing and graceful
handling of empty, malformed, and timeout responses."""

from __future__ import annotations

from datetime import date

from dsi.domain.evidence import DrugRole, LabelSectionName
from dsi.domain.tools import (
    FaersSearchRequest,
    LabelFetchRequest,
    LiteratureSearchRequest,
    ToolErrorCode,
)
from dsi.mcp_server.openfda import fetch_drug_label, search_adverse_events
from dsi.mcp_server.pubmed import search_literature


# --- FAERS ----------------------------------------------------------------- #
def test_faers_parses_seriousness_missingness_and_roles(http):
    client = http.Client([http.ok(http.faers())])
    req = FaersSearchRequest(drug="montelukast", event="depression",
                             date_start=date(2019, 1, 1), date_end=date(2021, 12, 31))
    res = search_adverse_events(req, client)
    assert res.ok and res.data.returned == 2
    r1, r2 = res.data.reports
    assert r1.serious is True and r1.serious_death is True
    assert r1.drugs[0].role is DrugRole.PRIMARY_SUSPECT
    assert r1.patient_sex == "female"
    assert r2.serious is False
    assert r2.patient_age is None  # missingness preserved as None
    # the query string is recorded for the audit trail
    assert 'medicinalproduct:"montelukast"' in res.query


def test_faers_empty_result_is_graceful(http):
    client = http.Client([http.empty404()])
    res = search_adverse_events(FaersSearchRequest(drug="nonexistent"), client)
    assert res.ok is True                 # empty is a valid, complete answer
    assert res.data.returned == 0
    assert res.error is None


def test_faers_malformed_response_is_error_not_crash(http):
    client = http.Client([http.malformed()])
    res = search_adverse_events(FaersSearchRequest(drug="montelukast"), client)
    assert res.ok is False
    assert res.error.code is ToolErrorCode.MALFORMED_RESPONSE


def test_faers_timeout_reports_error_and_retry_count(http):
    client = http.Client([http.timeout()])
    res = search_adverse_events(FaersSearchRequest(drug="montelukast"), client)
    assert res.ok is False
    assert res.error.code is ToolErrorCode.TIMEOUT
    assert res.retry_count == 2


# --- Label ----------------------------------------------------------------- #
def test_label_parses_boxed_warning_and_version(http):
    client = http.Client([http.ok(http.label())])
    req = LabelFetchRequest(drug="montelukast",
                            sections=[LabelSectionName.BOXED_WARNING,
                                      LabelSectionName.WARNINGS_AND_PRECAUTIONS])
    res = fetch_drug_label(req, client)
    assert res.ok
    boxed = [s for s in res.data.sections if s.section is LabelSectionName.BOXED_WARNING]
    assert boxed and "NEUROPSYCHIATRIC" in boxed[0].text.upper()
    assert boxed[0].effective_date == date(2020, 3, 4)   # the boxed-warning date
    assert boxed[0].spl_version == "7"


def test_label_empty_is_graceful(http):
    client = http.Client([http.empty404()])
    res = fetch_drug_label(LabelFetchRequest(drug="nope"), client)
    assert res.ok is True and res.data.sections == []


# --- Literature (two calls: esearch + esummary) ---------------------------- #
def test_literature_two_call_success(http):
    client = http.Client([http.ok(http.esearch()), http.ok(http.esummary())])
    res = search_literature(LiteratureSearchRequest(query="montelukast neuropsychiatric"), client)
    assert res.ok and res.data.total == 2
    titles = [r.title for r in res.data.references]
    assert any("No increased risk" in t for t in titles)
    assert any("suicidality" in t for t in titles)


def test_literature_empty_esearch_is_graceful(http):
    client = http.Client([http.ok(http.esearch(ids=[]))])
    res = search_literature(LiteratureSearchRequest(query="asdfqwer"), client)
    assert res.ok is True and res.data.total == 0
    assert len(client.calls) == 1  # esummary skipped when no ids


def test_literature_esummary_failure_reports_error(http):
    client = http.Client([http.ok(http.esearch()), http.timeout()])
    res = search_literature(LiteratureSearchRequest(query="montelukast"), client)
    assert res.ok is False
    assert res.error.code is ToolErrorCode.TIMEOUT
