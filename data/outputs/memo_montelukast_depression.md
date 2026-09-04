# Drug Safety Signal Investigation Memo

_Investigation `inv_87c55eb88eeb` | run `run_442d54489b20` | model `mistral:7b-instruct` | generated 2026-09-04 | validation: **passed**_

> Advisory only. A human safety professional is the decision-maker. This memo does not establish causation or rates and is not a treatment recommendation.

## Investigation question
- For montelukast, what does public evidence show about reports of depression during 2019-01-01 to 2021-12-31, and is the evidence sufficient to warrant deeper human review?

## Drug and event
- Drug 'montelukast' normalized to ['montelukast', 'singulair']; event 'depression' expanded to ['depression'].  
  _[ref: analysis:ana_995d5e15ddaf]_

## Review period
- Reports reviewed from 2019-01-01 to 2021-12-31.

## Executive summary
- The provided data contains six serious cases, each associated with various reactions, across different age groups and sexes, with five of the cases resulting in death.
- 85 of 100 distinct case(s) were flagged serious; 0 had unknown seriousness.  
  _[ref: analysis:ana_7dfa28347e00]_
- 100 distinct case(s) after resolving 0 confirmed version chain(s)/duplicate(s); 1 likely-duplicate group(s) were flagged for human review, not merged.  
  _[ref: analysis:ana_236e9ad72702]_

## Adverse-event evidence
- 100 report record(s) retrieved; most frequent reported reactions: [('Depression', 98), ('Anxiety', 53), ('Insomnia', 31), ('Sleep terror', 17), ('Drug ineffective', 15)].  
  _[ref: analysis:ana_3ea21c97fb48]_
- Serious case 15897240: reactions=[Vulvovaginal pain, Oxygen saturation decreased, Abdominal pain upper, Pulmonary arterial hypertension, Oedema peripheral, Crying, Vulvovaginal mycotic infection, Depression, Vulvovaginal burning sensation, Headache]; death=yes.  
  _[ref: evidence:evd_02314a904de2]_
- Serious case 15937675: reactions=[Chronic kidney disease, Depression, Acute kidney injury, Rebound acid hypersecretion, Renal failure, Renal injury, Dementia, Anxiety]; death=yes.  
  _[ref: evidence:evd_0837368a0de2]_
- Serious case 15952336: reactions=[End stage renal disease, Depression, Renal failure, Hyperparathyroidism secondary, Renal injury, Nephrogenic anaemia, Rebound acid hypersecretion, Acute kidney injury, Chronic kidney disease]; death=yes.  
  _[ref: evidence:evd_48659af220ea]_
- Serious case 16045137: reactions=[Depression, Dizziness, Asthenia, Malaise, Therapeutic response unexpected, Death]; death=yes.  
  _[ref: evidence:evd_eb7a3211237c]_
- Serious case 16278455: reactions=[Death, Graft versus host disease in gastrointestinal tract, Failure to thrive, Renal injury, Skin cancer, Cytomegalovirus infection reactivation, Erectile dysfunction, Cellulitis, Device related infection, Terminal state, Adenovirus infection, Skin discomfort, Skin lesion, Depression, Blood creatinine increased, Heart rate irregular, Mobility decreased, Muscle twitching, Renal disorder, Limb injury, Off label use, Product dose omission issue, Liver function test increased, Muscle spasms, Constipation, Asthenia]; death=yes.  
  _[ref: evidence:evd_951b37609ad1]_

## Temporal pattern
- Report counts by year: {'2019': 100, '2020': 0, '2021': 0}; direction: insufficient_data. These are counts of spontaneous reports, not incidence or rates.  
  _[ref: analysis:ana_e8119cfcee04]_

## Seriousness and missingness
- Seriousness by criterion: {'death': 5, 'hospitalization': 26, 'life_threatening': 2, 'disabling': 14, 'congenital_anomaly': 0, 'other': 78}.  
  _[ref: analysis:ana_7dfa28347e00]_
- Missingness (fraction of reports missing each field): {'patient_age': 0.26, 'patient_sex': 0.09, 'receive_date': 0.0, 'reporter_qualification': 0.09, 'serious': 0.0}.  
  _[ref: analysis:ana_c76fb10b70ea]_

## Label evidence
- Label section 'boxed_warning' (effective 2026-03-05) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_900cf94484ac]_
- Label section 'adverse_reactions' (effective 2026-03-05) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_30d9bfc67bee]_
- Label section 'indications_and_usage' (effective 2026-03-05) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_e5c4fb542785]_
- Label section 'contraindications' (effective 2026-03-05) addresses the event; the label does not assert causation.  
  _[ref: label_section:evd_940f52a429fa]_

## External evidence
- PMID 42403889, 2026-01-01: "Montelukast Prescription Prevalence and Impact on Clinical Outcomes Among Patients with Asthma: A Cross-Sectional Study in Saudi Arabia.".  
  _[ref: evidence:evd_023f5d82ea82]_
