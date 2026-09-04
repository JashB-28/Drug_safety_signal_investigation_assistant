# Phase 5 — Deterministic analysis (how it works, where to change it)

## What this layer is
All the numeric/inferential work, as plain tested Python — **no LLM, no I/O**.
Each function takes evidence records and returns a typed `AnalysisResult` that
records exactly which evidence it consumed, so the dependency graph (Phase 3) can
recompute selectively. This layer is where the assessment's "deterministic
controls — never delegate to the LLM" principle actually lives.

## The functions (`src/dsi/analysis/`)
| Function | Produces | Notes |
|---|---|---|
| `normalize` | `NormalizationResult` | drug salt-stripping + brand/generic synonyms; event phrase → reaction terms. Query-driven (consumes no evidence). |
| `aggregate_reports` | `AggregationResult` | counts by year / reaction / seriousness. Counts only. |
| `summarize_seriousness` | `SeriousnessSummary` | serious / non-serious / unknown + per-criterion (death, hospitalization, …). |
| `summarize_missingness` | `MissingnessSummary` | per-field missing count + fraction; unreported = `None`, never a default. |
| `resolve_duplicates` | `DedupResult` | **confirmed vs likely** (see below). |
| `compare_periods` | `TemporalComparison` | report-count trend by year, with a rate/causation disclaimer baked in. |

## Identifier mapping (the FAERS trap — pinned)
`report_id` maps to openFDA **`safetyreportid`, which is the CASE-level id (FAERS
`CASEID`)**, stable across follow-ups; the version is `report_version`
(`safetyreportversion`). This is why "same `report_id` ⇒ confirmed version chain"
is the correct branch. The canonical FAERS reduction — **keep the latest version
per case** — is `collapse_to_latest_versions`, and **all count analyses
(aggregation, seriousness, missingness, temporal) must run on the collapsed set**,
or a followed-up case is counted once per version. Tested: a two-version case gives
`unique_report_count == 1` and, after collapse, a serious count of 1 (not 2).

## The two judgment calls worth defending
1. **Confirmed vs likely duplicates.** Same FAERS `report_id` ⇒ **confirmed** (a
   follow-up version chain, or an exact duplicate when a version repeats) — this is
   certain. Different ids that share a distinctive fingerprint (sex + age +
   reactions + date + country) ⇒ **likely** — plausible but unproven, so it is
   *flagged for human review and NOT merged*. `unique_report_count` counts distinct
   `report_id`s only. Sparse reports (missing sex/age/reactions) are never even
   suspected. This is the "distinguish confirmed from likely when certainty isn't
   possible" requirement, made concrete.
2. **Temporal is descriptive, not causal.** `compare_periods` reports the direction
   of the *report count* and carries the disclaimer that this is not incidence, not
   a rate, and not causal evidence — reporting rises for many reasons.

## How it feeds selective recompute
Every result is built with `make_provenance_fields(consumed_hashes, output_body)`,
which sets `consumed_evidence_hashes` (sorted), `inputs_hash` (order-independent),
and `output_hash` (hash of the output *data only*). Tests prove the output hash is
stable for identical evidence and changes when evidence changes — exactly the
signal the dependency graph uses.

## Where I would change each thing
| To change… | Edit… |
|---|---|
| Drug/event synonyms (or add a pair) | the tables in `analysis/normalize.py` |
| A seriousness criterion or missingness field | `_CRITERIA` / `_MISSINGNESS_FIELDS` in `seriousness.py` |
| The likely-duplicate fingerprint | `_likely_key` in `dedup.py` |
| Temporal bucketing (e.g. quarters) | `compare_periods` in `temporal.py` |

## Tests (14 new; 95 total)
`test_analysis.py`: normalization (salt/synonym/fallback), aggregation, seriousness
+ missingness, dedup (confirmed chain, exact dup, likely-not-merged, sparse-skip),
temporal (increase / insufficient-data), and dependency tracking (stable/changing
output hash). All run with no model or network — the layer is pure.
