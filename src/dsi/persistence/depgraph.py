"""The selective-recompute dependency graph.

Model: a DAG per run with three node types.
  * evidence      -- a logical evidence slot; holds the content hash of whatever
                     evidence currently fills that role. Correcting/adding a report
                     updates this hash (evidence itself stays immutable; a new
                     record simply becomes the current content of the slot).
  * analysis      -- a deterministic result; holds inputs_hash + output_hash.
  * memo_section  -- a memo section; holds inputs_hash + output_hash.

Recompute rule (the whole point --- NOT "recompute everything"):
  Process nodes in topological order. For each non-evidence node, recompute its
  inputs_hash from its *current* upstream hashes. If that equals the stored
  inputs_hash, its inputs did not change -> REUSE (never call the compute fn).
  Otherwise recompute; if the new output_hash equals the old one, SHORT-CIRCUIT
  (its downstream inputs are unchanged, so they reuse). Because outputs are
  updated in topo order, changes cascade exactly as far as they actually alter
  results and no further.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Literal, TYPE_CHECKING

from dsi.hashing import hash_of_hashes

if TYPE_CHECKING:
    from dsi.persistence.db import Database

NodeType = Literal["evidence", "analysis", "memo_section"]


@dataclass
class DepNode:
    node_id: str
    node_type: NodeType
    content_hash: str | None = None   # evidence nodes
    output_hash: str | None = None    # analysis / memo_section nodes
    inputs_hash: str | None = None
    stale: bool = False

    def current_hash(self) -> str:
        """The hash this node exposes to its downstream consumers."""
        h = self.content_hash if self.node_type == "evidence" else self.output_hash
        return h or ""


@dataclass
class RecomputeReport:
    """What happened during a recompute --- the reused-vs-recomputed breakdown."""

    recomputed: list[str] = field(default_factory=list)      # compute fn was called
    reused: list[str] = field(default_factory=list)          # inputs unchanged -> skipped
    short_circuited: list[str] = field(default_factory=list) # recomputed but output identical
    changed_outputs: list[str] = field(default_factory=list) # recompute produced a new output

    @property
    def recomputed_count(self) -> int:
        return len(self.recomputed)

    @property
    def reused_count(self) -> int:
        return len(self.reused)


class DependencyGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, DepNode] = {}
        self._out: dict[str, set[str]] = defaultdict(set)
        self._in: dict[str, set[str]] = defaultdict(set)

    # -- construction ------------------------------------------------------- #
    def add_node(self, node: DepNode) -> DepNode:
        self.nodes[node.node_id] = node
        return node

    def add_edge(self, upstream_id: str, downstream_id: str) -> None:
        if upstream_id not in self.nodes or downstream_id not in self.nodes:
            raise KeyError("both nodes must exist before adding an edge")
        self._out[upstream_id].add(downstream_id)
        self._in[downstream_id].add(upstream_id)

    def upstream_of(self, node_id: str) -> list[str]:
        return sorted(self._in.get(node_id, set()))

    def downstream_of(self, node_id: str) -> list[str]:
        return sorted(self._out.get(node_id, set()))

    # -- ordering ----------------------------------------------------------- #
    def topo_order(self) -> list[str]:
        """Kahn's algorithm. Raises on a cycle (the graph must be a DAG)."""
        indeg = {n: len(self._in.get(n, set())) for n in self.nodes}
        queue = deque(sorted(n for n, d in indeg.items() if d == 0))
        order: list[str] = []
        while queue:
            n = queue.popleft()
            order.append(n)
            for m in sorted(self._out.get(n, set())):
                indeg[m] -= 1
                if indeg[m] == 0:
                    queue.append(m)
        if len(order) != len(self.nodes):
            raise ValueError("dependency graph contains a cycle")
        return order

    def _current_inputs_hash(self, node_id: str) -> str:
        upstream_hashes = [self.nodes[u].current_hash() for u in self.upstream_of(node_id)]
        return hash_of_hashes(upstream_hashes)

    def initialize_input_hashes(self) -> None:
        """Set every non-evidence node's inputs_hash to match its current upstreams.

        Call this once after building the first-run graph (with outputs filled in),
        so that a later `recompute` detects change as a *difference* from this
        baseline. With no changes, recompute does zero work.
        """
        for node_id in self.topo_order():
            node = self.nodes[node_id]
            if node.node_type != "evidence":
                node.inputs_hash = self._current_inputs_hash(node_id)

    # -- the selective recompute -------------------------------------------- #
    def update_evidence_hash(self, node_id: str, new_content_hash: str) -> None:
        """Point an evidence slot at new content (Scenario A: corrected/added report)."""
        node = self.nodes[node_id]
        if node.node_type != "evidence":
            raise ValueError(f"{node_id} is not an evidence node")
        node.content_hash = new_content_hash

    def recompute(self, recompute_fn: Callable[[DepNode], str]) -> RecomputeReport:
        """Recompute only the nodes whose inputs actually changed.

        `recompute_fn(node)` must recompute the node and return its new output hash.
        It is called ONLY for nodes with changed inputs; unchanged nodes are reused.
        """
        report = RecomputeReport()
        for node_id in self.topo_order():
            node = self.nodes[node_id]
            if node.node_type == "evidence":
                continue  # raw inputs are never recomputed
            current = self._current_inputs_hash(node_id)
            if current == node.inputs_hash:
                report.reused.append(node_id)
                node.stale = False
                continue
            # inputs changed -> this node is genuinely affected
            node.stale = True
            new_output = recompute_fn(node)
            node.inputs_hash = current
            report.recomputed.append(node_id)
            if new_output == node.output_hash:
                report.short_circuited.append(node_id)  # downstream will reuse
            else:
                report.changed_outputs.append(node_id)
            node.output_hash = new_output
            node.stale = False
        return report


