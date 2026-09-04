"""Local MCP server exposing three read-only evidence-retrieval tools.

The tools are pure retrieval: bounded timeouts, bounded retries with backoff, and
structured errors --- no caching and no tracing here (those are owned by the agent
so they can be measured uniformly). Retrieved text is captured verbatim as typed
DATA; it is never interpreted as instructions.
"""

from dsi.mcp_server.http_client import BoundedHttpClient, HttpClient, HttpOutcome
from dsi.mcp_server.openfda import fetch_drug_label, search_adverse_events
from dsi.mcp_server.pubmed import search_literature
from dsi.mcp_server.server import ToolClients, build_server

__all__ = [
    "BoundedHttpClient", "HttpClient", "HttpOutcome",
    "search_adverse_events", "fetch_drug_label", "search_literature",
    "build_server", "ToolClients",
]
