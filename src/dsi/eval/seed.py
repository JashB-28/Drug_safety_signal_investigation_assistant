"""Seed the snapshot cache from the pinned eval dataset so the evaluation runs fully
offline. After seeding, the agent's tool requests are cache hits; a real HTTP client
is never called. `OfflineGuardClient` enforces this: any actual network attempt
raises, so a cache miss fails loudly instead of silently going live.
"""

from __future__ import annotations

from dsi.domain.investigation import Investigation
from dsi.domain.tools import (
    FaersSearchData,
    FaersSearchRequest,
    LabelFetchData,
    LabelFetchRequest,
    LiteratureSearchData,
    LiteratureSearchRequest,
    ToolResult,
)
from dsi.eval import fixtures
from dsi.mcp_server.http_client import HttpOutcome
from dsi.mcp_server.openfda import (
    build_faers_query,
    build_label_query,
    parse_faers_response,
    parse_label_response,
)
from dsi.mcp_server.pubmed import parse_esummary
from dsi.persistence.cache import SnapshotCache
from dsi.persistence.db import Database


class OfflineGuardClient:
    """An HTTP client that must never be called during the eval (proves offline)."""

    def get_json(self, path: str, params: dict) -> HttpOutcome:  # pragma: no cover - guard
        raise RuntimeError(f"network access attempted during offline eval: {path}")


def seed_cache(db: Database, investigation: Investigation = fixtures.EVAL_INVESTIGATION) -> None:
    """Populate the snapshot cache with the exact tool responses the agent will request."""
    cache = SnapshotCache(db)

    faers_req = FaersSearchRequest(
        drug=investigation.drug, event=investigation.event,
        date_start=investigation.review_period.start, date_end=investigation.review_period.end)
    faers_res = ToolResult[FaersSearchData](
        tool_name="faers_search", ok=True,
        data=parse_faers_response(fixtures.faers_payload()),
        query=build_faers_query(faers_req))
    cache.put(_key("faers_search", faers_req), "faers_search", faers_req, faers_res,
              source_version=fixtures.SNAPSHOT_LABEL)

    label_req = LabelFetchRequest(drug=investigation.drug)
    label_res = ToolResult[LabelFetchData](
        tool_name="label_fetch", ok=True,
        data=parse_label_response(fixtures.label_payload(), investigation.drug, None),
        query=build_label_query(label_req))
    cache.put(_key("label_fetch", label_req), "label_fetch", label_req, label_res,
              source_version=fixtures.SNAPSHOT_LABEL)

    lit_req = LiteratureSearchRequest(query=f"{investigation.drug} {investigation.event}")
    lit_res = ToolResult[LiteratureSearchData](
        tool_name="literature_search", ok=True,
        data=parse_esummary(fixtures.esummary_payload()), query=lit_req.query)
    cache.put(_key("literature_search", lit_req), "literature_search", lit_req, lit_res,
              source_version=fixtures.SNAPSHOT_LABEL)


def _key(tool_name: str, request) -> str:
    from dsi.persistence.cache import make_cache_key
    return make_cache_key(tool_name, request)
