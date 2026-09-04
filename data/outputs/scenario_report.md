# Challenge Scenario Results (synthetic fixtures)

_Drug-event pair: montelukast -> neuropsychiatric events. Data below uses clearly-labeled synthetic fixtures; the pipeline is identical for cached openFDA/PubMed snapshots._

## A. Evidence update -> selective recompute
- Run 1: `run_6446492a41a7`  ->  Run 2: `run_cca69df41552`  (prior run preserved: **True**)
- Change introduced: corrected later version of case US-002 (now serious). Serious count **1 -> 2**
- Recomputed nodes (8): ['analysis:aggregation', 'analysis:dedup', 'analysis:missingness', 'analysis:seriousness', 'analysis:temporal', 'memo:adverse_event_evidence', 'memo:executive_summary', 'memo:seriousness_missingness']
- Reused nodes (11): ['memo:conflicting_evidence', 'memo:drug_and_event', 'memo:external_evidence', 'memo:human_review_considerations', 'memo:investigation_question', 'memo:label_evidence', 'memo:limitations', 'memo:review_period', 'memo:source_references', 'memo:temporal_pattern', 'memo:unresolved_questions']
- Short-circuited (recomputed, output unchanged): ['analysis:temporal']

## B. Conflicting evidence -> disagreement preserved
- Unresolved (not forced to consensus): **True**
  - FAERS spontaneous reports: 2 case(s), 1 flagged serious (spontaneous reports cannot establish causation or rates).
  - Label section 'adverse_reactions' (effective 2020-03-04): describes the event; label does not assert causation.
  - Label section 'warnings_and_precautions' (effective 2020-03-04): describes the event; label does not assert causation.
  - Label section 'boxed_warning' (effective 2020-03-04): describes the event; label does not assert causation.
  - Literature PMID 44444444, 2021-01-01: "Case series: montelukast and suicidality" [reports a signal].
  - Literature PMID 33333333, 2019-01-01: "No increased risk of neuropsychiatric events with montelukast vs ICS" [reports no increased risk].

## C. Constrained run -> cost down, quality floor held
- Baseline model tokens: **225**  ->  Constrained: **120**  (**46.7%** reduction)
- Quality floor held: **True**  details={'claims_cited': True, 'seriousness_exact': True, 'missingness_exact': True, 'safety_gates_pass': True, 'top_n_inspected': True}
- First failure mode as budget tightens: Agentic decision autonomy degrades first: late decisions fall back to the deterministic policy. Evidence gathering and the deterministic analyses are preserved longest; only if the budget is cut so far that analysis cannot run would the exact seriousness/missingness counts (the quality floor) break.