class DepGraphRepo:
    """Persist a run's graph. A new run is saved under a new run_id; prior runs are
    never modified --- that preservation IS the audit trail for Scenario A."""

    def __init__(self, db: "Database") -> None:
        self.db = db

    def save_graph(self, investigation_id: str, run_id: str, graph: DependencyGraph) -> None:
        with self.db.transaction() as c:
            for node in graph.nodes.values():
                c.execute(
                    "INSERT OR REPLACE INTO dep_nodes "
                    "(run_id, node_id, investigation_id, node_type, content_hash, "
                    " output_hash, inputs_hash, stale) VALUES (?,?,?,?,?,?,?,?)",
                    (run_id, node.node_id, investigation_id, node.node_type,
                     node.content_hash, node.output_hash, node.inputs_hash, int(node.stale)),
                )
            for up, downs in graph._out.items():
                for down in downs:
                    c.execute(
                        "INSERT OR REPLACE INTO dep_edges "
                        "(run_id, upstream_node_id, downstream_node_id) VALUES (?,?,?)",
                        (run_id, up, down),
                    )

    def load_graph(self, run_id: str) -> DependencyGraph:
        graph = DependencyGraph()
        nodes = self.db.conn.execute(
            "SELECT * FROM dep_nodes WHERE run_id = ?", (run_id,)
        ).fetchall()
        for r in nodes:
            graph.add_node(DepNode(
                node_id=r["node_id"], node_type=r["node_type"],
                content_hash=r["content_hash"], output_hash=r["output_hash"],
                inputs_hash=r["inputs_hash"], stale=bool(r["stale"]),
            ))
        edges = self.db.conn.execute(
            "SELECT upstream_node_id, downstream_node_id FROM dep_edges WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        for e in edges:
            graph.add_edge(e["upstream_node_id"], e["downstream_node_id"])
        return graph

    def run_ids_for(self, investigation_id: str) -> list[str]:
        rows = self.db.conn.execute(
            "SELECT DISTINCT run_id FROM dep_nodes WHERE investigation_id = ?",
            (investigation_id,),
        ).fetchall()
        return [r["run_id"] for r in rows]