- PMID 41644790, 2026-01-01: "Respiratory drugs and psychiatric adverse events in children and adolescents: a pharmacovigilance study based on the FAERS database.".  
  _[ref: evidence:evd_042b647bd04c]_
- PMID 41208871, 2025-01-01: "Montelukast: risk of mental disorders vs. efficacy-a meta-analysis.".  
  _[ref: evidence:evd_841c51ab583c]_
- PMID 40553531, 2025-01-01: "Montelukast: A Scientific and Legal Review.".  
  _[ref: evidence:evd_92159f7bb201]_
- PMID 40491164, 2025-01-01: "Potentially Overlooked Risk for Neuropsychiatric Symptoms in Children: Montelukast Treatment.".  
  _[ref: evidence:evd_545b329464b1]_
- PMID 40413828, 2025-01-01: "Drug-related suicidal ideation in the K-12 population: a real-world pharmacovigilance study of the FDA adverse event reporting system (FAERS) database.".  
  _[ref: evidence:evd_587b1be41e53]_
- PMID 40211683, 2025-01-01: "Montelukast Induces Depressive-Like Behaviour in ICR Young Mice Through Oxidative Stress and Inflammatory Response.".  
  _[ref: evidence:evd_c24ad729e518]_
- PMID 40120471, 2025-01-01: "Comparative efficacy of intranasal mometasone furoate monotherapy or combination therapy with montelukast in pediatric adenoid hypertrophy: A systematic review and meta-analysis of randomized clinical trials.".  
  _[ref: evidence:evd_e710407d4fd5]_
- PMID 39912596, 2025-01-01: "Effects of Montelukast on Neuroinflammation in Parkinson's Disease: An Open Label Safety and Tolerability Trial with CSF Markers and [(11)C]PBR28 PET.".  
  _[ref: evidence:evd_a7e6996d0b96]_
- PMID 39836401, 2025-01-01: "Montelukast Use and the Risk of Neuropsychiatric Adverse Events in Children.".  
  _[ref: evidence:evd_718d0b3bdce2]_
- PMID 39171880, 2024-01-01: "[Modern approaches to rational combination pharmacotherapy of allergic rhinitis].".  
  _[ref: evidence:evd_874c96eee298]_
- PMID 38824963, 2024-01-01: "Association and mechanism of montelukast on depression: A combination of clinical and network pharmacology study.".  
  _[ref: evidence:evd_3a44c3a7cd64]_
- PMID 38663558, 2024-01-01: "Leukotriene-modifying agents may increase the risk of depression: A cross-sectional study.".  
  _[ref: evidence:evd_55ab6d84d0a5]_
- PMID 38094668, 2023-01-01: "The Impact of Montelukast's Black Box Warning on Pediatric Mental Health Adverse Event Reports.".  
  _[ref: evidence:evd_c23189676b54]_
- PMID 37957053, 2024-01-01: "Drug-induced psychiatric disorders: A pharmacovigilance update.".  
  _[ref: evidence:evd_8b21778b8b58]_
- PMID 37758273, 2023-01-01: "Neuropsychiatric events associated with montelukast in patients with asthma: a systematic review.".  
  _[ref: evidence:evd_d5a34822fdc8]_
- PMID 37628300, 2023-01-01: "Evaluation of Neuropsychiatric Effects of Montelukast-Levocetirizine Combination Therapy in Children with Asthma and Allergic Rhinitis.".  
  _[ref: evidence:evd_3488606a9b37]_
- PMID 37498493, 2023-01-01: "Evaluating the Association of Montelukast Use on Neuropsychiatry-Related Healthcare Utilization and Depression in COVID-19-Hospitalized Veterans: A Nationwide VA Observational Cohort Study.".  
  _[ref: evidence:evd_0f76bd9aa371]_
- PMID 36368225, 2023-01-01: "Montelukast and risk for antidepressant treatment failure.".  
  _[ref: evidence:evd_0224affacb1b]_
- PMID 36228771, 2022-01-01: "The mechanisms underlying montelukast's neuropsychiatric effects - new insights from a combined metabolic and multiomics approach.".  
  _[ref: evidence:evd_a6fe6ecf2310]_

## Conflicting evidence
- Sources are broadly consistent or incomplete; no direct contradiction detected, but see individual source limitations.  
  _[ref: analysis:ana_a7218b8378ad]_
- FAERS spontaneous reports: 100 case(s), 85 flagged serious (spontaneous reports cannot establish causation or rates).  
  _[ref: analysis:ana_a7218b8378ad]_
- Label section 'adverse_reactions' (effective 2026-03-05): describes the event; label does not assert causation.  
  _[ref: analysis:ana_a7218b8378ad]_
- Label section 'boxed_warning' (effective 2026-03-05): describes the event; label does not assert causation.  
  _[ref: analysis:ana_a7218b8378ad]_
- Label section 'contraindications' (effective 2026-03-05): describes the event; label does not assert causation.  
  _[ref: analysis:ana_a7218b8378ad]_
