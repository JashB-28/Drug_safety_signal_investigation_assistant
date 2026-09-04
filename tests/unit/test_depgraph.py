"""The selective-recompute engine: only-downstream recompute, output-hash
short-circuit, and prior-run preservation."""

from __future__ import annotations

import pytest

from dsi.hashing import canonical_hash
from dsi.persistence.depgraph import DependencyGraph, DepGraphRepo, DepNode


def _build_graph() -> DependencyGraph:
    """A small but realistic graph:

        E1(faers) -> A_ser -> M_sm
        E1(faers) -> A_ser -> M_exec
        E2(label) -> A_label -> M_label
        E2(label) -> A_label -> M_exec
    """
    g = DependencyGraph()
    g.add_node(DepNode("E1", "evidence", content_hash="e1a"))
    g.add_node(DepNode("E2", "evidence", content_hash="e2a"))
    g.add_node(DepNode("A_ser", "analysis"))
    g.add_node(DepNode("A_label", "analysis"))
    g.add_node(DepNode("M_sm", "memo_section"))
    g.add_node(DepNode("M_label", "memo_section"))
    g.add_node(DepNode("M_exec", "memo_section"))
    g.add_edge("E1", "A_ser")
    g.add_edge("E2", "A_label")
    g.add_edge("A_ser", "M_sm")
    g.add_edge("A_label", "M_label")
    g.add_edge("A_ser", "M_exec")
    g.add_edge("A_label", "M_exec")
    return g


def _cascade_compute(g: DependencyGraph):
    """Output = deterministic function of node id + upstream hashes. So a node's
    output changes exactly when its inputs change (full cascade)."""
    def compute(node: DepNode) -> str:
        ups = sorted(g.nodes[u].current_hash() for u in g.upstream_of(node.node_id))
        return canonical_hash({"node": node.node_id, "inputs": ups})
    return compute


def test_topo_order_and_cycle_detection():
    g = _build_graph()
    order = g.topo_order()
    # every upstream precedes its downstream
    assert order.index("E1") < order.index("A_ser") < order.index("M_sm")
    assert order.index("A_label") < order.index("M_exec")
    # introduce a cycle
    g.add_edge("M_exec", "A_ser")
    with pytest.raises(ValueError):
        g.topo_order()


def test_first_run_computes_everything():
    g = _build_graph()
    report = g.recompute(_cascade_compute(g))
    non_evidence = {"A_ser", "A_label", "M_sm", "M_label", "M_exec"}
    assert set(report.recomputed) == non_evidence
    assert report.reused == []


def test_unchanged_second_run_reuses_everything():
    g = _build_graph()
    compute = _cascade_compute(g)
    g.recompute(compute)               # first run
    report = g.recompute(compute)      # nothing changed
    assert report.recomputed == []
    assert len(report.reused) == 5


def test_evidence_change_recomputes_only_downstream():
    g = _build_graph()
    compute = _cascade_compute(g)
    g.recompute(compute)               # establish baseline

    g.update_evidence_hash("E1", "e1b")  # a corrected FAERS report arrives
    report = g.recompute(compute)

    # Affected by E1: A_ser, M_sm, M_exec. Untouched: A_label, M_label.
    assert set(report.recomputed) == {"A_ser", "M_sm", "M_exec"}
    assert set(report.reused) == {"A_label", "M_label"}
    assert set(report.changed_outputs) == {"A_ser", "M_sm", "M_exec"}


def test_output_hash_short_circuit_stops_propagation():
    g = _build_graph()

    def compute(node: DepNode) -> str:
        if node.node_id == "A_ser":
            return "SER_CONST"  # this analysis ignores its inputs -> stable output
        ups = sorted(g.nodes[u].current_hash() for u in g.upstream_of(node.node_id))
        return canonical_hash({"node": node.node_id, "inputs": ups})

    g.recompute(compute)                 # baseline
    g.update_evidence_hash("E1", "e1b")  # change A_ser's input
    report = g.recompute(compute)

    # A_ser is recomputed but its output is unchanged -> short-circuit.
    assert report.recomputed == ["A_ser"]
    assert report.short_circuited == ["A_ser"]
    # Because A_ser's output did not change, its downstream sections are REUSED.
    assert set(report.reused) == {"A_label", "M_sm", "M_label", "M_exec"}


def test_prior_run_preserved_in_storage(db):
    repo = DepGraphRepo(db)
    g1 = _build_graph()
    g1.recompute(_cascade_compute(g1))
    repo.save_graph("inv_1", "run_1", g1)

    g2 = _build_graph()
    g2.update_evidence_hash("E1", "e1b")
    g2.recompute(_cascade_compute(g2))
    repo.save_graph("inv_1", "run_2", g2)

    assert set(repo.run_ids_for("inv_1")) == {"run_1", "run_2"}
    # run_1's E1 hash is untouched; run_2's is the corrected one.
    loaded1 = repo.load_graph("run_1")
    loaded2 = repo.load_graph("run_2")
    assert loaded1.nodes["E1"].content_hash == "e1a"
    assert loaded2.nodes["E1"].content_hash == "e1b"
