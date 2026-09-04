# Research Brief — FDE Discovery

Treating the assessment as an initial customer request, this brief records what the
early signal-investigation workflow actually is, who it serves, where it hurts, the
drug–event pair chosen, and — explicitly — which statements are researched fact,
which are assumptions, and what I'd ask a real customer next.

## 1. Primary user, the decision, and the cost of getting it wrong

**Primary user:** a **pharmacovigilance (drug-safety) analyst** on a manufacturer's
or a regulator's safety team. Day to day they work a queue of potential *signals* —
drug–event pairs flagged for review.

**The decision they're trying to make (early triage):** *Is there enough here to
justify deeper human investigation?* Concretely: are reports of this event for this
drug notable, is the event already described in the product label, and are the data
strong enough to escalate — or is it noise, duplication, or already-known?

**Cost of a poor investigation (both directions):**
- **False negative** — dismissing a real signal delays label changes or warnings;
  patients stay exposed to an under-communicated risk. (Montelukast's
  neuropsychiatric signal took from 2008 warnings to a 2020 boxed warning.)
- **False positive** — escalating noise wastes scarce expert time, and, if it leaks,
  can cause unwarranted alarm or inappropriate discontinuation of a useful drug.
- **Evidence indiscipline** — a conclusion that can't be traced to its source/query/
  date is unusable in a regulated setting and can't survive audit.

## 2. Workflow bottlenecks, data-quality problems, and safety risks

**Bottlenecks.** The evidence is spread across systems (FAERS, the current label,
the literature) and must be manually reconciled; a large fraction of an analyst's
time is spent *cleaning and de-duplicating* rather than reasoning.

**Data-quality problems (the core difficulty — FDA states these plainly):**
- Spontaneous reports are **incomplete, duplicated, and unverified**; many lack the
  detail needed to assess a relationship.
- **Product names vary** (brand vs. generic vs. generic-plus-salt).
- **One case can have several follow-up versions** (a case id with versions).
- **Several drugs and reactions co-occur** in one report.
- Critically, spontaneous reports **cannot establish causality or occurrence rates**.

**Safety risks specific to an AI assistant here:** hallucinated counts or citations;
silently computing an "incidence" from spontaneous reports; forcing conflicting
evidence into a single confident answer; or treating retrieved text as instructions.
The architecture is built to make each of these structurally hard (deterministic
numbers, a citation requirement, explicit conflict preservation, delimited untrusted
data, and a deterministic output validator).

## 3. Chosen drug–event pair (and why)

**Montelukast (Singulair) → serious neuropsychiatric events**, review period
2019–2021. Two hard requirements drove the choice:

- **A real, dated label change** (so the "evidence changed after the first run"
  scenario is authentic): the FDA required a **Boxed Warning on 2020-03-04**,
  escalating from earlier warnings communicated in 2008–2009.
- **A genuine evidence conflict** (so the "conflicting evidence" scenario is real,
  not contrived): a strong FAERS spontaneous-report signal (including reports of
  completed suicide) sits alongside an FDA-cited observational/Sentinel study that
  found **no increased risk versus inhaled corticosteroids**, while the FDA notes
  most reports lacked the detail to evaluate a relationship.

The review period straddles the 2020 boxed warning so both the label-change and the
temporal-comparison work are meaningful. (It is distinct from the PDF's
semaglutide/pancreatitis illustration, as instructed.)

## 4. Facts vs. assumptions vs. questions for the customer

**Researched facts (sourced below):** the 2020-03-04 boxed warning and its 2008–2009
predecessors; the FDA's stance that FAERS data are incomplete/duplicated/unverified
and cannot establish causality or rates; the existence of an observational study
reporting no increased risk vs. ICS; that openFDA `safetyreportid` is the
case-level id (CASEID) with `safetyreportversion` as the version.

**Assumptions I made (documented, smallest-defensible):**
- Review period 2019–2021 (to straddle the label change).
- "Material claim" = any sentence with a number, count, date, comparison, or source
  attribution → must be cited.
- Event matching uses openFDA's MedDRA reaction terms; a specific term is expected.
- Likely-duplicate grouping uses a sex/age/reactions/date/country fingerprint; it is
  flagged for human review, never auto-merged.

**Questions I'd ask a real customer next:**
- What is the escalation threshold — what makes a signal "worth deeper review" for
  you, and what's the tolerance for false positives vs. negatives?
- Which coding dictionary and version (MedDRA level: PT vs. HLT/SOC) should event
  matching use, and do you want term expansion (e.g. an SMQ) applied automatically?
- Should the assistant integrate into an existing safety database (Argus/Vault) as a
  draft assessment, rather than emit a standalone memo?
- What is the authoritative de-duplication rule in your environment (FAERS quarterly
  ASCII `caseid`/`primaryid`, or openFDA)?
- What audit/retention and e-signature requirements must the output satisfy?

## 5. Sources (≥3 credible; ≥2 primary/regulatory)

1. **FDA Drug Safety Communication — montelukast boxed warning (2020-03-04)** *(primary/regulatory)*.
   Confirms the dated label change, the 2008–2009 predecessors, the named events, the
   observational study finding no increased risk vs. ICS, and the report-incompleteness caveat.
   https://www.fda.gov/drugs/drug-safety-communications/fda-requires-boxed-warning-about-serious-mental-health-side-effects-asthma-and-allergy-drug
2. **openFDA drug adverse-event (FAERS) & drug-label APIs** *(primary/regulatory data source)*.
   The core public evidence endpoints used by the tools.
   https://open.fda.gov/apis/drug/event/ · https://open.fda.gov/apis/drug/label/
3. **FDA FAERS Public Dashboard — data limitations** *(primary/regulatory)*.
   FDA's explicit statement that public adverse-event reports may be incomplete,
   duplicated, or unverified and cannot establish causality or occurrence rates.
   https://www.fda.gov/drugs/questions-and-answers-fdas-adverse-event-reporting-system-faers/fda-adverse-event-reporting-system-faers-public-dashboard
4. **PubMed / peer-reviewed observational literature** *(secondary)* — the discordant
   "no increased risk vs. ICS" evidence used in the conflict scenario; searched via
   the PubMed E-utilities. https://pubmed.ncbi.nlm.nih.gov/

*Regulatory dates in this brief were verified against the FDA primary source above
during development.*
