# Before / After — Evidence-Update Trace

_Scenario A: evidence changes after the first run. The system detects what became stale, recomputes ONLY the affected work, and preserves the prior run. Generated offline from the pinned snapshot; deterministic._

## 1. The change introduced
- Investigation: **montelukast / neuropsychiatric events** (2019-01-01 to 2021-12-31)
- One corrected follow-up version of case **EV-002** arrived and flips it to **serious**.
- This is a *new row* (a later version), not an edit — original evidence is immutable.
- New evidence id: `evd_cfb67cc02029`

## 2. Effect on the numbers
- Serious cases: **5 → 6**  (out of 7 → 7 distinct cases)

## 3. Work reused vs. recomputed (from the dependency graph)
- **Recomputed (8)**: analysis:aggregation, analysis:dedup, analysis:missingness, analysis:seriousness, analysis:temporal, memo:adverse_event_evidence, memo:executive_summary, memo:seriousness_missingness
- **Reused, untouched (11)**: memo:conflicting_evidence, memo:drug_and_event, memo:external_evidence, memo:human_review_considerations, memo:investigation_question, memo:label_evidence, memo:limitations, memo:review_period, memo:source_references, memo:temporal_pattern, memo:unresolved_questions
- **Short-circuited** (recomputed but output unchanged → downstream reused): analysis:temporal

> Only the parts that actually depend on the changed case were redone. An analysis whose output did not change stops the cascade, so its memo section is reused verbatim.

## 4. Memo sections — changed vs. reused

| Section | Status |
|---|---|
| investigation_question | reused |
| drug_and_event | reused |
| review_period | reused |
| executive_summary | RECOMPUTED |
| adverse_event_evidence | RECOMPUTED |
| temporal_pattern | reused |
| seriousness_missingness | RECOMPUTED |
| label_evidence | reused |
| external_evidence | reused |
| conflicting_evidence | reused |
| limitations | reused |
| unresolved_questions | reused |
| human_review_considerations | reused |
| source_references | reused |

## 5. What actually changed in the memo
### executive_summary
**Before:**
```
  - This advisory memo organizes public evidence for human review. It does not establish causation or rates and is not a treatment recommendation.
  - 5 of 7 distinct case(s) were flagged serious; 0 had unknown seriousness.
  - 7 distinct case(s) after resolving 1 confirmed version chain(s)/duplicate(s); 1 likely-duplicate group(s) were flagged for human review, not merged.
```
**After:**
```
  - This advisory memo organizes public evidence for human review. It does not establish causation or rates and is not a treatment recommendation.
  - 6 of 7 distinct case(s) were flagged serious; 0 had unknown seriousness.
  - 7 distinct case(s) after resolving 2 confirmed version chain(s)/duplicate(s); 1 likely-duplicate group(s) were flagged for human review, not merged.
```

### adverse_event_evidence
**Before:**
```
  - 7 report record(s) retrieved; most frequent reported reactions: [('Depression', 3), ('Suicidal ideation', 2), ('Aggression', 1), ('Anxiety', 1), ('Insomnia', 1)].
  - Serious case EV-001: reactions=[Depression, Suicidal ideation]; death=yes.
  - Serious case EV-003: reactions=[Aggression]; death=no.
  - Serious case EV-004: reactions=[Suicidal ideation]; death=yes.
  - Serious case EV-006: reactions=[Depression]; death=no.
  - Serious case EV-007: reactions=[Depression]; death=no.
```
**After:**
```
  - 7 report record(s) retrieved; most frequent reported reactions: [('Depression', 4), ('Suicidal ideation', 2), ('Aggression', 1), ('Anxiety', 1), ('Insomnia', 1)].
  - Serious case EV-001: reactions=[Depression, Suicidal ideation]; death=yes.
  - Serious case EV-002: reactions=[Insomnia, Depression]; death=yes.
  - Serious case EV-004: reactions=[Suicidal ideation]; death=yes.
  - Serious case EV-006: reactions=[Depression]; death=no.
  - Serious case EV-007: reactions=[Depression]; death=no.
```

### seriousness_missingness
**Before:**
```
  - Seriousness by criterion: {'death': 2, 'hospitalization': 0, 'life_threatening': 0, 'disabling': 0, 'congenital_anomaly': 0, 'other': 0}.
  - Missingness (fraction of reports missing each field): {'patient_age': 0.0, 'patient_sex': 0.0, 'receive_date': 0.0, 'reporter_qualification': 0.0, 'serious': 0.0}.
```
**After:**
```
  - Seriousness by criterion: {'death': 3, 'hospitalization': 0, 'life_threatening': 0, 'disabling': 0, 'congenital_anomaly': 0, 'other': 0}.
  - Missingness (fraction of reports missing each field): {'patient_age': 0.1429, 'patient_sex': 0.1429, 'receive_date': 0.0, 'reporter_qualification': 0.1429, 'serious': 0.0}.
```

