"""Drug/product and event normalization.

Public adverse-event data is messy: the same drug appears as a brand, a generic,
or a generic-plus-salt ('MONTELUKAST SODIUM'), and an analyst's event phrase
('neuropsychiatric events') maps to many specific reaction terms. Normalization
produces the expanded term sets used to query and to match, WITHOUT overwriting
the analyst's original words (those stay on the Investigation).

Deterministic and table-driven. The synonym tables are intentionally small and
explicit for the montelukast/neuropsychiatric pair; they are the obvious place to
extend for another pair.
"""

from __future__ import annotations

from dsi.domain.analysis import NormalizationResult, make_provenance_fields

# Salt/ester suffixes stripped from a generic name to get its canonical base.
_SALT_SUFFIXES = [
    "sodium", "hydrochloride", "hcl", "sulfate", "sulphate", "potassium",
    "calcium", "maleate", "mesylate", "besylate", "acetate", "phosphate",
]

# Brand <-> generic synonym clusters. Each key maps to the full cluster.
_DRUG_SYNONYMS: dict[str, set[str]] = {
    "montelukast": {"montelukast", "singulair"},
    "singulair": {"montelukast", "singulair"},
}

# Analyst event phrase -> specific reaction terms (MedDRA-style preferred terms).
_EVENT_SYNONYMS: dict[str, list[str]] = {
    "neuropsychiatric events": [
        "depression", "suicidal ideation", "suicidal behaviour", "completed suicide",
        "aggression", "agitation", "anxiety", "insomnia", "abnormal dreams",
        "hallucination", "irritability",
    ],
    "neuropsychiatric": [
        "depression", "suicidal ideation", "aggression", "anxiety", "insomnia",
    ],
}


def canonical_drug(raw: str) -> str:
    """Lowercase, trim, and drop a trailing salt word -> canonical base name."""
    tokens = raw.strip().lower().split()
    if len(tokens) > 1 and tokens[-1] in _SALT_SUFFIXES:
        tokens = tokens[:-1]
    return " ".join(tokens)


def expand_drug(raw: str) -> list[str]:
    """Canonical base plus any known brand/generic synonyms (sorted, de-duplicated)."""
    base = canonical_drug(raw)
    cluster = _DRUG_SYNONYMS.get(base, {base})
    return sorted(cluster)


def expand_event(raw: str) -> list[str]:
    """Expand an event phrase to specific reaction terms; falls back to the phrase."""
    key = raw.strip().lower()
    if key in _EVENT_SYNONYMS:
        return list(_EVENT_SYNONYMS[key])
    return [key]


def normalize(raw_drug: str, raw_event: str, investigation_id: str) -> NormalizationResult:
    """Produce a NormalizationResult. Query-driven, so it consumes no evidence
    (its `consumed_evidence_hashes` is empty but its output is still hashed)."""
    drugs = expand_drug(raw_drug)
    events = expand_event(raw_event)
    body = {
        "raw_drug": raw_drug, "normalized_drug_names": drugs,
        "raw_event": raw_event, "normalized_event_terms": events,
    }
    prov = make_provenance_fields([], body)
    return NormalizationResult(investigation_id=investigation_id, **body, **prov)
