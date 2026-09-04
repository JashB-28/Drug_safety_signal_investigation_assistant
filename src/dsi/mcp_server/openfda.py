"""openFDA tools: adverse-event (FAERS) search and drug-label retrieval.

Parsing is separated from the tool wrapper so it can be unit-tested against
synthetic fixtures with no network. openFDA returns HTTP 404 when a query matches
nothing, so both tools translate a 404 into a *graceful empty result* (a valid,
complete answer: "no matching records"), not an error.

All retrieved free text (label section bodies, reported product/reaction names)
is captured verbatim into typed fields --- it is DATA, never instructions.
"""

from __future__ import annotations

from datetime import date

from dsi.domain.evidence import (
    AdverseEventReport,
    DrugEntry,
    DrugRole,
    LabelSection,
    LabelSectionName,
    ReactionEntry,
)
from dsi.domain.tools import (
    FaersSearchData,
    FaersSearchRequest,
    LabelFetchData,
    LabelFetchRequest,
    ToolResult,
)
from dsi.mcp_server.http_client import HttpClient

FAERS_PATH = "/drug/event.json"
LABEL_PATH = "/drug/label.json"

_DRUG_ROLE = {"1": DrugRole.PRIMARY_SUSPECT, "2": DrugRole.CONCOMITANT, "3": DrugRole.INTERACTING}
_SEX = {"1": "male", "2": "female"}

# openFDA label field key(s) for each of our section enums.
_LABEL_FIELDS: dict[LabelSectionName, list[str]] = {
    LabelSectionName.BOXED_WARNING: ["boxed_warning"],
    LabelSectionName.WARNINGS_AND_PRECAUTIONS: ["warnings_and_precautions", "warnings"],
    LabelSectionName.ADVERSE_REACTIONS: ["adverse_reactions"],
    LabelSectionName.INDICATIONS_AND_USAGE: ["indications_and_usage"],
    LabelSectionName.CONTRAINDICATIONS: ["contraindications"],
}


# --------------------------------------------------------------------------- #
# Small parsing helpers
# --------------------------------------------------------------------------- #
def _fda_date(value: str | None) -> date | None:
    if not value or len(value) != 8 or not value.isdigit():
        return None
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError:
        return None


def _yn(value) -> bool | None:
    """openFDA '1' = yes, '2' = no; anything else = not reported (None)."""
    if value in ("1", 1):
        return True
    if value in ("2", 2):
        return False
    return None


def _present(value) -> bool | None:
    """A seriousness-criterion flag: '1' present -> True, absent -> None."""
    return True if value in ("1", 1) else None


# --------------------------------------------------------------------------- #
# FAERS
# --------------------------------------------------------------------------- #
def build_faers_query(request: FaersSearchRequest) -> str:
    """Build the openFDA `search` expression (spaces = AND)."""
    parts = [f'patient.drug.medicinalproduct:"{request.drug}"']
    if request.event:
        parts.append(f'patient.reaction.reactionmeddrapt:"{request.event}"')
    if request.date_start and request.date_end:
        s = request.date_start.strftime("%Y%m%d")
        e = request.date_end.strftime("%Y%m%d")
        parts.append(f"receivedate:[{s} TO {e}]")
    return " AND ".join(parts)


def parse_faers_response(payload: dict) -> FaersSearchData:
    total = int(payload.get("meta", {}).get("results", {}).get("total", 0) or 0)
    reports = [_parse_one_report(r) for r in payload.get("results", [])]
    return FaersSearchData(reports=reports, total_matched=total, returned=len(reports))


def _parse_one_report(r: dict) -> AdverseEventReport:
    patient = r.get("patient", {}) or {}
    drugs = [
        DrugEntry(
            name=(d.get("medicinalproduct") or "").strip() or "UNKNOWN",
            role=_DRUG_ROLE.get(str(d.get("drugcharacterization")), DrugRole.UNKNOWN),
            indication=d.get("drugindication"),
        )
        for d in patient.get("drug", []) or []
    ]
    reactions = [
        ReactionEntry(term=(x.get("reactionmeddrapt") or "").strip() or "UNKNOWN",
                      outcome=str(x.get("reactionoutcome")) if x.get("reactionoutcome") else None)
        for x in patient.get("reaction", []) or []
    ]
    age = patient.get("patientonsetage")
    # IDENTIFIER MAPPING (load-bearing for dedup): openFDA `safetyreportid` is the
    # CASE-level id (FAERS CASEID / case report number), stable across follow-up
    # versions; `safetyreportversion` is the version. So `report_id` is caseid-level
    # and multiple versions of one case share it (a confirmed version chain).
    return AdverseEventReport(
        report_id=str(r.get("safetyreportid", "")),
        report_version=int(r["safetyreportversion"]) if str(r.get("safetyreportversion", "")).isdigit() else None,
        receive_date=_fda_date(r.get("receivedate")),
        receipt_date=_fda_date(r.get("receiptdate")),
        serious=_yn(r.get("serious")),
        serious_death=_present(r.get("seriousnessdeath")),
        serious_hospitalization=_present(r.get("seriousnesshospitalization")),
        serious_life_threatening=_present(r.get("seriousnesslifethreatening")),
        serious_disabling=_present(r.get("seriousnessdisabling")),
        serious_congenital_anomaly=_present(r.get("seriousnesscongenitalanomali")),
        serious_other=_present(r.get("seriousnessother")),
        patient_age=float(age) if age not in (None, "") else None,
        patient_age_unit=patient.get("patientonsetageunit"),
        patient_sex=_SEX.get(str(patient.get("patientsex"))),
        reporter_qualification=(r.get("primarysource", {}) or {}).get("qualification"),
        occur_country=r.get("occurcountry"),
        drugs=drugs,
        reactions=reactions,
    )


