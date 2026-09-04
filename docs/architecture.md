# Architecture

## One-glance view

```mermaid
flowchart TB
    subgraph CLI["CLI (dsi)"]
        I["investigate / eval / scenarios"]
    end

    subgraph AGENT["Single investigation agent (LangGraph)"]
        direction TB
        INIT[initialize] --> NORM[normalize]
        NORM --> DECIDE{{"decide (LLM)"}}
        DECIDE -->|retrieve_*| TOOLS
        DECIDE -->|run_analysis| ANA
        DECIDE -->|check_sufficiency| SUFF[sufficiency]
        DECIDE -->|detect_conflicts| CONF[conflicts]
        DECIDE -->|generate_memo / stop| FIN[finalize]
        TOOLS --> DECIDE
        ANA --> DECIDE
        SUFF --> DECIDE
        CONF --> DECIDE
    end

    subgraph TOOLS["MCP tools (read-only)"]
        T1[faers_search]
        T2[label_fetch]
        T3[literature_search]
    end

    subgraph ANA["Deterministic analysis (no LLM)"]
        A1[normalize] & A2[aggregate] & A3[seriousness] & A4[missingness] & A5[dedup] & A6[temporal]
    end

    subgraph STORE["Persistence + trace (SQLite)"]
        E[(evidence — immutable)]
        AR[(analysis_results)]
        M[(memos)]
        DG[(dependency graph)]
        C[(snapshot cache)]
        TR[(trace spine)]
    end

    subgraph EXT["Public sources"]
        FDA[(openFDA FAERS + label)]
        PM[(PubMed)]
    end

    I --> AGENT
    TOOLS -->|"live (investigate) or cache (eval)"| EXT
    TOOLS --> C
    AGENT --> STORE
    FIN --> MEMO["Cited memo → safety validator"]
```

Everything the agent does flows through the **trace spine** (tokens/latency/outcome
per tool + model call) and is persisted to SQLite. Evidence is stored **immutable**
(DB triggers); analysis and memo are separate categories that record the evidence
they consumed, so the whole thing is auditable and selectively recomputable.

## The three data categories (kept physically separate)

| Category | Where | Who may write it |
|---|---|---|
| (a) raw evidence | `domain/evidence.py`, `evidence` table | tools only; immutable after write |
| (b) deterministic analysis | `domain/analysis.py`, `analysis_results` | plain Python, never the LLM |
| (c) LLM prose (memo) | `domain/memo.py`, `memos` | the agent; rebuildable from (a)+(b) |

## Agentic vs. deterministic (the §10 answer)

The LLM is used in exactly two roles; everything numeric or safety-critical is
plain, tested Python.

| Action | Layer | Why |
|---|---|---|
| Choose the next action from state | **LLM** (agentic) | open-ended judgement over investigation state |
| Write one framing sentence | **LLM** (agentic) | non-factual narrative; validated + fallback |
| Which actions are *legal* next | Deterministic | bounds the agent; guarantees termination |
| Normalize drug/event | Deterministic | table-driven, reproducible |
| Count serious cases / missingness | Deterministic | exact arithmetic; LLMs miscount |
| Dedup / version resolution | Deterministic | precise identity logic; confirmed vs. likely |
| Temporal comparison | Deterministic | counts only, never rates |
| Conflict detection | Deterministic | preserves positions; no forced consensus |
| Sufficiency check | Deterministic | rules, not judgement |
| Safety validation of the memo | Deterministic | prohibited-pattern scan; fails the run |
| Structured-output validation | Deterministic | Pydantic + bounded re-ask + fallback |

## Selective recompute (dependency graph)

`evidence → analysis → memo_section` is modelled as a per-run DAG. Each analysis and
memo section records the content/output hashes it consumed. When evidence changes,
only downstream nodes whose inputs actually changed are recomputed; if a recomputed
analysis produces an unchanged output, the cascade **short-circuits** and its memo
sections are reused. Prior runs are preserved under a new `run_id` (audit trail).
See `persistence/depgraph.py` and Scenario A.

## Control, safety, and cost properties

- **Bounded & terminating:** step limit + token budget guards force safe termination.
- **Failure-tolerant:** tool failures are structured values (not exceptions); bounded
  retries with backoff (429/503 honor `Retry-After`); empty results are valid.
- **Untrusted input:** retrieved text enters the model only inside delimited DATA
  blocks; the system prompt marks it untrusted.
- **Context control:** the decision prompt sees only compact state summaries; the
  memo framing sees only the top-N most serious cases.
- **Reproducible:** the eval runs fully offline from a pinned snapshot cache.
