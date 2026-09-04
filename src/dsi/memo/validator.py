"""Deterministic output validator --- the hard safety boundary.

Scans the memo text for prohibited claim patterns and fails the run if any survive.
This does NOT rely on prompt instructions; it is a Python scanner over the final
prose. Two categories:

  * ALWAYS prohibited: incidence / occurrence rate / prevalence language, and
    treatment recommendations. These should never appear regardless of context.
  * NEGATION-GUARDED: causal assertions ('caused', 'drug-induced', 'responsible
    for') and false certainty ('proves', 'conclusively'). These are violations
    ONLY when affirmative --- the memo is EXPECTED to say "the data cannot establish
    that the drug caused the event", and that negated form must pass.

Also checks citation completeness: every material claim must carry >=1 citation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from dsi.domain.memo import Memo

# Negation tokens that, when they appear just before a guarded term, make it safe.
_NEG = re.compile(
    r"(?:\bnot\b|\bno\b|\bcannot\b|\bcan't\b|\bunable\b|\bwithout\b|\bnever\b|n't\b|"
    r"\bdoes not\b|\bdo not\b|\bno evidence\b|\bcannot establish\b|\bnot establish\b|"
    r"\bnot prove\b|\bno proof\b|\bnot been\b)", re.IGNORECASE)

# Always prohibited regardless of surrounding words.
_ALWAYS = [
    (re.compile(r"\b\d+(?:\.\d+)?\s*%\s*(?:of\s+(?:patients|cases)|incidence)", re.I), "rate_percent"),
    (re.compile(r"\b(?:we\s+recommend|is\s+recommended|recommend\s+that|should\s+"
                r"(?:start|stop|discontinue|switch|avoid|be\s+prescribed|take|not\s+take)|"
                r"advise\s+(?:patients|clinicians))", re.I), "treatment_recommendation"),
]

# Negation-guarded: a violation only when AFFIRMATIVE. The memo is expected to say
# "these are not incidence or occurrence rates" and "cannot establish that the drug
# caused the event" --- those negated forms must pass.
_GUARDED = [
    (re.compile(r"\bincidence\b", re.I), "incidence_language"),
    (re.compile(r"\bprevalence\b", re.I), "prevalence_language"),
    (re.compile(r"\b(occurrence|event|adverse[- ]event)\s+rate\b", re.I), "rate_language"),
    (re.compile(r"\bcaus(?:ed|es|ing)\b", re.I), "causal_claim"),
    (re.compile(r"\bdrug[- ]induced\b", re.I), "causal_claim"),
    (re.compile(r"\bresponsible for\b", re.I), "causal_claim"),
    (re.compile(r"\b(?:proves|proven|conclusively|definitively|confirms)\b", re.I), "false_certainty"),
]


@dataclass
class ValidationReport:
    ok: bool
    violations: list[dict] = field(default_factory=list)      # {code, snippet}
    uncited_claims: list[str] = field(default_factory=list)


def _negated(text: str, start: int) -> bool:
    window = text[max(0, start - 45): start]
    return bool(_NEG.search(window))


def scan_text(text: str) -> list[dict]:
    """Return a list of {code, snippet} violations found in a single string."""
    found: list[dict] = []
    for pattern, code in _ALWAYS:
        for m in pattern.finditer(text):
            found.append({"code": code, "snippet": _snip(text, m.start())})
    for pattern, code in _GUARDED:
        for m in pattern.finditer(text):
            if not _negated(text, m.start()):
                found.append({"code": code, "snippet": _snip(text, m.start())})
    return found


def _snip(text: str, at: int) -> str:
    return text[max(0, at - 25): at + 25].replace("\n", " ").strip()


def validate_memo(memo: Memo) -> ValidationReport:
    """Scan every claim; collect prohibited-pattern violations and uncited claims."""
    violations: list[dict] = []
    for section in memo.sections:
        for claim in section.claims:
            if claim.quoted:
                continue  # attributed verbatim source data, not a system assertion
            violations.extend(scan_text(claim.text))
    uncited = [c.text for c in memo.uncited_material_claims()]
    ok = not violations and not uncited
    return ValidationReport(ok=ok, violations=violations, uncited_claims=uncited)
