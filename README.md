# Drug Safety Signal Investigation Assistant

An open-source, **agentic** pharmacovigilance assistant. Given a marketed drug, a
suspected adverse event, and a review period, it gathers public evidence
(openFDA FAERS + drug label + PubMed), runs deterministic analysis, and produces a
concise, **fully-cited, safety-bounded memo** for a human safety analyst to review.

> **Advisory only.** The system never claims the drug caused the event, never
> computes incidence/occurrence rates from spontaneous reports, and never makes
> treatment recommendations. A human safety professional remains the decision-maker.

**Selected drug–event pair:** montelukast (Singulair) → serious neuropsychiatric
events, review period **Jan 2019 – Dec 2021**. Chosen because it has a real,
dated label change (FDA **Boxed Warning, 2020-03-04**) and a genuine evidence
conflict (a strong FAERS spontaneous-report signal vs. an observational study
reporting no increased risk). Rationale + sources: [docs/research_brief.md](docs/research_brief.md).

**Local model:** `mistral:7b-instruct` via Ollama (local, no API key, no cost).

## Assumptions

These choices are documented in `docs/research_brief.md` and `docs/phase1_architecture.md`.

- Review period: 2019–2021. Covers the time before and after the FDA's March 2020 boxed warning.
- Exact event names are needed. Terms like "depression" can find reports; vague phrases may return no results.
- Count each case once. `report_id` uses openFDA's `safetyreportid`. When a case has follow-ups, analyses use its latest version.
- Key claims need citations. This includes numbers, dates, comparisons, and statements about sources.
- Possible duplicates are flagged. Matching patient and report details suggest duplicates, but a person must review them.
- Synonym support is limited. Name variations are mainly supported for the montelukast example; other inputs get basic cleanup.
- Local AI, two data modes. The system uses `mistral:7b-instruct` through Ollama. Tests use a fixed synthetic dataset; investigations fetch live public data.

---

## Quick start

Prerequisites: **Python 3.11+**, [`uv`](https://docs.astral.sh/uv/), and
[Ollama](https://ollama.com/) running locally.

```bash
uv venv --python 3.13 .venv
```
```bash
source .venv/Scripts/activate      # Windows Git Bash;  PowerShell: .venv\Scripts\Activate.ps1;  macOS/Linux: source .venv/bin/activate
```
```bash
uv pip install -e ".[dev]"
```
```bash
ollama pull mistral:7b-instruct
```

Then verify everything (no model or network needed — runs on synthetic fixtures):

```bash
pytest -q
```

## Running it

**Reproducible offline evaluation** (pinned snapshot, real model; writes `data/outputs/`):

```bash
dsi eval
```

**The three challenge scenarios** (evidence-update recompute, conflict, constrained run):

```bash
dsi scenarios
```

**Investigate any pair — LIVE openFDA/PubMed** (no key; first run fetches and caches,
re-runs are offline):

```bash
dsi investigate --drug "montelukast" --event "depression" --start 2019-01-01 --end 2021-12-31
```

The event should be a specific reaction term (a MedDRA preferred term such as
`depression` or `suicidal ideation`); a vague phrase may match no reports, in which
case the memo honestly reports insufficient evidence. The memo is written to
`data/outputs/memo_<drug>_<event>.md`.

## What's where

| Path | Contents |
|---|---|
| `src/dsi/domain/` | Pydantic schemas: evidence, provenance, analysis, memo, agent state |
| `src/dsi/persistence/` | SQLite storage, snapshot cache, the selective-recompute dependency graph |
| `src/dsi/trace/` | the metrics/trace spine (every tool + model call) |
| `src/dsi/mcp_server/` | the local MCP server + 3 read-only tools (openFDA ×2, PubMed) |
| `src/dsi/analysis/` | deterministic analysis (no LLM): normalize, aggregate, seriousness, missingness, dedup, temporal |
| `src/dsi/agent/` | the single LangGraph investigation agent |
| `src/dsi/memo/` | memo builder, safety validator, Markdown renderer |
| `src/dsi/scenarios/` | the three challenge scenarios |
| `src/dsi/eval/` | the offline evaluation harness + pinned dataset |
| `tests/` | 130 tests (unit + integration + scenarios) |
| `data/outputs/` | sample memo, scenario report, eval results |
| `docs/` | research brief, architecture, design decisions, evaluation, limitations, status, AI disclosure |

## Documentation

- [Research brief](docs/research_brief.md) — user, workflow, data problems, pair choice, sources
- [Architecture](docs/architecture.md) — diagram + agentic-vs-deterministic split
- [Design decisions](docs/design_decisions.md) — alternatives considered and why
- [Evaluation methodology](docs/evaluation_methodology.md)
- [Limitations](docs/limitations.md)
- [Status: completed / not completed / next steps](docs/status.md)
- [AI-assistant disclosure](docs/ai_disclosure.md)
- Per-phase build notes: `docs/phase1_architecture.md` … `docs/phase9_evaluation.md`

## Configuration & security

No API keys are required. Configuration is via environment variables with safe
defaults — copy `.env.example` to `.env` to override the Ollama host or model tag.
**No secrets, credentials, or real patient data are committed.** The evidence used
by `dsi eval`/`dsi scenarios` is clearly-labelled synthetic data; real data flows
only through `dsi investigate` (which reads public, keyless openFDA/PubMed).
