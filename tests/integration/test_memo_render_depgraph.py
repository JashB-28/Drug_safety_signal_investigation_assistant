"""Phase 7: the rendered memo is analyst-readable + safe, section dependency
fingerprints are populated, and memo-section nodes are wired into the dep graph."""

from __future__ import annotations

from dsi.agent.graph import RunContext, run_investigation
from dsi.agent.llm import ScriptedLLM
from dsi.domain.memo import MemoSectionKind
from dsi.mcp_server.server import ToolClients
from dsi.memo import render_memo, scan_text


def _clients(http):
    return ToolClients(
        openfda=http.Routed({"/drug/event": [http.ok(http.faers())],
                             "/drug/label": [http.ok(http.label())]}),
        pubmed=http.Routed({"/esearch": [http.ok(http.esearch())],
                            "/esummary": [http.ok(http.esummary())]}),
    )


def _run(db, investigation, http):
    ctx = RunContext(db=db, llm=ScriptedLLM(), tool_clients=_clients(http))
    result = run_investigation(ctx, investigation)
    memo = ctx.memos.get_for_run(investigation.investigation_id, result.state.run_id)
    return ctx, result, memo


def test_rendered_memo_is_readable_and_safe(db, investigation, http):
    _, _, memo = _run(db, investigation, http)
    text = render_memo(memo)
    # all required section titles present
    for section in memo.sections:
        assert f"## {section.title}" in text
    assert "Advisory only" in text
    assert "[ref:" in text                       # citations shown inline
    # the rendered document contains no prohibited claim patterns
    assert scan_text(text) == []


def test_section_consumed_hashes_are_populated(db, investigation, http):
    _, _, memo = _run(db, investigation, http)
    sm = next(s for s in memo.sections if s.kind is MemoSectionKind.SERIOUSNESS_MISSINGNESS)
    assert sm.consumed_output_hashes, "seriousness/missingness section should record its inputs"


def test_memo_section_nodes_wired_into_dependency_graph(db, investigation, http):
    ctx, result, memo = _run(db, investigation, http)
    graph = ctx.depgraphs.load_graph(result.state.run_id)
    memo_nodes = [n for n in graph.nodes.values() if n.node_type == "memo_section"]
    assert memo_nodes, "memo-section nodes should be persisted"
    # the executive summary consumes analyses -> it has upstream edges
    exec_node = "memo:executive_summary"
    assert exec_node in graph.nodes
    assert graph.upstream_of(exec_node), "executive summary should depend on upstream nodes"
    # and those upstreams include at least one analysis node
    ups = graph.upstream_of(exec_node)
    assert any(u.startswith("analysis:") for u in ups)
