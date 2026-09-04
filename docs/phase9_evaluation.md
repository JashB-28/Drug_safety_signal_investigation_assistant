# Phase 9 — Evaluation (how it works, where to change it)

## One command
`dsi eval` (or `python -m dsi.eval.run_eval`) seeds a pinned offline snapshot, runs
the investigation N times, does the baseline-vs-constrained comparison and the
Scenario-A recompute, and writes `data/outputs/eval_results.{md,json}`.

## Reproducibility — fully offline
`eval/fixtures.py` is the pinned dataset (clearly-labeled synthetic; swap this one
module to run against real openFDA/PubMed snapshots). `eval/seed.py` puts the exact
tool responses the agent will request into the snapshot cache, then the run uses an
`OfflineGuardClient` that **raises on any network attempt** — so a cache miss fails
loudly instead of silently going live. The eval therefore does not depend on any
live API.

## Metrics — read only from the trace spine
`eval/metrics.py` aggregates `trace_events`, so the numbers cannot drift from what
happened: latency p50/p90/p95 (cold rep vs warm reps), tokens in/out/total, max
context, retry tokens, tool calls attempted/succeeded/failed/empty/retried, invalid
model outputs, cache hits, records read/written, and peak process memory. VRAM is
reported as **explicitly not measured** on a CPU-only run rather than fabricated.
`eval/quality_checks.py` adds citation completeness, unsupported-claim count,
schema validity, required-section coverage, and safety-boundary compliance.

## Representative real run (mistral:7b-instruct, this machine)
- Latency: cold ~12.3 s, warm p50 ~11.3 s (CPU-only).
- 8 model calls, 1851 tokens; 3 tool calls, all cache hits (offline); 14 records read.
- Quality: 26 material claims, **0 uncited**, **0 unsupported**, all sections, safe.
- Constrained: 1851 → 1042 tokens (**43.7% reduction**), quality floor held.
- Evidence update: **8 recomputed / 11 reused**, temporal short-circuited, prior run
  preserved.

## An honest note on the constrained budget
With the real model, per-decision token counts vary, so the budget guard (which
checks before a call) overshoots slightly. The eval therefore imposes a **50%**
model-token budget to reliably achieve the assessment's **≥40%** actual reduction;
both the imposed target and the achieved reduction are reported.

## Where I would change each thing
| To change… | Edit… |
|---|---|
| The eval dataset (or use real snapshots) | `eval/fixtures.py` (+ re-seed) |
| Which metrics are reported | `eval/metrics.py` / `eval/quality_checks.py` |
| Reps / budget / output location | args to `run_eval` (and `cli.py`) |
| The offline guarantee | `OfflineGuardClient` in `eval/seed.py` |

## Tests (1 new; 129 total)
`test_eval.py` runs the harness offline with a scripted model and asserts the metric
families are present, the run is offline (cache hits), the quality floor holds, the
constrained run is cheaper, and the evidence-update reused/recomputed split + prior-
run preservation are reported.