## 6. Prior run preserved (audit trail)
- Run 1 id: `run_89fec34fd370`  (still in the database: **True**)
- Run 2 id: `run_9fed3282ee44`  (the recomputed run)
- Both runs' memos, analyses, and dependency graphs are kept — nothing overwritten.

---
## Appendix A — Full memo BEFORE the change (run 1)

# Drug Safety Signal Investigation Memo

_Investigation `inv_eval_montelukast` | run `run_89fec34fd370` | model `mistral:7b-instruct` | generated 2026-09-04 | validation: **passed**_

> Advisory only. A human safety professional is the decision-maker. This memo does not establish causation or rates and is not a treatment recommendation.

## Investigation question
- For montelukast, what does public evidence show about reports of neuropsychiatric events during 2019-01-01 to 2021-12-31, and is the evidence sufficient to warrant deeper human review?

## Drug and event
- Drug 'montelukast' normalized to ['montelukast', 'singulair']; event 'neuropsychiatric events' expanded to ['depression', 'suicidal ideation', 'suicidal behaviour', 'completed suicide', 'aggression', 'agitation', 'anxiety', 'insomnia', 'abnormal dreams', 'hallucination', 'irritability'].  
  _[ref: analysis:ana_582a2c3be4c0]_

## Review period
- Reports reviewed from 2019-01-01 to 2021-12-31.

## Executive summary
- This advisory memo organizes public evidence for human review. It does not establish causation or rates and is not a treatment recommendation.
- 5 of 7 distinct case(s) were flagged serious; 0 had unknown seriousness.  
  _[ref: analysis:ana_dae9505d41cc]_
- 7 distinct case(s) after resolving 1 confirmed version chain(s)/duplicate(s); 1 likely-duplicate group(s) were flagged for human review, not merged.  
  _[ref: analysis:ana_9b951f6c332a]_

## Adverse-event evidence
- 7 report record(s) retrieved; most frequent reported reactions: [('Depression', 3), ('Suicidal ideation', 2), ('Aggression', 1), ('Anxiety', 1), ('Insomnia', 1)].  
  _[ref: analysis:ana_8b1ec7a33d44]_
- Serious case EV-001: reactions=[Depression, Suicidal ideation]; death=yes.  
  _[ref: evidence:evd_6fe2cb7daebc]_
- Serious case EV-003: reactions=[Aggression]; death=no.  
  _[ref: evidence:evd_308c2e8a1e51]_
- Serious case EV-004: reactions=[Suicidal ideation]; death=yes.  
  _[ref: evidence:evd_e89f349f87cc]_
- Serious case EV-006: reactions=[Depression]; death=no.  
  _[ref: evidence:evd_caba6df26d05]_
- Serious case EV-007: reactions=[Depression]; death=no.  
  _[ref: evidence:evd_e70f5c776e32]_

## Temporal pattern
- Report counts by year: {'2019': 2, '2020': 3, '2021': 2}; direction: flat. These are counts of spontaneous reports, not incidence or rates.  
  _[ref: analysis:ana_00df4f3f583d]_

## Seriousness and missingness
- Seriousness by criterion: {'death': 2, 'hospitalization': 0, 'life_threatening': 0, 'disabling': 0, 'congenital_anomaly': 0, 'other': 0}.  
  _[ref: analysis:ana_dae9505d41cc]_
- Missingness (fraction of reports missing each field): {'patient_age': 0.0, 'patient_sex': 0.0, 'receive_date': 0.0, 'reporter_qualification': 0.0, 'serious': 0.0}.  
  _[ref: analysis:ana_520baf2c0dd9]_

## Label evidence
- Label section 'boxed_warning' (effective 2020-03-04) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_66504df81c8d]_
- Label section 'warnings_and_precautions' (effective 2020-03-04) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_cbba9b38176f]_
- Label section 'adverse_reactions' (effective 2020-03-04) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_256605452496]_

## External evidence
- PMID 30000001, 2019-01-01: "No increased risk of neuropsychiatric events with montelukast versus inhaled corticosteroids".  
  _[ref: evidence:evd_eb95a51ec79a]_
- PMID 30000002, 2021-01-01: "Case series: montelukast and suicidality in adolescents".  
  _[ref: evidence:evd_037437f74735]_
- PMID 30000003, 2020-01-01: "Montelukast neuropsychiatric adverse events: a disproportionality analysis".  
  _[ref: evidence:evd_728ebaf9f886]_

