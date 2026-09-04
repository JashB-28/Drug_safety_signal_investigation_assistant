"""The local MCP server. Exposes three READ-ONLY tools over FastMCP:

  * faers_search      -- openFDA adverse-event search
  * label_fetch       -- openFDA drug-label retrieval
  * literature_search -- PubMed citation search

Tools return JSON (a serialized `ToolResult`) so the MCP schema stays simple and
transport-friendly. The HTTP clients are built from settings and can be injected
(`build_server(clients=...)`) so tests never touch the network. No secrets are in
source; an optional openFDA key is read from the environment only.
"""

from __future__ import annotations

from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from dsi.config import Settings, get_settings
from dsi.domain.tools import FaersSearchRequest, LabelFetchRequest, LiteratureSearchRequest
from dsi.mcp_server.http_client import BoundedHttpClient, HttpClient
from dsi.mcp_server.openfda import fetch_drug_label, search_adverse_events
from dsi.mcp_server.pubmed import search_literature


@dataclass
class ToolClients:
    """The HTTP clients each tool uses. Injectable for tests."""

    openfda: HttpClient
    pubmed: HttpClient
    openfda_api_key: str | None = None
    pubmed_api_key: str | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> "ToolClients":
        return cls(
            openfda=BoundedHttpClient(base_url=settings.openfda_base_url),
            pubmed=BoundedHttpClient(base_url=settings.pubmed_base_url),
            openfda_api_key=settings.openfda_api_key,
        )


def build_server(clients: ToolClients | None = None, settings: Settings | None = None) -> FastMCP:
    settings = settings or get_settings()
    clients = clients or ToolClients.from_settings(settings)
    mcp = FastMCP("dsi-evidence-tools")

    @mcp.tool()
    def faers_search(request: FaersSearchRequest) -> dict:
        """Search openFDA adverse-event (FAERS) reports for a drug/event/date range."""
        result = search_adverse_events(request, clients.openfda, clients.openfda_api_key)
        return result.model_dump(mode="json")

    @mcp.tool()
    def label_fetch(request: LabelFetchRequest) -> dict:
        """Retrieve sections of the current public drug label from openFDA."""
        result = fetch_drug_label(request, clients.openfda, clients.openfda_api_key)
        return result.model_dump(mode="json")

    @mcp.tool()
    def literature_search(request: LiteratureSearchRequest) -> dict:
        """Search PubMed for external evidence (citation metadata)."""
        result = search_literature(request, clients.pubmed, clients.pubmed_api_key)
        return result.model_dump(mode="json")

    return mcp


def main() -> None:
    """Run the server over stdio (for use as a local MCP server)."""
    build_server().run()


if __name__ == "__main__":
    main()
