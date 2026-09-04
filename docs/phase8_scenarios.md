# Phase 8 — Challenge scenarios (how they work, where to change them)

All three are automated (`tests/integration/test_scenarios.py`), reproducible, and
run fully offline with synthetic fixtures. The combined artifact is
`data/outputs/scenario_report.md`.

## A. Evidence update → selective recompute (`scenarios/a_evidence_update.py`)
Runs the investigation, then introduces ONE corrected later case version (US-002
flipped to serious). It updates the changed evidence slot's hash and calls the
Phase-3 dependency engine's `recompute`:
- **Recomputed**: the affected FAERS analyses + the memo sections that consumed
  changed outputs (executive summary, seriousness/missingness, adverse-event evidence).
- **Reused (verbatim)**: label evidence, external evidence, temporal pattern, and
  the narrative sections — 11 of 19 nodes in the demo.
- **Short-circuit**: `analysis:temporal` is recomputed but its output is unchanged,
  so `memo:temporal_pattern` is reused rather than regenerated.
- **Prior run preserved**: run 2 gets a new `run_id`; run 1's memo/analyses/graph
  remain in the DB (the audit trail). The before/after memo differs only in the
  affected sections.

## B. Conflicting evidence → disagreement preserved (`scenarios/b_conflict.py`)
A normal run where FAERS (a serious signal), the label (acknowledges the event,
asserts no causation), and PubMed (one study finding *no increased risk* + one case
series reporting a signal) disagree. The deterministic `detect_conflicts` builds a
`ConflictFinding` that keeps **every** position with its date and limitation and
sets `unresolved=True`. Nothing is dropped and no consensus is forced; all positions
are carried into the memo's conflicting-evidence section.

## C. Constrained run → cheaper, floor held (`scenarios/c_constrained.py`)
Reruns under a tighter model-token budget. Optimizations, all explicit: framing
**moved into deterministic logic** (no LLM framing call), **smaller context**
(top-N serious 5→2), and a **token budget** whose guard curtails late agentic
decisions (they fall back to the deterministic policy). Declared quality floor —
checked after the run — held on all counts: every claim cited, seriousness &
missingness counts identical to baseline, safety gates pass, top-N serious cases
inspected. Demo: **225 → 120 model tokens (46.7% reduction)**. Documented first
failure mode as the budget tightens further: agentic autonomy degrades first;
evidence gathering + deterministic analysis (the floor) are preserved longest.

## Where I would change each thing
| To change… | Edit… |
|---|---|
| The Scenario-A change (report vs label vs version) | the `new_evidence` passed to `run_scenario_a` |
| How stale work is detected/recomputed | `run_scenario_a` + `persistence/depgraph.py` |
| Conflict detection rules | `agent/conflicts.py` |
| Constrained-run optimizations / budget | `scenarios/c_constrained.py` + `RunContext` flags |
| The declared quality floor | `_check_floor` in `c_constrained.py` |

## Tests (3 new; 128 total)
`test_scenarios.py`: A (selective recompute + preservation + short-circuit),
B (disagreement preserved, unresolved, dates kept), C (≥40% token reduction with
the quality floor intact).
