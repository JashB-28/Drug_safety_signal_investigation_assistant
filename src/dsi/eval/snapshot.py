"""Real public-data snapshot for the evaluation (assessment §5).

`capture_snapshot()` runs the three tools LIVE (the only network use), for the real
eval pair (montelukast / depression / 2019-2021), and writes the responses to a
committed JSON file with provenance: the exact query, retrieval date, source, and a
content hash per record. `load_into_cache()` replays that snapshot into a DB's cache
so `dsi eval` runs on real, cached public data --- fully offline and reproducible.

The synthetic `fixtures.py` remains for fast unit tests; only the eval uses this
real snapshot.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from dsi.common import utcnow
from dsi.config import REPO_ROOT, get_settings
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
from dsi.eval.fixtures import REAL_EVAL_INVESTIGATION
from dsi.hashing import canonical_hash
from dsi.mcp_server.openfda import fetch_drug_label, search_adverse_events
from dsi.mcp_server.pubmed import search_literature
from dsi.mcp_server.server import ToolClients
from dsi.persistence.cache import SnapshotCache, make_cache_key
from dsi.persistence.db import Database

SNAPSHOT_PATH = REPO_ROOT / "data" / "cache" / "eval_snapshot.json"

# tool_name -> (request type, response type). Response is the whole ToolResult.
_TYPES = {
    "faers_search": (FaersSearchRequest, ToolResult[FaersSearchData]),
    "label_fetch": (LabelFetchRequest, ToolResult[LabelFetchData]),
    "literature_search": (LiteratureSearchRequest, ToolResult[LiteratureSearchData]),
}


def _requests(inv: Investigation):
    """The exact requests the agent will make --- must match graph.py construction."""
    return [
        ("faers_search", FaersSearchRequest(
            drug=inv.drug, event=inv.event,
            date_start=inv.review_period.start, date_end=inv.review_period.end)),
        ("label_fetch", LabelFetchRequest(drug=inv.drug)),
        ("literature_search", LiteratureSearchRequest(query=f"{inv.drug} {inv.event}")),
    ]


def capture_snapshot(inv: Investigation = REAL_EVAL_INVESTIGATION,
                     path: Path = SNAPSHOT_PATH) -> Path:
    """LIVE-fetch the three tools once and write the snapshot + provenance to disk."""
    settings = get_settings()
    clients = ToolClients.from_settings(settings)
    fns = {
        "faers_search": lambda r: search_adverse_events(r, clients.openfda, clients.openfda_api_key),
        "label_fetch": lambda r: fetch_drug_label(r, clients.openfda, clients.openfda_api_key),
        "literature_search": lambda r: search_literature(r, clients.pubmed, clients.pubmed_api_key),
    }
    now = utcnow().isoformat()
    entries = []
    for tool_name, request in _requests(inv):
        result = fns[tool_name](request)
        if not result.ok:
            raise RuntimeError(f"live fetch for {tool_name} failed: {result.error}")
        entries.append({
            "tool_name": tool_name,
            "query": result.query,
            "retrieved_at": now,
            "source": {"faers_search": "openFDA/drug/event", "label_fetch": "openFDA/drug/label",
                       "literature_search": "PubMed"}[tool_name],
            "content_hash": canonical_hash(result.data.model_dump(mode="json")),
            "request": request.model_dump(mode="json"),
            "response": result.model_dump(mode="json"),
        })
    manifest = {
        "snapshot": "real-openfda-pubmed",
        "captured_at": now,
        "investigation": {"drug": inv.drug, "event": inv.event,
                          "review_start": str(inv.review_period.start),
                          "review_end": str(inv.review_period.end)},
        "entries": entries,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def snapshot_exists(path: Path = SNAPSHOT_PATH) -> bool:
    return path.exists()


def _load_manifest(path: Path = SNAPSHOT_PATH) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"No eval snapshot at {path}. Run `dsi snapshot` once (needs network) to create it.")
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot_captured_at(path: Path = SNAPSHOT_PATH) -> str:
    return _load_manifest(path).get("captured_at", "unknown")


def load_into_cache(db: Database, inv: Investigation = REAL_EVAL_INVESTIGATION,
                    path: Path = SNAPSHOT_PATH) -> None:
    """Replay the committed snapshot into the DB's cache so the eval runs offline."""
    manifest = _load_manifest(path)
    cache = SnapshotCache(db)
    for e in manifest["entries"]:
        req_type, resp_type = _TYPES[e["tool_name"]]
        request = req_type.model_validate(e["request"])
        response = resp_type.model_validate(e["response"])
        cache.put(make_cache_key(e["tool_name"], request), e["tool_name"], request, response,
                  source_version="real-snapshot", retrieved_at=e["retrieved_at"])


def first_report_target(path: Path = SNAPSHOT_PATH) -> tuple[str, int, list[str], date | None]:
    """A real (report_id, next_version, reactions, receive_date) from the snapshot, so the
    evidence-update scenario corrects an ACTUAL case rather than a synthetic one."""
    manifest = _load_manifest(path)
    faers = next(e for e in manifest["entries"] if e["tool_name"] == "faers_search")
    reports = faers["response"]["data"]["reports"]
    if not reports:
        raise RuntimeError("snapshot FAERS data has no reports to correct")
    r = reports[0]
    version = (r.get("report_version") or 1) + 1
    reactions = [x["term"] for x in r.get("reactions", [])] or ["Depression"]
    rdate = date.fromisoformat(r["receive_date"]) if r.get("receive_date") else None
    return r["report_id"], version, reactions, rdate
