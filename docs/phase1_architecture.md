# Phase 1 — Architecture & Requirements (no implementation code)

**Project:** Drug Safety Signal Investigation Assistant
**Source of truth:** `Take_home_Assessment.pdf` (PDF wins over the build prompt on any conflict)
**Status:** Phase 1 deliverable — awaiting gate approval before any implementation code.

---

## 0. What this document contains

1. Selected drug–event pair, with primary-source verification and dates.
2. Full requirements checklist extracted from the PDF, each mapped to an acceptance test.
3. Proposed repository structure.
4. Concrete spec of the **metrics/trace spine** (built Phase 1, wired everywhere from run 1).
5. Concrete spec of the **dependency-graph selective-recompute** design.
6. Architectural tradeoffs, rejected alternatives, assumptions, and explicit out-of-scope list.
7. "Where I would change each thing" pointers (legibility for defense).

---

## 1. Drug–event pair — decision and justification

The build prompt left the pair blank, so per its instructions I propose candidates and pick one, subject to two hard constraints:
**(A)** a real, documented, dated label change (so Scenario A is authentic), and
**(B)** FAERS pattern, label, and literature genuinely disagree or are incomplete (so Scenario B is real, not contrived).

### Candidates considered

| # | Drug – Event | Documented label change (constraint A) | Genuine conflict / incompleteness (constraint B) |
|---|---|---|---|
| **1 ✅ CHOSEN** | **Montelukast (Singulair) — serious neuropsychiatric events** (depression, suicidal ideation/behavior, agitation/aggression) | **Boxed Warning added 2020-03-04**, escalating from earlier Warnings/Precautions communications in **2008-03, 2009-01, 2009-06, 2009-08**. Verified against FDA primary source. | Strong FAERS spontaneous-report signal (incl. reports of completed suicide) **vs.** FDA-cited Sentinel/observational study that found **no increased risk vs. inhaled corticosteroids**; FDA states most reports "did not contain sufficient information to evaluate the relationship." Authentic disagreement + incompleteness. |
| 2 | Levofloxacin / fluoroquinolones — aortic aneurysm & dissection | FDA Drug Safety Communication **2018-12-20** + class label update (Cipro, Levaquin, Avelox, Factive, Ofloxacin). Verified. | Observational signal vs. confounding-by-indication debate; plausible but conflict is subtler and class-wide (product-normalization noise higher). |
| 3 | Varenicline (Chantix) — neuropsychiatric events | Boxed warning **added 2009**, then **removed 2016** after the EAGLES trial (a rare bidirectional change). | Good conflict, but the "removal" makes the before/after label modeling more complex than the assessment needs; dates not re-verified this pass. |

### Chosen: Montelukast — serious neuropsychiatric events. Review period: **2019-01-01 → 2021-12-31** (assumption, see §6).

**Why it wins.**
- **Cleanest Scenario A.** The label change is a *Boxed Warning addition* with a crisp primary-source date (2020-03-04) and a documented pre-state (Warnings/Precautions since 2008–09). I can snapshot a pre-2020 label section and the post-2020 boxed-warning section as two authentic versions — the evidence-update scenario is real, not invented.
- **Cleanest Scenario B.** The conflict is documented *by the FDA itself*: a large FAERS spontaneous-report signal (including completed suicides) sits next to a Sentinel/observational study finding no increased risk vs. inhaled corticosteroids, and the FDA explicitly flags report incompleteness. The system can preserve this disagreement honestly.
- **Strong FDE narrative.** Montelukast is extremely widely prescribed, including in children for asthma/allergic rhinitis, so the cost of a poor early investigation is high and the primary user (safety analyst) decision is consequential.
- **Distinct from the PDF's semaglutide/pancreatitis illustration**, as instructed.

