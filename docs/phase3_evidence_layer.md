# Phase 3 — Evidence layer (how it works, where to change it)

## What this layer is
Everything that persists, caches, hashes, and tracks dependencies — the storage
spine the agent (Phase 6) will sit on top of. No LLM here; no analysis math yet
(that is Phase 5). It also builds the **metrics/trace spine** early, so every tool
and model call in later phases records through one path.

## The five moving parts

### 1. SQLite storage (`persistence/db.py`, `schema.sql`, `repositories.py`)
One connection, foreign keys on, WAL journal (survives a crash — relevant to
resume). Repositories translate rows ↔ domain models. **Evidence is immutable at
the database layer**: triggers `evidence_no_update` / `evidence_no_delete` raise
`ABORT` on any UPDATE/DELETE, so no code path — LLM or otherwise — can silently
rewrite persisted evidence. A corrected report is a *new* row, never an edit.

### 2. Snapshot cache (`persistence/cache.py`)
`get_or_fetch(tool, request, fetch_fn, type)` returns `(response, cache_hit)` and
calls `fetch_fn` **only on a miss**. The key is `hash(tool + canonical request)`,
so a different query is automatically a different key — query-change invalidation
is free. This is what makes the eval run fully offline and makes resume cheap.

### 3. Dependency graph (`persistence/depgraph.py`) — the important one
A per-run DAG: `evidence → analysis → memo_section`. `recompute(fn)` walks nodes
in topological order and:
- reuses a node whose `inputs_hash` is unchanged (never calls `fn`),
- recomputes a node whose inputs changed, and
- **short-circuits**: if a recomputed node's `output_hash` is unchanged, its
  downstream sees unchanged inputs and is reused.

So changing one FAERS report recomputes only that report's analysis + the memo
sections that actually cite it — proven in `test_evidence_change_recomputes_only_downstream`
and `test_output_hash_short_circuit_stops_propagation`. `DepGraphRepo` saves each
run under a new `run_id` and never touches prior runs → the Scenario-A audit trail.

### 4. Staleness / invalidation (`persistence/staleness.py`)
`detect_changes(old, new)` compares two `{logical_key → content_hash}` snapshots
into added/changed/removed — the deterministic trigger that feeds the graph. Three
invalidation causes are handled: query change (cache key), source snapshot version
(`snapshot_is_stale`), and label version (a changed content hash on the label slot).

### 5. Trace spine (`trace/spine.py`, `trace/models.py`)
`spine.span(kind, name, inv, run)` is a context manager that times the block,
marks the first call of each kind **cold** vs **warm**, records tokens / cache-hit
/ retries / bytes / records / outcome, and writes one `trace_events` row. An
exception inside is recorded as `outcome=error` **and re-raised** (never swallowed).
Phase 8C and Phase 9 read only from this table.

## Restart / resume (the load-bearing test)
`test_restart_resume.py` runs a gather step, **closes the connection to simulate a
crash**, reopens the SQLite file as a fresh "process", and resumes the same run.
It asserts zero additional work: no re-fetch (cache hit), no re-run model call
(normalized names read back from persisted state), no duplicate evidence
(content-hash dedup).

## Where I would change each thing
| To change… | Edit… |
|---|---|
| A stored table/column | `persistence/schema.sql` (+ the matching repo) |
| Evidence immutability policy | the triggers in `schema.sql` |
| What makes a cache entry stale | `persistence/cache.py` + `persistence/staleness.py` |
| Recompute / short-circuit logic | `persistence/depgraph.py::DependencyGraph.recompute` |
| A recorded metric | add a column in `schema.sql` + a field in `trace/models.py`, set it in the span |
| DB engine (e.g. to DuckDB) | `persistence/db.py` only (repos are thin) |

## Tests (25 new; 57 total)
`test_persistence.py` (round-trips, immutability, dedup no-op), `test_cache.py`
(hit/miss/fetch-once/invalidate), `test_depgraph.py` (topo/cycle, only-downstream,
short-circuit, prior-run preserved), `test_staleness.py`, `test_trace_spine.py`
(ok/error/cold-warm/tokens), `test_restart_resume.py`. Run: `pytest -q`.
