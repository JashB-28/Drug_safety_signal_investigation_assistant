# Limitations

Stated plainly, because evidence discipline includes being honest about the tool's
own boundaries.

## Scope / product
- **Advisory only, by design.** Never asserts causation, never computes incidence/
  rates from spontaneous reports, never recommends treatment. This is a constraint,
  not a gap.
- **No UI.** CLI + structured memo only. The memo is deliberately structured data, so
  a UI would be a thin view over it (see the UI discussion in the design notes).
- **No auth / multi-user / web service.** Single-user local tool.

## Evidence & data
- **Eval/scenarios use synthetic data.** `dsi eval` and `dsi scenarios` run on a
  pinned, clearly-labelled synthetic snapshot for reproducibility. **Real** openFDA/
  PubMed data flows through `dsi investigate` (verified live). Snapshotting a real
  dataset into the committed cache is a straightforward next step.
- **FAERS fetch caps at ~100 reports (no pagination yet).** For a wide review period
  this undercounts and can skew the by-year temporal tally. Pagination is a small,
  isolated improvement in the FAERS tool.
- **Event matching is exact against openFDA MedDRA terms.** A specific reaction term
  (e.g. `depression`) finds reports; a vague phrase may match none. Automatic term
  expansion (e.g. an SMQ, or falling back to normalized terms in the query) is future
  work — normalization currently expands terms for display, not for the FAERS query.
- **PubMed tool returns citation metadata, not abstracts.** Abstracts need `efetch`
  XML; the conflict analysis works from titles + metadata.

## Analysis
- **Likely-duplicate detection is heuristic** (sex/age/reactions/date/country) and is
  intentionally *flagged, not merged* — it can miss or over-group; a human decides.
- **Conflict detection is title-keyword based** (signal vs. no-signal regex). It
  preserves all positions honestly but is a coarse divergence detector, not a
  meta-analysis.
- **Drug/event synonym tables are scoped to the montelukast pair** as the documented
  extension point; other pairs use a minimal canonicalization.

## Model / agent
- **Local 7B model.** Decision quality and JSON reliability are bounded by
  `mistral:7b-instruct`; the structured-output re-ask + deterministic fallback + legal-
  action constraint keep this safe, at the cost of occasionally falling back to the
  deterministic policy.
- **Sequential, single agent.** No parallelism.

## Evaluation
- **Small sample** (one pair, few reps) — enough to demonstrate the metrics spine and
  the tradeoffs, not a statistical benchmark.
- **CPU-only latency; VRAM not measured** (reported as such, not fabricated).
- The constrained run imposes a 50% budget to reliably clear the ≥40% achieved bar
  (real per-call token variance causes guard overshoot).