**Provenance to record in the snapshot (Phase 5/8 will pin exact retrieval).**
- Primary: FDA Drug Safety Communication, "FDA requires Boxed Warning about serious mental health side effects for asthma and allergy drug montelukast (Singulair)…", dated 2020-03-04 — https://www.fda.gov/drugs/drug-safety-communications/fda-requires-boxed-warning-about-serious-mental-health-side-effects-asthma-and-allergy-drug
- Primary data: openFDA drug adverse-event endpoint (FAERS) + openFDA drug-label endpoint.
- Third source (Scenario B): a PubMed abstract / the Sentinel study reference showing the discordant observational result.

**Facts vs. assumptions vs. open customer questions** (FDE requirement, PDF §4) will be spelled out fully in `research_brief.md` (Phase 10); the pair choice above is grounded in the verified facts.

---

## 2. Requirements checklist → acceptance tests

Traceability IDs are used throughout the build. "Test" names the acceptance test that must pass at the relevant gate. PDF section references in parentheses.

### Agent behavior (PDF §7)
| ID | Requirement | Acceptance test |
|---|---|---|
| R-AG-1 | LLM makes ≥ real next-action decisions from current investigation state, not a hardcoded script (§7; core principle 3) | `test_agent_decisions_vary_with_state`: different state fixtures yield different logged next-actions; each decision row records the state it saw |
| R-AG-2 | Replan/stop safely on missing/inconsistent evidence or tool failure (§7) | `test_empty_evidence_safe_stop`, `test_tool_failure_retry_then_replan` |
| R-AG-3 | One primary agent; any boundary justified (§7; principle: single agent unless justified) | Design-doc assertion + `test_single_agent_graph` |
| R-AG-4 | Deterministic code for calculations, schema validation, limits, safety gates (§7; principle 2) | `test_no_llm_in_analysis_paths` (monkeypatch LLM to raise; analysis + validator still pass) |

### Tools & MCP (PDF §7)
| ID | Requirement | Acceptance test |
|---|---|---|
| R-TL-1 | ≥3 meaningful tools; ≥2 read-only exposed via a local MCP server (§7) | `test_mcp_server_exposes_three_tools` |
| R-TL-2 | Typed/schema-validated I/O, traceable, timeouts + bounded retries, no secrets in source (§7; principle) | `test_tool_io_schema`, `test_tool_timeout`, `test_tool_retry_backoff`, `test_no_secrets_grep` |
| R-TL-3 | Handle ≥1 tool failure, empty result, malformed response (§7) | `test_tool_empty_fixture`, `test_tool_malformed_fixture`, `test_tool_timeout_fixture` |
| R-TL-4 | Retrieved text is untrusted data, never instructions (§7; principle 6) | `test_prompt_injection_ignored` (injected instruction string in a fixture is not obeyed) |

### Context, memory, state (PDF §7)
| ID | Requirement | Acceptance test |
|---|---|---|
| R-CX-1 | Select relevant context, not every report/message per model call (§7; principle) | `test_context_builder_bounded` (cap enforced; top-N most-serious cases selected) |
| R-CX-2 | Separate raw evidence from model summaries; prose rebuildable from evidence+analysis (§7; principle 1) | `test_evidence_and_prose_separated`, `test_memo_rebuildable_from_a_and_b` |
| R-CX-3 | Persist state to resume after restart, no redundant reads/model calls (§7) | `test_restart_resume_no_redundant_io` (kill mid-run, resume; assert 0 duplicate tool/model calls) |
| R-CX-4 | Define + enforce staleness/invalidation when query, label, or snapshot changes (§7; principle) | `test_staleness_on_query_change`, `test_staleness_on_label_version`, `test_staleness_on_snapshot_hash` |

### Safety & evidence (PDF §7; build-prompt principles 1 & 4)
| ID | Requirement | Acceptance test |
|---|---|---|
| R-SF-1 | Every material claim links to a source record, label section, or named calculation (§7) | `test_citation_completeness` (0 uncited material claims) |
| R-SF-2 | Represent unknown/conflicting/missing explicitly (§7) | `test_conflict_preserved` (Scenario B memo retains disagreement + dates + limitations) |
| R-SF-3 | Advisory only; human remains decision-maker (§7) | validator rejects treatment-recommendation patterns |
| R-SF-4 | NEVER claim causation; NEVER compute/imply incidence or occurrence rates from spontaneous reports; no treatment recs; no certainty-from-uncertainty (§2 boundary; principle 4) | `test_output_validator_blocks_prohibited_patterns` — deterministic scanner fails the run on any prohibited pattern; not prompt-only |
| R-SF-5 | Structured-output safety: every model output Pydantic-validated, one bounded re-ask, deterministic fallback, never crash/silent pass (principle) | `test_malformed_model_json_reask_then_fallback` |

