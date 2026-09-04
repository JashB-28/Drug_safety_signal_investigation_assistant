# Design Decisions & Tradeoffs

Each decision lists what was chosen, the simpler/alternative design considered, and
why the choice won. Honest tradeoffs are called out.

### 1. One agent, not multi-agent
**Chosen:** a single LangGraph investigation agent. **Rejected:** retriever/analyst/
writer multi-agent. **Why:** no boundary earns its coordination cost; the determinism
a second "analyst agent" would add is better provided by plain tested Python (exact,
auditable). Agent-to-agent messages are tokens the eval explicitly penalizes (§9).
The PDF permits one agent and warns against adding agents to satisfy scenarios.

### 2. LangGraph vs. a custom orchestrator (the most questionable dependency)
**Chosen:** LangGraph, for its explicit *cyclic* state graph + conditional edges
(the `decide ⇄ action` loop) and the legibility that gives when explaining a trace —
and it's a tool the PDF names. **We do NOT use** its multi-agent, parallel, or
checkpointer features; resume is our own `StateRepo`. **Honest tradeoff:** a ~50-line
`while`-loop orchestrator would satisfy the requirements with one fewer dependency,
and the PDF permits that. Kept LangGraph for clarity, accepting an under-exploited
dependency. Swappable in one module.

### 3. Deterministic analysis, not LLM analysis
**Chosen:** all counting/dedup/temporal/missingness in plain Python. **Rejected:**
letting the model compute over reports. **Why:** exactness (LLMs miscount), the §7
requirement that claims trace to a "clearly identified calculation," structural
enforcement of the no-rates/no-causation boundary, and token cost. See
[architecture.md](architecture.md) agentic-vs-deterministic table.

### 4. Deterministic output validator, not prompt-only safety
**Chosen:** a Python scanner that fails the run on prohibited patterns (causation,
incidence/rate, treatment recs, false certainty), with negation-awareness so the
memo's own disclaimers pass. **Rejected:** trusting the prompt. **Why:** the safety
boundary must be guaranteed, not requested. **Refinement (from real data):** verbatim
source text (paper titles, reaction terms) is marked `quoted` and exempt from the
prohibited-*claim* scan — quoting a paper titled "Drug-induced…" is not the system
asserting causation — while the system's own synthesis stays fully scanned.

### 5. Confirmed vs. likely duplicates; keep-latest-version-per-case
**Chosen:** same FAERS `report_id` (= CASEID) ⇒ confirmed version chain/duplicate;
different ids sharing a fingerprint ⇒ likely, flagged not merged. Count analyses run
on the latest version per case. **Why:** `safetyreportid` is case-level, so this is
the correct FAERS reduction; asserting a merge we can't prove would be unsafe, and
counting every version would inflate totals. (This was a deliberate correctness
guard — see the identifier note in `analysis/dedup.py`.)

### 6. SQLite, not DuckDB / files
**Chosen:** SQLite for transactional investigation state, evidence, trace, and the
dependency graph, with a WAL journal and immutability triggers. **Why:** small
analytic volume; we need transactions, crash-safe resume, and DB-level constraints
more than columnar analytics. DB engine is isolated to `persistence/db.py`.

### 7. Structured output with bounded re-ask + deterministic fallback
**Chosen:** validate every model JSON output against Pydantic, re-ask once, then fall
back deterministically and log `invalid`. **Why:** local models emit unreliable JSON;
a malformed reply must never crash the graph or pass through unchecked.

### 8. Snapshot cache + offline eval, live `investigate`
**Chosen:** tool responses are cached; the eval seeds a pinned snapshot and blocks the
network (`OfflineGuardClient`); `dsi investigate` fetches live (keyless openFDA/PubMed)
and caches so re-runs are offline. **Why:** the demo/eval must not depend on unstable
live responses, while real use still works on demand.

### 9. Trace spine built early, read late
**Chosen:** one `trace_events` table + a `span()` primitive wired through every tool
and model call from the first run; the eval and constrained run only *read* it.
**Why:** measurements can't drift from behaviour, and instrumentation isn't a
reporting afterthought.
