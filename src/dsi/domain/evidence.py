"""Raw evidence records --- category (a) in the three-way separation.

These are faithful, typed representations of what the tools retrieved. They are
the source of truth: the LLM may read them but may never modify them, and every
material claim in the memo must trace back to one of these records.

Design notes:
  * Missingness is modeled as `None`. A FAERS report with no patient age carries
    `patient_age=None`; the deterministic missingness analysis (Phase 5) counts
    these. We never invent a value to fill a gap.
  * Each record's `content_hash` is computed over the *payload only* (not the
    provenance/timestamp), so identical content re-fetched later hashes the same.
  * The three payload types are a discriminated union keyed on `kind`, so a
    mixed list of evidence round-trips through JSON without ambiguity.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from dsi.common import new_id, utcnow
from dsi.hashing import canonical_hash
from dsi.domain.provenance import Provenance


# --------------------------------------------------------------------------- #
# FAERS adverse-event report
# --------------------------------------------------------------------------- #
class DrugRole(str, Enum):
    """openFDA `drugcharacterization`: the role a drug played in a report."""

    PRIMARY_SUSPECT = "primary_suspect"
    SECONDARY_SUSPECT = "secondary_suspect"
    CONCOMITANT = "concomitant"
    INTERACTING = "interacting"
    UNKNOWN = "unknown"


class DrugEntry(BaseModel):
    """One drug named within an adverse-event report."""

    name: str = Field(description="Reported product name (brand or generic, as filed).")
    role: DrugRole = DrugRole.UNKNOWN
    indication: str | None = None


class ReactionEntry(BaseModel):
    """One reaction (MedDRA preferred term) named within a report."""

    term: str = Field(description="Reaction term as reported (ideally a MedDRA PT).")
    outcome: str | None = Field(default=None, description="Reported reaction outcome, if any.")


class AdverseEventReport(BaseModel):
    """A single FAERS spontaneous report.

    `report_id` + `report_version` together identify a specific version of a
    case; follow-up versions share `report_id` with a higher `report_version`
    (used by the duplicate/version-resolution analysis in Phase 5).
    """

    kind: Literal["adverse_event_report"] = "adverse_event_report"

    report_id: str = Field(description="FAERS safetyreportid.")
    report_version: int | None = Field(
        default=None, description="FAERS safetyreportversion; higher = later follow-up."
    )
    receive_date: date | None = None
    receipt_date: date | None = None

    # Seriousness: overall flag plus the specific criteria. None == not reported.
    serious: bool | None = None
    serious_death: bool | None = None
    serious_hospitalization: bool | None = None
    serious_life_threatening: bool | None = None
    serious_disabling: bool | None = None
    serious_congenital_anomaly: bool | None = None
    serious_other: bool | None = None

    # Patient fields --- frequently missing; None models that honestly.
    patient_age: float | None = None
    patient_age_unit: str | None = None
    patient_sex: str | None = None

    reporter_qualification: str | None = None
    occur_country: str | None = None

    drugs: list[DrugEntry] = Field(default_factory=list)
    reactions: list[ReactionEntry] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Drug-label section
# --------------------------------------------------------------------------- #
class LabelSectionName(str, Enum):
    """The label sections this system inspects. Extend as needed."""

    BOXED_WARNING = "boxed_warning"
    WARNINGS_AND_PRECAUTIONS = "warnings_and_precautions"
    ADVERSE_REACTIONS = "adverse_reactions"
    INDICATIONS_AND_USAGE = "indications_and_usage"
    CONTRAINDICATIONS = "contraindications"
    OTHER = "other"


class LabelSection(BaseModel):
    """One section of a current public product label."""

    kind: Literal["label_section"] = "label_section"

    drug_name: str
    section: LabelSectionName
    text: str
    # Label version identifiers let us detect a label change (Scenario A).
    spl_set_id: str | None = Field(default=None, description="SPL set id (stable across versions).")
    spl_version: str | None = Field(default=None, description="SPL version for this specific label.")
    effective_date: date | None = None


# --------------------------------------------------------------------------- #
# External literature reference
# --------------------------------------------------------------------------- #
class LiteratureReference(BaseModel):
    """A PubMed abstract / citation used as the third evidence source."""

    kind: Literal["literature_reference"] = "literature_reference"

    pmid: str
    title: str
    abstract: str | None = None
    journal: str | None = None
    authors: list[str] = Field(default_factory=list)
    pub_date: date | None = None
    doi: str | None = None


# Discriminated union over the payload types.
EvidencePayload = Annotated[
    Union[AdverseEventReport, LabelSection, LiteratureReference],
    Field(discriminator="kind"),
]


# --------------------------------------------------------------------------- #
# Evidence record wrapper
# --------------------------------------------------------------------------- #
class EvidenceRecord(BaseModel):
    """A payload plus its provenance and content hash --- the unit stored, hashed,
    and cited. Construct via `EvidenceRecord.create` so the hash and id are always
    computed consistently."""

    evidence_id: str
    payload: EvidencePayload
    provenance: Provenance
    content_hash: str = Field(description="SHA-256 of the canonical payload (content only).")
    created_at: datetime

    @classmethod
    def create(cls, payload: EvidencePayload, provenance: Provenance) -> "EvidenceRecord":
        """Build a record, deterministically hashing the payload content."""
        return cls(
            evidence_id=new_id("evd"),
            payload=payload,
            provenance=provenance,
            content_hash=canonical_hash(payload),
            created_at=utcnow(),
        )

    def recompute_hash(self) -> str:
        """Return the hash the payload *should* have --- used to detect tampering
        or drift between stored `content_hash` and actual payload content."""
        return canonical_hash(self.payload)