### Reproducibility (PDF §5; principle 5)
| ID | Requirement | Acceptance test |
|---|---|---|
| R-RP-1 | Snapshot FAERS/label/PubMed used for eval into local cache: retrieval timestamp, exact query, source, source version/date, content hash per record | `test_snapshot_record_has_provenance` |
| R-RP-2 | Eval runs fully from cache; final demo does not depend on live APIs | `test_eval_runs_offline` (network disabled) |
| R-RP-3 | Pin exact local model name+tag | asserted in config + README |

### Challenge scenarios (PDF §8) — all three mandatory, automated, reproducible
| ID | Requirement | Acceptance test |
|---|---|---|
| R-SC-A | Evidence update → detect stale state, recompute only affected, preserve prior run, show before/after + reused-vs-recomputed from trace | `scenario_a_evidence_update` |
| R-SC-B | Conflicting/incomplete evidence preserved with dates + limitations; no forced consensus, no silent drop | `scenario_b_conflict` |
| R-SC-C | Constrained run: ≥50% smaller context budget **or** ≥40% lower total token budget; quality floor defined before run; report cost reduction, quality change, first failure mode | `scenario_c_constrained` |

### Measurements / evaluation (PDF §9)
| ID | Requirement | Acceptance test |
|---|---|---|
| R-EV-1 | One repeatable command; report method, sample size, hardware, raw results | `test_eval_command_emits_report` |
| R-EV-2 | p50/p90/p95 latency, cold vs warm distinguished | fields present + populated from trace spine |
| R-EV-3 | Input/output/total tokens; context size; retry tokens; agent-message tokens | from trace spine |
| R-EV-4 | Tool calls attempted/succeeded/failed/retried/invalid/redundant | from trace spine |
| R-EV-5 | Records & bytes read/written; cache hits; peak process memory (VRAM if relevant) | from trace spine + `resource`/psutil |
| R-EV-6 | Quality checks: citation completeness, unsupported-claim count, valid output structure, correct limitation handling | quality_checks module |
| R-EV-7 | Work reused vs recomputed after evidence update; stale state detected; memo change | Scenario A trace |
| R-EV-8 | Baseline vs constrained comparison on same cases; explain what reduced cost & whether floor held | Scenario C report |
| R-EV-9 | If a metric can't be measured reliably, say so explicitly (no fabricated numbers) | methodology doc + explicit "unmeasured" markers |

### Repository & submission (PDF §11)
| ID | Requirement | Acceptance test / artifact |
|---|---|---|
| R-DOC-1 | README: setup, one-command run, assumptions, selected pair | README present |
| R-DOC-2 | Research brief (≥3 credible sources, ≥2 primary/regulatory), architecture diagram, design-decisions doc (alternatives + tradeoffs) | docs present |
| R-DOC-3 | Source, deps, tests, synthetic fixtures, reproducible eval command | repo contents |
| R-DOC-4 | ≥1 sample memo, before/after evidence-update trace, constrained-run result, results summary with raw measurements | artifacts under `data/`/`docs/` |
| R-DOC-5 | Statement of completed / not completed / next steps | docs |
| R-DOC-6 | AI-assistant disclosure + how output was reviewed | `docs/ai_disclosure.md` |
| R-DOC-7 | No secrets in any commit; `.env.example` with placeholders only; clean-env run | `.env.example` + secret-scan |

