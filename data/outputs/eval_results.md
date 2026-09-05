# Evaluation Results

_Method: Offline eval from a pinned REAL openFDA/PubMed snapshot; metrics read from the SQLite trace spine._
_Snapshot: real-openfda-pubmed (2026-09-05T03:03:27.894781+00:00) | pair: montelukast / depression | reps: 3 | generated 2026-09-05T03:06:25.036872+00:00_

## Hardware
- Windows-11-10.0.26200-SP0 | 32 logical CPUs | Python 3.13.12
- VRAM: not measured (CPU-only run; report VRAM from `ollama ps` if GPU is used)

## Latency (end-to-end)
- Cold: **21085.27 ms**
- Warm: p50 **11217.32 ms** | p90 11414.4 ms | p95 11414.4 ms (n=2, min 11217.32 / max 11414.4 ms)

## Tokens & I/O (baseline run)
- Model calls: 8 | tokens in/out/total: 1710/451/**2161** | retry tokens: 0 | max context: 566
- Tool calls attempted/succeeded/failed/empty/retried: 3/3/0/0/0 | invalid model outputs: 0
- Cache hits: 3 | records read/written: 124/0
- Peak process memory: **111.8 MB**

## Quality (baseline memo)
- Material claims: 62 | uncited: **0** | citation completeness: **1.0**
- Unsupported (prohibited-pattern) claims: **0** | all required sections: True | safety-boundary compliant: **True** | schema valid: True

## Baseline vs constrained
- Tokens: 2161 -> 1239 (**42.7%** reduction)
- Quality floor held: **True**

## Evidence update: work reused vs recomputed
- Recomputed (8): ['analysis:aggregation', 'analysis:dedup', 'analysis:missingness', 'analysis:seriousness', 'analysis:temporal', 'memo:adverse_event_evidence', 'memo:executive_summary', 'memo:seriousness_missingness']
- Reused (11): ['memo:conflicting_evidence', 'memo:drug_and_event', 'memo:external_evidence', 'memo:human_review_considerations', 'memo:investigation_question', 'memo:label_evidence', 'memo:limitations', 'memo:review_period', 'memo:source_references', 'memo:temporal_pattern', 'memo:unresolved_questions']
- Short-circuited: ['analysis:aggregation', 'analysis:temporal', 'memo:adverse_event_evidence']
- Serious count before/after: [100, 85] -> [100, 85] | prior run preserved: **True**