- Label section 'indications_and_usage' (effective 2026-03-05): describes the event; label does not assert causation.  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 36368225, 2023-01-01: "Montelukast and risk for antidepressant treatment failure.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 42403889, 2026-01-01: "Montelukast Prescription Prevalence and Impact on Clinical Outcomes Among Patients with Asthma: A Cross-Sectional Study in Saudi Arabia.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 41644790, 2026-01-01: "Respiratory drugs and psychiatric adverse events in children and adolescents: a pharmacovigilance study based on the FAERS database.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 37498493, 2023-01-01: "Evaluating the Association of Montelukast Use on Neuropsychiatry-Related Healthcare Utilization and Depression in COVID-19-Hospitalized Veterans: A Nationwide VA Observational Cohort Study.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 37628300, 2023-01-01: "Evaluation of Neuropsychiatric Effects of Montelukast-Levocetirizine Combination Therapy in Children with Asthma and Allergic Rhinitis.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 38824963, 2024-01-01: "Association and mechanism of montelukast on depression: A combination of clinical and network pharmacology study.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 40491164, 2025-01-01: "Potentially Overlooked Risk for Neuropsychiatric Symptoms in Children: Montelukast Treatment.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 38663558, 2024-01-01: "Leukotriene-modifying agents may increase the risk of depression: A cross-sectional study.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 40413828, 2025-01-01: "Drug-related suicidal ideation in the K-12 population: a real-world pharmacovigilance study of the FDA adverse event reporting system (FAERS) database." [reports a signal].  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 39836401, 2025-01-01: "Montelukast Use and the Risk of Neuropsychiatric Adverse Events in Children.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 41208871, 2025-01-01: "Montelukast: risk of mental disorders vs. efficacy-a meta-analysis.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 39171880, 2024-01-01: "[Modern approaches to rational combination pharmacotherapy of allergic rhinitis].".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 37957053, 2024-01-01: "Drug-induced psychiatric disorders: A pharmacovigilance update.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 40553531, 2025-01-01: "Montelukast: A Scientific and Legal Review.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 36228771, 2022-01-01: "The mechanisms underlying montelukast's neuropsychiatric effects - new insights from a combined metabolic and multiomics approach.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 39912596, 2025-01-01: "Effects of Montelukast on Neuroinflammation in Parkinson's Disease: An Open Label Safety and Tolerability Trial with CSF Markers and [(11)C]PBR28 PET.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 38094668, 2023-01-01: "The Impact of Montelukast's Black Box Warning on Pediatric Mental Health Adverse Event Reports.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 40211683, 2025-01-01: "Montelukast Induces Depressive-Like Behaviour in ICR Young Mice Through Oxidative Stress and Inflammatory Response.".  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 37758273, 2023-01-01: "Neuropsychiatric events associated with montelukast in patients with asthma: a systematic review." [reports a signal].  
  _[ref: analysis:ana_a7218b8378ad]_
- Literature PMID 40120471, 2025-01-01: "Comparative efficacy of intranasal mometasone furoate monotherapy or combination therapy with montelukast in pediatric adenoid hypertrophy: A systematic review and meta-analysis of randomized clinical trials.".  
  _[ref: analysis:ana_a7218b8378ad]_

## Limitations
- Spontaneous adverse-event reports cannot establish that the drug caused the event, and cannot be used to compute incidence or occurrence rates.
- Public reports may be incomplete, duplicated, or unverified.

## Unresolved questions
- Do the likely-duplicate groups represent the same case? (requires manual review)
- What is the clinical context of the serious cases (confounders, comorbidity)?

## Human-review considerations
- This memo is advisory. A human safety professional must review the individual serious cases and decide whether deeper evaluation is warranted.

## Source references
- evd_900cf94484ac: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-04
- evd_30d9bfc67bee: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-04
- evd_e5c4fb542785: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-04
- evd_940f52a429fa: openFDA/drug/label | query='openfda.generic_name:"montelukast" OR openfda.brand_name:"montelukast"' | retrieved 2026-09-04
- evd_023f5d82ea82: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_042b647bd04c: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_841c51ab583c: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_92159f7bb201: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_545b329464b1: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_587b1be41e53: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_c24ad729e518: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_e710407d4fd5: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_a7e6996d0b96: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_718d0b3bdce2: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_874c96eee298: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_3a44c3a7cd64: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_55ab6d84d0a5: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_c23189676b54: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_8b21778b8b58: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_d5a34822fdc8: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_3488606a9b37: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_0f76bd9aa371: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_0224affacb1b: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_a6fe6ecf2310: PubMed | query='montelukast depression' | retrieved 2026-09-04
- evd_02314a904de2: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"depression" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_0837368a0de2: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"depression" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_48659af220ea: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"depression" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_eb7a3211237c: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"depression" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
- evd_951b37609ad1: openFDA/drug/event | query='patient.drug.medicinalproduct:"montelukast" AND patient.reaction.reactionmeddrapt:"depression" AND receivedate:[20190101 TO 20211231]' | retrieved 2026-09-04