### Metrics spine & dependency graph (build prompt — load-bearing)
| ID | Requirement | Acceptance test |
|---|---|---|
| R-MS-1 | Metrics spine built Phase 1; every tool call & model call emits tokens/latency/context/retry/cache/outcome into SQLite trace; Phase 8C & Phase 9 read only from it | `test_every_tool_and_model_call_traced` |
| R-DG-1 | Evidence→analysis→memo-section dependency graph; each result stores consumed-evidence hashes; on change, diff hashes, mark only downstream stale, recompute only those, preserve prior run | `test_selective_recompute_only_downstream`, `test_prior_run_preserved` |

---

## 3. Proposed repository structure

```
drug-safety-signal-assistant/
  README.md                      # setup + one-command run (R-DOC-1)
  pyproject.toml                 # pinned deps, python>=3.11
  .env.example                   # placeholders only (R-DOC-7)
  Makefile / run.py              # one-command entrypoints: run, eval, scenarios
  docs/
    phase1_architecture.md       # THIS FILE
    research_brief.md            # FDE discovery, sources (R-DOC-2)
    design_decisions.md          # alternatives + tradeoffs (R-DOC-2)
    architecture.md              # mermaid diagram + narrative
    evaluation_methodology.md
    limitations.md
    ai_disclosure.md
  src/dsi/
    config.py                    # pinned model tag, budgets, paths — no secrets
    domain/                      # Phase 2 — Pydantic schemas
      investigation.py evidence.py provenance.py tools.py analysis.py memo.py state.py
    persistence/                 # Phase 3 — SQLite
      db.py schema.sql repositories.py depgraph.py cache.py
    trace/                       # Phase 1 — metrics spine (wired everywhere)
      spine.py instrumentation.py models.py
    mcp_server/                  # Phase 4 — 3 read-only MCP tools
      server.py http_client.py tools_faers.py tools_label.py tools_literature.py
    analysis/                    # Phase 5 — deterministic, no LLM
      normalize.py aggregate.py seriousness.py dedup.py temporal.py hashing.py staleness.py
    agent/                       # Phase 6 — LangGraph, single agent
      graph.py nodes.py decisions.py sufficiency.py conflicts.py safety_gates.py
      context_builder.py llm.py structured_output.py
    memo/                        # Phase 7
      builder.py templates.py validator.py    # validator = deterministic safety scanner
    scenarios/                   # Phase 8
      a_evidence_update.py b_conflict.py c_constrained.py
    eval/                        # Phase 9
      run_eval.py metrics.py quality_checks.py
    cli.py                       # investigate / eval / scenario commands
  tests/
    unit/ integration/ scenario/ fixtures/
  data/
    cache/                       # committed snapshot for reproducibility (R-RP-1/2)
    db/                          # sqlite runtime (gitignored)
    outputs/                     # sample memo, before/after trace, constrained result
```

Design intent: **one module = one phase**, small files, strong separation between (a) raw evidence `persistence`+`cache`, (b) deterministic `analysis`, (c) LLM `agent`/`memo` prose — matching core principle 1. The `trace` spine and `persistence.depgraph` are cross-cutting and built early.

---

## 4. Metrics / trace spine — concrete spec (Phase 1)

**Principle:** built now, routed through from the first run; Phases 8C and 9 are *readers*, never a separate reporting path.

**Storage — SQLite table `trace_events`:**

| column | meaning |
|---|---|
| `event_id` PK | uuid |
| `investigation_id`, `run_id` | scope; a re-run gets a new `run_id`, prior preserved |
| `span_id`, `parent_span_id` | nesting (node → tool/model call) |
| `kind` | `node` \| `tool_call` \| `model_call` \| `analysis` |
| `name` | e.g. `faers_search`, `decide_next_action` |
| `ts_start`, `ts_end`, `latency_ms` | timing |
| `tokens_in`, `tokens_out`, `tokens_total` | model calls; from Ollama `prompt_eval_count`/`eval_count` |
| `context_size_tokens` | prompt size measured before send |
| `retry_count` | bounded-retry counter |
| `cache_hit` | bool for evidence/analysis cache lookups |
| `outcome` | `ok` \| `error` \| `empty` \| `invalid` \| `redundant` |
| `error_type` | structured error class when outcome≠ok |
| `bytes_read`, `bytes_written`, `records_read`, `records_written` | I/O accounting (R-EV-5) |
| `attributes_json` | overflow (query text hash, tool args summary, model tag) |

