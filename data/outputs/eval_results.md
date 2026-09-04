# Evaluation Results

_Method: Offline eval from a pinned synthetic snapshot; metrics read from the SQLite trace spine._
_Snapshot: synthetic-eval-v1 (2026-09-03) | pair: montelukast / neuropsychiatric events | reps: 3 | generated 2026-09-04T07:07:44.634785+00:00_

## Hardware
- Windows-11-10.0.26200-SP0 | 32 logical CPUs | Python 3.13.12
- VRAM: not measured (CPU-only run; report VRAM from `ollama ps` if GPU is used)

## Latency (end-to-end)
- Cold: **41710.65 ms**
- Warm: p50 **10982.36 ms** | p90 11193.14 ms | p95 11193.14 ms (n=2, min 10982.36 / max 11193.14 ms)

## Tokens & I/O (baseline run)
- Model calls: 8 | tokens in/out/total: 1394/457/**1851** | retry tokens: 0 | max context: 297
- Tool calls attempted/succeeded/failed/empty/retried: 3/3/0/0/0 | invalid model outputs: 0
- Cache hits: 3 | records read/written: 14/0
- Peak process memory: **102.3 MB**

## Quality (baseline memo)
- Material claims: 26 | uncited: **0** | citation completeness: **1.0**
- Unsupported (prohibited-pattern) claims: **0** | all required sections: True | safety-boundary compliant: **True** | schema valid: True

## Baseline vs constrained
- Tokens: 1851 -> 1042 (**43.7%** reduction)
- Quality floor held: **True**

## Evidence update: work reused vs recomputed
- Recomputed (8): ['analysis:aggregation', 'analysis:dedup', 'analysis:missingness', 'analysis:seriousness', 'analysis:temporal', 'memo:adverse_event_evidence', 'memo:executive_summary', 'memo:seriousness_missingness']
- Reused (11): ['memo:conflicting_evidence', 'memo:drug_and_event', 'memo:external_evidence', 'memo:human_review_considerations', 'memo:investigation_question', 'memo:label_evidence', 'memo:limitations', 'memo:review_period', 'memo:source_references', 'memo:temporal_pattern', 'memo:unresolved_questions']
- Short-circuited: ['analysis:temporal']
- Serious count before/after: [7, 5] -> [7, 6] | prior run preserved: **True**
