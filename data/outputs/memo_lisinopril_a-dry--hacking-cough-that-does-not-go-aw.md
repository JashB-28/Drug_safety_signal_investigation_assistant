# Drug Safety Signal Investigation Memo

_Investigation `inv_a41a676d3bd1` | run `run_4199f776de38` | model `mistral:7b-instruct` | generated 2026-09-04 | validation: **passed**_

> Advisory only. A human safety professional is the decision-maker. This memo does not establish causation or rates and is not a treatment recommendation.

## Investigation question
- For Lisinopril, what does public evidence show about reports of A dry, hacking cough that does not go away during 2018-12-20 to 2022-12-31, and is the evidence sufficient to warrant deeper human review?

## Drug and event
- Drug 'Lisinopril' normalized to ['lisinopril']; event 'A dry, hacking cough that does not go away' expanded to ['a dry, hacking cough that does not go away'].  
  _[ref: analysis:ana_31649efde890]_

## Review period
- Reports reviewed from 2018-12-20 to 2022-12-31.

## Executive summary
- No reports of serious cases associated with the drug were found in the provided data.
- 0 of 0 distinct case(s) were flagged serious; 0 had unknown seriousness.  
  _[ref: analysis:ana_f331b2d705a7]_
- 0 distinct case(s) after resolving 0 confirmed version chain(s)/duplicate(s); 0 likely-duplicate group(s) were flagged for human review, not merged.  
  _[ref: analysis:ana_fc35edee5e01]_

## Adverse-event evidence
- 0 report record(s) retrieved; most frequent reported reactions: [].  
  _[ref: analysis:ana_a23eaa35fcdc]_

## Temporal pattern
- Report counts by year: {'2018': 0, '2019': 0, '2020': 0, '2021': 0, '2022': 0}; direction: insufficient_data. These are counts of spontaneous reports, not incidence or rates.  
  _[ref: analysis:ana_6287cac05151]_

## Seriousness and missingness
- Seriousness by criterion: {'death': 0, 'hospitalization': 0, 'life_threatening': 0, 'disabling': 0, 'congenital_anomaly': 0, 'other': 0}.  
  _[ref: analysis:ana_f331b2d705a7]_
- Missingness (fraction of reports missing each field): {'patient_age': 0.0, 'patient_sex': 0.0, 'receive_date': 0.0, 'reporter_qualification': 0.0, 'serious': 0.0}.  
  _[ref: analysis:ana_4d7175573676]_

## Label evidence
- Label section 'boxed_warning' (effective 2026-06-02) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_ff50a25b893b]_
- Label section 'warnings_and_precautions' (effective 2026-06-02) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_4ed28179adf7]_
- Label section 'adverse_reactions' (effective 2026-06-02) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_4e8d02f72189]_
- Label section 'indications_and_usage' (effective 2026-06-02) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_076f11e281a6]_
- Label section 'contraindications' (effective 2026-06-02) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_8cd327ab403b]_

## External evidence
- No external literature was retrieved.

## Conflicting evidence
- Fewer than two source types were available to compare.

## Limitations
- Spontaneous adverse-event reports cannot establish that the drug caused the event, and cannot be used to compute incidence or occurrence rates.
- Public reports may be incomplete, duplicated, or unverified.
- No adverse-event reports were found for this drug/event/period.
- No external literature was retrieved.

## Unresolved questions
- Do the likely-duplicate groups represent the same case? (requires manual review)
- What is the clinical context of the serious cases (confounders, comorbidity)?

## Human-review considerations
- This memo is advisory. A human safety professional must review the individual serious cases and decide whether deeper evaluation is warranted.

## Source references
- evd_ff50a25b893b: openFDA/drug/label | query='openfda.generic_name:"Lisinopril" OR openfda.brand_name:"Lisinopril"' | retrieved 2026-09-04
- evd_4ed28179adf7: openFDA/drug/label | query='openfda.generic_name:"Lisinopril" OR openfda.brand_name:"Lisinopril"' | retrieved 2026-09-04
- evd_4e8d02f72189: openFDA/drug/label | query='openfda.generic_name:"Lisinopril" OR openfda.brand_name:"Lisinopril"' | retrieved 2026-09-04
- evd_076f11e281a6: openFDA/drug/label | query='openfda.generic_name:"Lisinopril" OR openfda.brand_name:"Lisinopril"' | retrieved 2026-09-04
- evd_8cd327ab403b: openFDA/drug/label | query='openfda.generic_name:"Lisinopril" OR openfda.brand_name:"Lisinopril"' | retrieved 2026-09-04
