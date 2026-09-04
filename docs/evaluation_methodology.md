# Evaluation Methodology

## Command
`dsi eval` (or `python -m dsi.eval.run_eval`). It seeds a pinned offline snapshot,
runs the investigation N times, runs the baseline-vs-constrained comparison and the
Scenario-A recompute, and writes `data/outputs/eval_results.{md,json}`.

## Method
- **Sample:** one investigation (montelukast → neuropsychiatric events, 2019–2021)
  run `reps` times (default 3); rep 1 is **cold**, reps 2+ are **warm**.
- **Data:** a pinned, clearly-labelled **synthetic** snapshot (`eval/fixtures.py`),
  seeded into the cache. The run uses an `OfflineGuardClient` that raises on any
  network attempt, so the eval is provably offline. Swapping `fixtures.py` for real
  openFDA/PubMed snapshots changes nothing else.
- **Metrics source:** the SQLite **trace spine** only, so numbers cannot drift from
  what actually happened.
- **Hardware:** captured in the report (platform, logical CPUs, Python version).

## What is measured
- **Latency:** end-to-end wall clock, p50/p90/p95, **cold vs. warm** distinguished.
- **Tokens:** input / output / total, max context size, retry tokens.
- **Tool calls:** attempted / succeeded / failed / empty / retried; invalid model outputs.
- **I/O & cache:** records read/written, cache hits.
- **Memory:** peak process RSS. **VRAM is reported as explicitly not measured** on a
  CPU-only run (rather than fabricated).
- **Quality (deterministic):** material claims, uncited-claim count, citation
  completeness, unsupported (prohibited-pattern) claims, required-section coverage,
  schema validity, safety-boundary compliance.
- **Baseline vs. constrained:** token totals, % reduction, whether the quality floor held.
- **Evidence-update recompute:** reused vs. recomputed nodes, short-circuits,
  seriousness before/after, prior-run preservation.

## Constrained-run methodology (Scenario C)
The constrained run applies three explicit optimizations — framing moved to
deterministic logic (no LLM framing call), smaller context (top-N serious 5→2), and a
model-token budget whose guard curtails late agentic decisions. The **quality floor
is declared before the run**: every claim still cited, seriousness & missingness
counts identical to baseline, safety gates pass, top-N serious cases still inspected.

**Honest note on the budget:** with the real model, per-decision token counts vary and
the budget guard (checked before a call) overshoots slightly, so the eval imposes a
**50%** token budget to reliably achieve the assessment's **≥40% achieved** reduction.
Both the imposed target and the achieved number are reported.

## Representative result (real model, this machine)
Cold ~12.3 s / warm p50 ~11.3 s; 8 model calls, 1851 tokens; 3 tool calls all cache
hits; 0 uncited and 0 unsupported claims; all 14 sections; constrained 1851→1042
tokens (**43.7%**), floor held; evidence update **8 recomputed / 11 reused**, prior
run preserved. Raw numbers: `data/outputs/eval_results.json`.

## Honesty policy
Where a metric can't be measured reliably (e.g. VRAM on CPU), the report says so
explicitly rather than inventing a value. All numbers come from the trace spine.
