"""The investigation memo --- category (c): LLM-generated prose.

Prose is always rebuildable from evidence (a) + analysis (b). To make "every
material claim links to a source record, label section, or named calculation"
mechanically checkable, a memo is not free text: it is a list of sections, each
a list of `Claim`s, and each claim carries structured `Citation`s. The Phase-7
deterministic validator walks this structure to verify citation completeness and
to scan for prohibited (causal / incidence / treatment) language.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from dsi.common import new_id, utcnow


class MemoSectionKind(str, Enum):
    """The required memo sections (assessment Phase-7 list). Order is presentation order."""

    INVESTIGATION_QUESTION = "investigation_question"
    DRUG_AND_EVENT = "drug_and_event"
    REVIEW_PERIOD = "review_period"
    EXECUTIVE_SUMMARY = "executive_summary"
    ADVERSE_EVENT_EVIDENCE = "adverse_event_evidence"
    TEMPORAL_PATTERN = "temporal_pattern"
    SERIOUSNESS_MISSINGNESS = "seriousness_missingness"
    LABEL_EVIDENCE = "label_evidence"
    EXTERNAL_EVIDENCE = "external_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    LIMITATIONS = "limitations"
    UNRESOLVED_QUESTIONS = "unresolved_questions"
    HUMAN_REVIEW_CONSIDERATIONS = "human_review_considerations"
    SOURCE_REFERENCES = "source_references"


class CitationKind(str, Enum):
    EVIDENCE = "evidence"          # points at an EvidenceRecord.evidence_id
    ANALYSIS = "analysis"          # points at an AnalysisResult (by result_id or kind)
    LABEL_SECTION = "label_section"  # points at a specific label section evidence record


class Citation(BaseModel):
    """A pointer from a claim to the exact record or calculation that supports it."""

    kind: CitationKind
    ref_id: str = Field(description="evidence_id, analysis result_id, or label-section evidence_id.")
    detail: str | None = Field(default=None, description="Optional locator, e.g. a field name.")


class Claim(BaseModel):
    """A single assertion in the memo.

    `material` marks claims that make a factual assertion (a number, date, count,
    comparison, or source attribution) and therefore MUST be cited. Non-material
    connective prose (`material=False`) may be uncited. The validator enforces:
    material claim => at least one citation.
    """

    text: str
    material: bool = True
    citations: list[Citation] = Field(default_factory=list)
    quoted: bool = Field(
        default=False,
        description=(
            "True when the claim is verbatim text from a cited source (e.g. a paper "
            "title or a reported MedDRA reaction term). Such attributed data is exempt "
            "from the prohibited-CLAIM scan --- quoting a paper titled 'Drug-induced X' "
            "is not the SYSTEM asserting causation --- but still requires a citation."
        ),
    )


class MemoSection(BaseModel):
    """One section of the memo, plus the dependency fingerprint of what it used.

    `consumed_output_hashes` records the analysis/evidence outputs this section was
    built from, so the dependency graph can mark exactly this section stale when an
    upstream input changes (Scenario A) --- without rebuilding the whole memo.
    """

    section_id: str = Field(default_factory=lambda: new_id("sec"))
    kind: MemoSectionKind
    title: str
    claims: list[Claim] = Field(default_factory=list)
    consumed_output_hashes: list[str] = Field(default_factory=list)


class MemoValidationStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class Memo(BaseModel):
    """A complete investigation memo for one run of one investigation."""

    memo_id: str = Field(default_factory=lambda: new_id("memo"))
    investigation_id: str
    run_id: str
    model_tag: str = Field(description="Pinned model that generated the prose, for reproducibility.")
    sections: list[MemoSection] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utcnow)
    validation_status: MemoValidationStatus = MemoValidationStatus.PENDING

    def material_claims(self) -> list[Claim]:
        """All claims across sections that require citations."""
        return [c for s in self.sections for c in s.claims if c.material]

    def uncited_material_claims(self) -> list[Claim]:
        """Material claims missing any citation --- the validator fails the run if non-empty."""
        return [c for c in self.material_claims() if not c.citations]
