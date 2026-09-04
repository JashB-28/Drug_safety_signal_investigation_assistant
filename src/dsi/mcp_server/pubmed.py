"""PubMed literature tool --- the third evidence source (Scenario B).

Two calls: `esearch` to get PMIDs, then `esummary` for citation metadata. Abstracts
are not fetched here (that needs `efetch` XML); `abstract` is left None and the
conflict scenario supplies an abstract from a snapshot/synthetic record. This keeps
the tool honest about what it retrieves. All text is captured as typed DATA.
"""

from __future__ import annotations

from datetime import date

from dsi.domain.evidence import LiteratureReference
from dsi.domain.tools import LiteratureSearchData, LiteratureSearchRequest, ToolResult
from dsi.mcp_server.http_client import HttpClient

ESEARCH_PATH = "/esearch.fcgi"
ESUMMARY_PATH = "/esummary.fcgi"


def build_esearch_params(request: LiteratureSearchRequest, api_key: str | None = None) -> dict:
    params: dict = {
        "db": "pubmed", "term": request.query, "retmode": "json",
        "retmax": request.max_results, "datetype": "pdat",
    }
    if request.date_start:
        params["mindate"] = request.date_start.strftime("%Y/%m/%d")
    if request.date_end:
        params["maxdate"] = request.date_end.strftime("%Y/%m/%d")
    if api_key:
        params["api_key"] = api_key
    return params


def parse_esearch(payload: dict) -> list[str]:
    return list(payload.get("esearchresult", {}).get("idlist", []) or [])


def _pubmed_date(value: str | None) -> date | None:
    """PubMed pubdate is loosely formatted, e.g. '2020 Mar 4' or '2020'. Parse the year."""
    if not value:
        return None
    year = value.strip().split(" ")[0]
    if year.isdigit() and len(year) == 4:
        return date(int(year), 1, 1)
    return None


def parse_esummary(payload: dict) -> LiteratureSearchData:
    result = payload.get("result", {}) or {}
    uids = result.get("uids", []) or []
    refs: list[LiteratureReference] = []
    for uid in uids:
        item = result.get(uid, {}) or {}
        authors = [a.get("name", "") for a in item.get("authors", []) or [] if a.get("name")]
        refs.append(LiteratureReference(
            pmid=str(uid),
            title=(item.get("title") or "").strip() or "(no title)",
            journal=item.get("fulljournalname") or item.get("source"),
            authors=authors,
            pub_date=_pubmed_date(item.get("pubdate")),
            doi=_extract_doi(item),
        ))
    return LiteratureSearchData(references=refs, total=len(refs))


def _extract_doi(item: dict) -> str | None:
    for aid in item.get("articleids", []) or []:
        if aid.get("idtype") == "doi":
            return aid.get("value")
    return None


def search_literature(
    request: LiteratureSearchRequest, client: HttpClient, api_key: str | None = None
) -> ToolResult[LiteratureSearchData]:
    # 1) esearch for PMIDs
    esearch = client.get_json(ESEARCH_PATH, build_esearch_params(request, api_key))
    if not esearch.ok or esearch.json is None:
        return ToolResult[LiteratureSearchData](
            tool_name="literature_search", ok=False, error=esearch.error,
            retry_count=esearch.retry_count, latency_ms=esearch.latency_ms, query=request.query,
        )
    pmids = parse_esearch(esearch.json)
    if not pmids:  # graceful empty
        return ToolResult[LiteratureSearchData](
            tool_name="literature_search", ok=True,
            data=LiteratureSearchData(references=[], total=0),
            retry_count=esearch.retry_count, latency_ms=esearch.latency_ms, query=request.query,
        )

    # 2) esummary for metadata
    summ_params: dict = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
    if api_key:
        summ_params["api_key"] = api_key
    esummary = client.get_json(ESUMMARY_PATH, summ_params)
    retries = esearch.retry_count + esummary.retry_count
    latency = esearch.latency_ms + esummary.latency_ms
    if not esummary.ok or esummary.json is None:
        return ToolResult[LiteratureSearchData](
            tool_name="literature_search", ok=False, error=esummary.error,
            retry_count=retries, latency_ms=latency, query=request.query,
        )
    data = parse_esummary(esummary.json)
    return ToolResult[LiteratureSearchData](
        tool_name="literature_search", ok=True, data=data,
        retry_count=retries, latency_ms=latency, query=request.query,
    )