**Instrumentation surface (three primitives, used everywhere):**
- `span(kind, name, investigation_id, run_id)` — context manager writing one row.
- `@instrument_tool` — wraps every MCP tool client call: captures latency, retries, outcome (empty/malformed→`invalid`), bytes/records, cache hit.
- `@instrument_model` — wraps every LLM call: captures tokens in/out/total, context size, retry count, outcome.

**Cold vs warm:** first model call and first DB open in a process are tagged cold via a process-level flag stored in `attributes_json`; eval buckets p50/p90/p95 by cold/warm.

**Peak memory / VRAM:** sampled with `psutil` (process RSS) at run end; VRAM noted from `ollama ps` if a GPU is present, else explicitly reported as "not measured on CPU-only" (R-EV-9 honesty).

**Where I'd change it:** add a metric → add a column + set it inside the two decorators; nothing else changes. The eval never computes metrics itself — it aggregates rows.

---

## 5. Dependency-graph selective recompute — concrete spec (Phases 2–3, used in 8A)

**Model:** a DAG per investigation with three node types.
- `evidence` node — one raw record (a FAERS report, a label section, a PubMed abstract). Carries `content_hash`.
- `analysis` node — one deterministic result (e.g. seriousness counts, temporal comparison). Records `inputs_hash` = hash of the sorted list of upstream `content_hash`es it consumed, plus its own `output_hash`.
- `memo_section` node — one section of the memo. Records the `output_hash`es of the analysis nodes and evidence nodes it cited.

**Tables:**
- `dep_nodes(node_id, run_id, type, content_hash|output_hash, inputs_hash)`
- `dep_edges(run_id, upstream_node_id, downstream_node_id)`

**Recompute algorithm when evidence changes (Scenario A):**
1. Ingest the new/corrected evidence; compute its `content_hash`. If identical to prior → **no-op** (logged).
2. Diff against the prior run's evidence hashes → set of `{added, changed, removed}` evidence nodes = the **dirty frontier**.
3. Propagate dirty forward along `dep_edges` in topological order to reachable `analysis` and `memo_section` nodes **only**. Untouched branches are never revisited.
4. Recompute each dirty `analysis` node. **Output-hash short-circuit:** if a recomputed node's `output_hash` equals its prior value, stop propagation through it (its downstream stays clean). This is the key optimization over naive "recompute everything."
5. Recompute only the `memo_section` nodes still dirty after step 4.
6. Write everything under a **new `run_id`**; the prior run's rows are preserved (audit trail). Emit a **reused-vs-recomputed breakdown** by counting nodes touched vs. total, read from the trace spine.

**Staleness triggers (R-CX-4):** any of — query params changed, source snapshot hash changed, label version changed, or any evidence `content_hash` changed — marks the corresponding evidence nodes dirty and runs the same algorithm.

**Where I'd change it:** the propagation and short-circuit live in `persistence/depgraph.py`; recompute functions are registered per node type. To add a new analysis, register its inputs (which evidence/analysis it consumes) and its compute fn — the graph handles staleness automatically.

---

## 6. Tradeoffs, rejected alternatives, assumptions, out-of-scope