def search_adverse_events(
    request: FaersSearchRequest, client: HttpClient, api_key: str | None = None
) -> ToolResult[FaersSearchData]:
    query = build_faers_query(request)
    params: dict = {"search": query, "limit": request.limit, "skip": request.skip}
    if api_key:
        params["api_key"] = api_key
    outcome = client.get_json(FAERS_PATH, params)

    if outcome.ok and outcome.json is not None:
        data = parse_faers_response(outcome.json)
        return ToolResult[FaersSearchData](
            tool_name="faers_search", ok=True, data=data,
            retry_count=outcome.retry_count, latency_ms=outcome.latency_ms, query=query,
        )
    # openFDA 404 == no matches -> graceful empty (a valid, complete answer).
    if outcome.status_code == 404:
        return ToolResult[FaersSearchData](
            tool_name="faers_search", ok=True,
            data=FaersSearchData(reports=[], total_matched=0, returned=0),
            retry_count=outcome.retry_count, latency_ms=outcome.latency_ms, query=query,
        )
    return ToolResult[FaersSearchData](
        tool_name="faers_search", ok=False, error=outcome.error,
        retry_count=outcome.retry_count, latency_ms=outcome.latency_ms, query=query,
    )


# --------------------------------------------------------------------------- #
# Drug label
# --------------------------------------------------------------------------- #
def build_label_query(request: LabelFetchRequest) -> str:
    return (f'openfda.generic_name:"{request.drug}" '
            f'OR openfda.brand_name:"{request.drug}"')


def parse_label_response(payload: dict, drug_name: str,
                         sections: list[LabelSectionName] | None) -> LabelFetchData:
    results = payload.get("results", []) or []
    if not results:
        return LabelFetchData(drug_name=drug_name, sections=[])
    item = results[0]
    openfda = item.get("openfda", {}) or {}
    spl_set_id = (openfda.get("spl_set_id") or [None])[0]
    spl_version = item.get("version") or (openfda.get("spl_version") or [None])[0]
    effective = _fda_date(item.get("effective_time"))

    wanted = sections or list(_LABEL_FIELDS.keys())
    out: list[LabelSection] = []
    for sec in wanted:
        text = _extract_section_text(item, sec)
        if text:
            out.append(LabelSection(
                drug_name=drug_name, section=sec, text=text,
                spl_set_id=spl_set_id, spl_version=str(spl_version) if spl_version else None,
                effective_date=effective,
            ))
    return LabelFetchData(drug_name=drug_name, sections=out, spl_set_id=spl_set_id,
                          spl_version=str(spl_version) if spl_version else None)


def _extract_section_text(item: dict, section: LabelSectionName) -> str | None:
    for key in _LABEL_FIELDS[section]:
        value = item.get(key)
        if isinstance(value, list) and value:
            return "\n".join(str(v) for v in value).strip()
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def fetch_drug_label(
    request: LabelFetchRequest, client: HttpClient, api_key: str | None = None
) -> ToolResult[LabelFetchData]:
    query = build_label_query(request)
    params: dict = {"search": query, "limit": 1}
    if api_key:
        params["api_key"] = api_key
    outcome = client.get_json(LABEL_PATH, params)

    if outcome.ok and outcome.json is not None:
        data = parse_label_response(outcome.json, request.drug, request.sections)
        return ToolResult[LabelFetchData](
            tool_name="label_fetch", ok=True, data=data,
            retry_count=outcome.retry_count, latency_ms=outcome.latency_ms, query=query,
        )
    if outcome.status_code == 404:
        return ToolResult[LabelFetchData](
            tool_name="label_fetch", ok=True,
            data=LabelFetchData(drug_name=request.drug, sections=[]),
            retry_count=outcome.retry_count, latency_ms=outcome.latency_ms, query=query,
        )
    return ToolResult[LabelFetchData](
        tool_name="label_fetch", ok=False, error=outcome.error,
        retry_count=outcome.retry_count, latency_ms=outcome.latency_ms, query=query,
    )