## Conflicting evidence
- Sources do not point in the same direction: a spontaneous-report signal and/or case reports coexist with an observational study reporting no increased risk. The disagreement is preserved; it is not resolved by this system.  
  _[ref: analysis:ana_a897c71c5640]_
- FAERS spontaneous reports: 7 case(s), 5 flagged serious (spontaneous reports cannot establish causation or rates).  
  _[ref: analysis:ana_a897c71c5640]_
- Label section 'adverse_reactions' (effective 2020-03-04): describes the event; label does not assert causation.  
  _[ref: analysis:ana_a897c71c5640]_
- Label section 'boxed_warning' (effective 2020-03-04): describes the event; label does not assert causation.  
  _[ref: analysis:ana_a897c71c5640]_
- Label section 'warnings_and_precautions' (effective 2020-03-04): describes the event; label does not assert causation.  
  _[ref: analysis:ana_a897c71c5640]_
- Literature PMID 30000002, 2021-01-01: "Case series: montelukast and suicidality in adolescents" [reports a signal].  
  _[ref: analysis:ana_a897c71c5640]_
- Literature PMID 30000003, 2020-01-01: "Montelukast neuropsychiatric adverse events: a disproportionality analysis".  
  _[ref: analysis:ana_a897c71c5640]_
- Literature PMID 30000001, 2019-01-01: "No increased risk of neuropsychiatric events with montelukast versus inhaled corticosteroids" [reports no increased risk].  
  _[ref: analysis:ana_a897c71c5640]_

## Limitations
- Spontaneous adverse-event reports cannot establish that the drug caused the event, and cannot be used to compute incidence or occurrence rates.
- Public reports may be incomplete, duplicated, or unverified.

## Unresolved questions
- Do the likely-duplicate groups represent the same case? (requires manual review)
- What is the clinical context of the serious cases (confounders, comorbidity)?

## Human-review considerations
- This memo is advisory. A human safety professional must review the individual serious cases and decide whether deeper evaluation is warranted.

## Source references
- evd_66504df81c8d: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-04
- evd_cbba9b38176f: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-04
- evd_256605452496: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-04
- evd_eb95a51ec79a: PubMed | query='montelukast neuropsychiatric events' | retrieved 2026-09-04
- evd_037437f74735: PubMed | query='montelukast neuropsychiatric events' | retrieved 2026-09-04
- evd_728ebaf9f886: PubMed | query='montelukast neuropsychiatric events' | retrieved 2026-09-04
- evd_6fe2cb7daebc: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_308c2e8a1e51: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_e89f349f87cc: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_caba6df26d05: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_e70f5c776e32: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04


---
## Appendix B — Full memo AFTER the change (run 2)

# Drug Safety Signal Investigation Memo

_Investigation `inv_eval_montelukast` | run `run_9fed3282ee44` | model `mistral:7b-instruct` | generated 2026-09-04 | validation: **passed**_

> Advisory only. A human safety professional is the decision-maker. This memo does not establish causation or rates and is not a treatment recommendation.

## Investigation question
- For montelukast, what does public evidence show about reports of neuropsychiatric events during 2019-01-01 to 2021-12-31, and is the evidence sufficient to warrant deeper human review?

## Drug and event
- Drug 'montelukast' normalized to ['montelukast', 'singulair']; event 'neuropsychiatric events' expanded to ['depression', 'suicidal ideation', 'suicidal behaviour', 'completed suicide', 'aggression', 'agitation', 'anxiety', 'insomnia', 'abnormal dreams', 'hallucination', 'irritability'].  
  _[ref: analysis:ana_582a2c3be4c0]_

## Review period
- Reports reviewed from 2019-01-01 to 2021-12-31.

## Executive summary
- This advisory memo organizes public evidence for human review. It does not establish causation or rates and is not a treatment recommendation.
- 6 of 7 distinct case(s) were flagged serious; 0 had unknown seriousness.  
  _[ref: analysis:ana_732809a049a0]_
- 7 distinct case(s) after resolving 2 confirmed version chain(s)/duplicate(s); 1 likely-duplicate group(s) were flagged for human review, not merged.  
  _[ref: analysis:ana_cb8c98a85375]_

## Adverse-event evidence
- 7 report record(s) retrieved; most frequent reported reactions: [('Depression', 4), ('Suicidal ideation', 2), ('Aggression', 1), ('Anxiety', 1), ('Insomnia', 1)].  
  _[ref: analysis:ana_c951304744e5]_
- Serious case EV-001: reactions=[Depression, Suicidal ideation]; death=yes.  
  _[ref: evidence:evd_6fe2cb7daebc]_
- Serious case EV-002: reactions=[Insomnia, Depression]; death=yes.  
  _[ref: evidence:evd_cfb67cc02029]_