### Key tradeoffs / rejected alternatives (expanded in `design_decisions.md`)
- **Single primary agent (chosen) vs. multi-agent (retriever/analyst/writer).** Rejected multi-agent: no boundary earns the coordination cost, and agent-to-agent messages are tokens the eval explicitly penalizes (PDF §9). Determinism is provided by the analysis layer, not a second LLM.
- **LangGraph (chosen) vs. hand-rolled orchestrator.** LangGraph is used for its explicit *cyclic* state graph + conditional edges (the `decide ⇄ action` loop with retry/replan/safe-stop branches) and the legibility that gives when explaining the execution trace. We do **not** use its multi-agent, parallel, or checkpointer features — resume (R-CX-3) is provided by our own `StateRepo`, not LangGraph's checkpointer. Honest tradeoff: a ~50-line custom orchestrator (a `while` loop dispatching on the chosen action) would also satisfy the requirements with one fewer dependency, and the PDF permits "a small custom orchestrator"; LangGraph was chosen for legibility and as the sanctioned/standard tool, accepting a dependency we only partly exploit. Pinned.
- **SQLite (chosen) vs. DuckDB.** Transactional investigation state + trace, small analytic volume → SQLite. DuckDB's columnar analytics not needed at this scale.
- **Deterministic output validator (chosen) vs. prompt-only safety.** Principle 4 is explicit: a Python scanner fails the run on prohibited patterns (causation claims, incidence/rate language, treatment recs). Prompt instructions alone are insufficient.
- **Structured output:** Pydantic-validate every model output, one bounded re-ask, then deterministic fallback + log — never crash, never silent pass.
- **Snapshot-from-cache eval:** all evaluation runs offline from committed snapshots; dev may use live APIs.

### Assumptions (ambiguity rule — smallest defensible, documented)
- **Review period 2019-01-01 → 2021-12-31**, chosen to straddle the 2020-03-04 boxed warning so both the label-change (A) and temporal-comparison work are meaningful. Temporal comparison reports *report counts by sub-period only*, never rates.
- **"Material claim"** defined operationally = any sentence containing a number, count, date, comparison, or source attribution; the validator uses this to enforce citation completeness.
- **Local model:** **pinned to `mistral:7b-instruct`** (confirmed decision); exact installed tag re-verified against the target Ollama install in Phase 6 config.
- **PubMed/third source** limited to abstract + metadata for the conflict scenario (not full-text mining).

### Confirmed decisions (Phase 1 gate)
- **Drug–event pair:** Montelukast → serious neuropsychiatric events, 2019–2021. **Approved.**
- **Local model:** `mistral:7b-instruct`. **Pinned.**
- **Constrained run (Scenario C):** primary target is **≥40% lower total model-token budget** (context-cut knob still implemented as a secondary lever).

### Explicitly out of scope
- No causal inference; **no incidence/occurrence-rate computation** (forbidden by §2).
- No production auth, multi-user, or web UI — CLI only.
- No dependence on live APIs in the demo/eval.
- No required quantization/fine-tuning (quantization optional; effect noted if used).
- Not exhaustive FAERS ingestion — a bounded, pinned snapshot for the chosen pair/period.

---

## 7. Legibility — "where I would change each thing" (quick index)

| To change… | Edit… |
|---|---|
| The drug–event pair or period | `config.py` + re-snapshot via cache builder |
| A tracked metric | one column + the two `@instrument_*` decorators in `trace/` |
| Recompute/staleness behavior | `persistence/depgraph.py` + `analysis/staleness.py` |
| A safety rule | `memo/validator.py` (deterministic patterns) + `agent/safety_gates.py` |
| Tool timeout/retry/failure handling | `mcp_server/http_client.py` + per-tool modules |
| What context the model sees | `agent/context_builder.py` (top-N selection + cap) |
| Agent next-action logic | `agent/decisions.py` + `agent/graph.py` |
| Memo content/structure | `memo/templates.py` (prose is rebuildable from evidence+analysis) |

---

## Phase 1 summary

- **Built:** requirements checklist mapped to acceptance tests (§2); verified drug–event pair with primary-source dates (§1); repo structure (§3); concrete metrics-spine (§4) and dependency-graph recompute (§5) designs; tradeoffs, assumptions, out-of-scope (§6).
- **Files changed:** `docs/phase1_architecture.md` (this file) — no implementation code, per the phase gate.
- **Tests:** none yet (design phase); every requirement above already carries the name of the test that will verify it.
- **Remaining risks:** (1) FAERS/label snapshot for this exact pair/period must be captured early (Phase 3/5) to guarantee offline reproducibility; (2) local-model JSON reliability — mitigated by the structured-output re-ask+fallback design; (3) confirming the installed Ollama model tag on the target hardware.

**Gate:** awaiting explicit approval before starting Phase 2.
