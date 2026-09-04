# Status — Completed / Not Completed / Next Steps

## Completed
- **Domain schemas** (Pydantic): investigation, evidence + provenance, tool I/O,
  analysis results, memo, agent state; content hashing. (130 tests overall.)
- **Evidence layer:** SQLite persistence; **immutable evidence** (DB triggers);
  snapshot cache; the **selective-recompute dependency graph** with output-hash
  short-circuit; investigation-state persistence with **kill/restart resume** proven.
- **Metrics/trace spine:** every tool + model call recorded; read by the eval and the
  constrained run.
- **MCP tools:** local FastMCP server with 3 read-only tools (openFDA FAERS, openFDA
  label, PubMed); typed I/O; bounded timeout + retries with backoff (429/503 honor
  `Retry-After`); structured errors; empty/malformed/timeout handled; prompt-injection
  captured as inert data.
- **Deterministic analysis:** normalize, aggregate, seriousness, missingness,
  dedup (confirmed vs. likely; keep-latest-version-per-case), temporal (counts only).
- **Agent (LangGraph):** genuine next-action decisions logged with state; retry /
  tool-failure / empty-evidence / replan / safe-stop; structured-output re-ask +
  fallback; full trace persisted.
- **Memo:** all 14 required sections; every material claim cited; deterministic
  **safety validator** (negation-aware; quoted-source exemption); Markdown renderer.
- **Challenge scenarios A/B/C:** automated, reproducible, with artifacts.
- **Evaluation:** one command, fully offline from a pinned snapshot, metrics from the
  spine; baseline-vs-constrained; artifacts in `data/outputs/`.
- **`dsi investigate`:** run any pair with LIVE openFDA/PubMed + caching (verified
  live: montelukast/depression, 124 real records, memo passed).
- **Docs:** research brief, architecture (+diagram), design decisions, evaluation
  methodology, limitations, AI disclosure, per-phase notes.

## Not completed (deliberately or out of time)
- **Real-data committed snapshot** for the eval (eval currently uses synthetic;
  `investigate` uses real live data).
- **FAERS pagination** (fetch caps at ~100 reports).
- **Event-term expansion into the FAERS query** (normalization expands for display,
  not yet for querying).
- **PubMed abstracts** (metadata only).
- **UI**, multi-user, auth, packaging as a wheel with bundled schema (runs from source).
- **Presentation slides** (separate deliverable).

## Next steps (priority order)
1. Add a `snapshot` command that fetches a real openFDA/PubMed dataset once and
   commits it, so the eval runs on real data offline.
2. Add FAERS pagination + feed normalized event terms into the FAERS query, so wide
   periods and vague event phrases work well.
3. Broaden the synonym/event tables (or wire a MedDRA/SMQ source) beyond montelukast.
4. Optionally add a thin HTML/web view over the structured memo.
5. Package for a clean wheel install (bundle `schema.sql` as package data).