- Serious case EV-004: reactions=[Suicidal ideation]; death=yes.  
  _[ref: evidence:evd_e89f349f87cc]_
- Serious case EV-006: reactions=[Depression]; death=no.  
  _[ref: evidence:evd_caba6df26d05]_
- Serious case EV-007: reactions=[Depression]; death=no.  
  _[ref: evidence:evd_e70f5c776e32]_

## Temporal pattern
- Report counts by year: {'2019': 2, '2020': 3, '2021': 2}; direction: flat. These are counts of spontaneous reports, not incidence or rates.  
  _[ref: analysis:ana_00df4f3f583d]_

## Seriousness and missingness
- Seriousness by criterion: {'death': 3, 'hospitalization': 0, 'life_threatening': 0, 'disabling': 0, 'congenital_anomaly': 0, 'other': 0}.  
  _[ref: analysis:ana_732809a049a0]_
- Missingness (fraction of reports missing each field): {'patient_age': 0.1429, 'patient_sex': 0.1429, 'receive_date': 0.0, 'reporter_qualification': 0.1429, 'serious': 0.0}.  
  _[ref: analysis:ana_877f1e59da65]_

## Label evidence
- Label section 'boxed_warning' (effective 2020-03-04) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_66504df81c8d]_
- Label section 'warnings_and_precautions' (effective 2020-03-04) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_cbba9b38176f]_
- Label section 'adverse_reactions' (effective 2020-03-04) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_256605452496]_

## External evidence
- PMID 30000001, 2019-01-01: "No increased risk of neuropsychiatric events with montelukast versus inhaled corticosteroids".  
  _[ref: evidence:evd_eb95a51ec79a]_
- PMID 30000002, 2021-01-01: "Case series: montelukast and suicidality in adolescents".  
  _[ref: evidence:evd_037437f74735]_
- PMID 30000003, 2020-01-01: "Montelukast neuropsychiatric adverse events: a disproportionality analysis".  
  _[ref: evidence:evd_728ebaf9f886]_

## Conflicting evidence
- Sources do not point in the same direction: a spontaneous-report signal and/or case reports coexist with an observational study reporting no increased risk. The disagreement is preserved; it is not resolved by this system.  
  _[ref: analysis:ana_a897c71c5640]_
- FAERS spontaneous reports: 7 case(s), 5 flagged serious (spontaneous reports cannot establish causation or rates).  
  _[ref: analysis:ana_a897c71c5640]_
- Label section 'adverse_reactions' (effective 2020-03-04): describes the event; label does not assert causation.  
  _[ref: analysis:ana_a897c71c5640]_
- Label section 'boxed_warning' (effective 2020-03-04): describes the event; label does not assert causation.  
  _[ref: analysis:ana_a897c71c5640]_
- Label section 'warnings_and_precautions' (effective 2020-03-04): describes the event; label does not assert causation.  
  _[ref: analysis:ana_a897c71c5640]_
- Literature PMID 30000002, 2021-01-01: "Case series: montelukast and suicidality in adolescents" [reports a signal].  
  _[ref: analysis:ana_a897c71c5640]_
- Literature PMID 30000003, 2020-01-01: "Montelukast neuropsychiatric adverse events: a disproportionality analysis".  
  _[ref: analysis:ana_a897c71c5640]_
- Literature PMID 30000001, 2019-01-01: "No increased risk of neuropsychiatric events with montelukast versus inhaled corticosteroids" [reports no increased risk].  
  _[ref: analysis:ana_a897c71c5640]_

## Limitations
- Spontaneous adverse-event reports cannot establish that the drug caused the event, and cannot be used to compute incidence or occurrence rates.
- Public reports may be incomplete, duplicated, or unverified.

## Unresolved questions
- Do the likely-duplicate groups represent the same case? (requires manual review)
- What is the clinical context of the serious cases (confounders, comorbidity)?

## Human-review considerations
- This memo is advisory. A human safety professional must review the individual serious cases and decide whether deeper evaluation is warranted.

## Source references
- evd_66504df81c8d: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-04
- evd_cbba9b38176f: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-04
- evd_256605452496: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-04
- evd_eb95a51ec79a: PubMed | query='montelukast neuropsychiatric events' | retrieved 2026-09-04
- evd_037437f74735: PubMed | query='montelukast neuropsychiatric events' | retrieved 2026-09-04
- evd_728ebaf9f886: PubMed | query='montelukast neuropsychiatric events' | retrieved 2026-09-04
- evd_6fe2cb7daebc: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_308c2e8a1e51: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_e89f349f87cc: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_caba6df26d05: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_e70f5c776e32: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04

