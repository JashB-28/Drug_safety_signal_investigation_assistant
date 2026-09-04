"""The local MCP server exposes exactly the three read-only tools and can invoke
them (with an injected fake client --- no network)."""

from __future__ import annotations

import json

import pytest

from dsi.mcp_server.server import ToolClients, build_server


@pytest.fixture
def server(http):
    clients = ToolClients(
        openfda=http.Client([http.ok(http.faers())]),
        pubmed=http.Client([http.ok(http.esearch()), http.ok(http.esummary())]),
    )
    return build_server(clients=clients)


async def test_server_exposes_three_readonly_tools(server):
    tools = await server.list_tools()
    assert sorted(t.name for t in tools) == ["faers_search", "label_fetch", "literature_search"]


async def test_call_faers_tool_returns_ok_payload(server):
    result = await server.call_tool("faers_search",
                                    {"request": {"drug": "montelukast", "event": "depression"}})
    payload = json.loads(result[0].text)
    assert payload["ok"] is True
    assert payload["tool_name"] == "faers_search"
    assert payload["data"]["returned"] == 2
