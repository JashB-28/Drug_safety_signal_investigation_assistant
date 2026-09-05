"""The pinned evaluation dataset.

CLEARLY-LABELED SYNTHETIC DATA. These openFDA/PubMed-shaped payloads are the fixed
snapshot the evaluation runs against, so the eval is fully reproducible offline. The
pipeline is byte-for-byte identical when the cache is instead seeded from real
openFDA/PubMed snapshots; only this module would be swapped.

Snapshot metadata (recorded on every seeded record's provenance):
  * snapshot date, exact query, source, and a content hash (via the cache).
"""

from __future__ import annotations

from datetime import date

from dsi.domain.investigation import Investigation, ReviewPeriod

SNAPSHOT_DATE = date(2026, 9, 3)
SNAPSHOT_LABEL = "synthetic-eval-v1"

EVAL_INVESTIGATION = Investigation(
    investigation_id="inv_eval_montelukast",
    drug="montelukast",
    event="neuropsychiatric events",
    review_period=ReviewPeriod(start=date(2019, 1, 1), end=date(2021, 12, 31)),
)

# For the REAL-data snapshot eval, the event must be a specific openFDA/MedDRA reaction
# term ("depression"), so a live FAERS query actually returns reports. `dsi snapshot`
# captures this pair once; the eval then replays it offline. See dsi.eval.snapshot.
REAL_EVAL_INVESTIGATION = Investigation(
    investigation_id="inv_eval_real_montelukast",
    drug="montelukast",
    event="depression",
    review_period=ReviewPeriod(start=date(2019, 1, 1), end=date(2021, 12, 31)),
)


def _report(rid, version, year, month, serious, death=False, sex=None, age=None,
            reactions=("Depression",), country="US"):
    r = {
        "safetyreportid": rid, "safetyreportversion": str(version),
        "receivedate": f"{year}{month:02d}15",
        "serious": "1" if serious else "2",
        "patient": {
            "drug": [{"medicinalproduct": "SINGULAIR", "drugcharacterization": "1",
                      "drugindication": "ASTHMA"}],
            "reaction": [{"reactionmeddrapt": t} for t in reactions],
        },
        "primarysource": {"qualification": "1"}, "occurcountry": country,
    }
    if death:
        r["seriousnessdeath"] = "1"
    if sex is not None:
        r["patient"]["patientsex"] = sex
    if age is not None:
        r["patient"]["patientonsetage"] = str(age)
        r["patient"]["patientonsetageunit"] = "801"
    return r


def faers_payload() -> dict:
    """~8 records: seriousness mix, a version chain, a likely-duplicate pair, and
    varying missingness --- enough for meaningful aggregation/dedup/temporal."""
    reports = [
        _report("EV-001", 1, 2019, 3, True, death=True, sex="2", age=15,
                reactions=["Depression", "Suicidal ideation"]),
        _report("EV-002", 1, 2019, 7, False, sex="1", age=42, reactions=["Insomnia"]),
        _report("EV-003", 1, 2020, 2, True, sex="2", age=9, reactions=["Aggression"]),
        _report("EV-004", 1, 2020, 6, True, death=True, reactions=["Suicidal ideation"]),  # missing age/sex
        _report("EV-004", 2, 2020, 6, True, death=True, sex="1", age=17,
                reactions=["Suicidal ideation"]),  # follow-up version of EV-004
        _report("EV-005", 1, 2020, 9, False, sex="2", age=33, reactions=["Anxiety"]),
        # EV-006 and EV-007: different ids, same fingerprint -> LIKELY duplicate
        _report("EV-006", 1, 2021, 4, True, sex="2", age=28, reactions=["Depression"]),
        _report("EV-007", 1, 2021, 4, True, sex="2", age=28, reactions=["Depression"]),
    ]
    return {"meta": {"results": {"total": len(reports)}}, "results": reports}


def label_payload() -> dict:
    return {"meta": {"results": {"total": 1}}, "results": [{
        "boxed_warning": ["WARNING: SERIOUS NEUROPSYCHIATRIC EVENTS. Reported events include "
                          "depression, suicidal thoughts and actions, aggression."],
        "warnings_and_precautions": ["Neuropsychiatric events have been reported in patients "
                                     "taking montelukast."],
        "adverse_reactions": ["Headache; neuropsychiatric events."],
        "effective_time": "20200304", "version": "7",
        "openfda": {"spl_set_id": ["eval-set-id"], "generic_name": ["MONTELUKAST SODIUM"],
                    "brand_name": ["SINGULAIR"]}}]}


def esearch_payload() -> dict:
    return {"esearchresult": {"idlist": ["30000001", "30000002", "30000003"]}}


def esummary_payload() -> dict:
    return {"result": {
        "uids": ["30000001", "30000002", "30000003"],
        "30000001": {"title": "No increased risk of neuropsychiatric events with montelukast "
                              "versus inhaled corticosteroids", "fulljournalname": "J Allergy Clin Immunol",
                     "pubdate": "2019 May", "authors": [{"name": "Smith J"}],
                     "articleids": [{"idtype": "doi", "value": "10.1000/eval1"}]},
        "30000002": {"title": "Case series: montelukast and suicidality in adolescents",
                     "fulljournalname": "Pharmacoepidemiology", "pubdate": "2021", "authors": []},
        "30000003": {"title": "Montelukast neuropsychiatric adverse events: a disproportionality "
                              "analysis", "fulljournalname": "Drug Safety", "pubdate": "2020", "authors": []}}}
