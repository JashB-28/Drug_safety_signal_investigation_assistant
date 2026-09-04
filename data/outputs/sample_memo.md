# Drug Safety Signal Investigation Memo

_Investigation `inv_bc14eb1c41d7` | run `run_5d59d7e2f945` | model `mistral:7b-instruct` | generated 2026-09-03 | validation: **passed**_

> Advisory only. A human safety professional is the decision-maker. This memo does not establish causation or rates and is not a treatment recommendation.

## Investigation question
- For montelukast, what does public evidence show about reports of neuropsychiatric events during 2019-01-01 to 2021-12-31, and is the evidence sufficient to warrant deeper human review?

## Drug and event
- Drug 'montelukast' normalized to ['montelukast', 'singulair']; event 'neuropsychiatric events' expanded to ['depression', 'suicidal ideation', 'suicidal behaviour', 'completed suicide', 'aggression', 'agitation', 'anxiety', 'insomnia', 'abnormal dreams', 'hallucination', 'irritability'].  
  _[ref: analysis:ana_1f52e47c17d3]_

## Review period
- Reports reviewed from 2019-01-01 to 2021-12-31.

## Executive summary
- This advisory memo organizes public evidence for human review. It does not establish causation or rates and is not a treatment recommendation.
- 1 of 2 distinct case(s) were flagged serious; 0 had unknown seriousness.  
  _[ref: analysis:ana_3705cb80d282]_
- 2 distinct case(s) after resolving 0 confirmed version chain(s)/duplicate(s); 0 likely-duplicate group(s) were flagged for human review, not merged.  
  _[ref: analysis:ana_19106c711c4a]_

## Adverse-event evidence
- 2 report record(s) retrieved; most frequent reported reactions: [('Depression', 1), ('Suicidal ideation', 1)].  
  _[ref: analysis:ana_9bc997d89594]_
- Serious case US-001: reactions=[Depression]; death=yes.  
  _[ref: evidence:evd_ad006891bf1b]_
- Serious case US-002: reactions=[Suicidal ideation]; death=no.  
  _[ref: evidence:evd_9d343daf04bf]_

## Temporal pattern
- Report counts by year: {'2019': 0, '2020': 2, '2021': 0}; direction: insufficient_data. These are counts of spontaneous reports, not incidence or rates.  
  _[ref: analysis:ana_c7497364a8db]_

## Seriousness and missingness
- Seriousness by criterion: {'death': 1, 'hospitalization': 0, 'life_threatening': 0, 'disabling': 0, 'congenital_anomaly': 0, 'other': 0}.  
  _[ref: analysis:ana_3705cb80d282]_
- Missingness (fraction of reports missing each field): {'patient_age': 0.5, 'patient_sex': 0.0, 'receive_date': 0.0, 'reporter_qualification': 0.5, 'serious': 0.0}.  
  _[ref: analysis:ana_3777f645a620]_

## Label evidence
- Label section 'boxed_warning' (effective 2020-03-04) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_d16a01d9679c]_
- Label section 'warnings_and_precautions' (effective 2020-03-04) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_64f7467f51b1]_
- Label section 'adverse_reactions' (effective 2020-03-04) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_3246cc21749d]_

## External evidence
- PMID 33333333, 2019-01-01: "No increased risk of neuropsychiatric events with montelukast vs ICS".  
  _[ref: evidence:evd_3e3540a3466b]_
- PMID 44444444, 2021-01-01: "Case series: montelukast and suicidality".  
  _[ref: evidence:evd_f4d479ea9776]_

## Conflicting evidence
- Sources do not point in the same direction: a spontaneous-report signal and/or case reports coexist with an observational study reporting no increased risk. The disagreement is preserved; it is not resolved by this system.  
  _[ref: analysis:ana_0c998db2e977]_
- FAERS spontaneous reports: 2 case(s), 1 flagged serious (spontaneous reports cannot establish causation or rates).  
  _[ref: analysis:ana_0c998db2e977]_
- Label section 'adverse_reactions' (effective 2020-03-04): describes the event; label does not assert causation.  
  _[ref: analysis:ana_0c998db2e977]_
- Label section 'warnings_and_precautions' (effective 2020-03-04): describes the event; label does not assert causation.  
  _[ref: analysis:ana_0c998db2e977]_
- Label section 'boxed_warning' (effective 2020-03-04): describes the event; label does not assert causation.  
  _[ref: analysis:ana_0c998db2e977]_
- Literature PMID 33333333, 2019-01-01: "No increased risk of neuropsychiatric events with montelukast vs ICS" [reports no increased risk].  
  _[ref: analysis:ana_0c998db2e977]_
- Literature PMID 44444444, 2021-01-01: "Case series: montelukast and suicidality" [reports a signal].  
  _[ref: analysis:ana_0c998db2e977]_

## Limitations
- Spontaneous adverse-event reports cannot establish that the drug caused the event, and cannot be used to compute incidence or occurrence rates.
- Public reports may be incomplete, duplicated, or unverified.
- Only 2 distinct case(s) found; evidence is limited.

## Unresolved questions
- Do the likely-duplicate groups represent the same case? (requires manual review)
- What is the clinical context of the serious cases (confounders, comorbidity)?

## Human-review considerations
- This memo is advisory. A human safety professional must review the individual serious cases and decide whether deeper evaluation is warranted.

## Source references
- evd_d16a01d9679c: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-03
- evd_64f7467f51b1: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-03
- evd_3246cc21749d: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-03
- evd_3e3540a3466b: PubMed | query='montelukast neuropsychiatric events' | retrieved 2026-09-03
- evd_f4d479ea9776: PubMed | query='montelukast neuropsychiatric events' | retrieved 2026-09-03
- evd_ad006891bf1b: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-03
- evd_9d343daf04bf: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"neuropsychiatric events" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-03
