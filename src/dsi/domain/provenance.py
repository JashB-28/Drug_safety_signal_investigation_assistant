"""Provenance --- the retrieval metadata that must accompany every evidence record.

The assessment requires that each snapshotted record carry: retrieval timestamp,
the exact query used, the source, the source version/date, and a content hash.
The content hash lives on the `EvidenceRecord` itself (it hashes the payload);
everything else about *how/when the content was obtained* lives here.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    """Where a piece of evidence came from. `SYNTHETIC` flags clearly-labeled
    test/edge-case fixtures so they can never be mistaken for real FDA data."""

    FAERS = "faers"                 # openFDA drug adverse-event endpoint
    DRUG_LABEL = "drug_label"       # openFDA drug-label endpoint
    PUBMED = "pubmed"               # PubMed abstract / metadata
    FDA_COMMUNICATION = "fda_communication"  # e.g. an FDA safety communication
    SYNTHETIC = "synthetic"         # clearly-labeled synthetic record


class Provenance(BaseModel):
    """How and when a single evidence record was obtained."""

    model_config = ConfigDict(frozen=True)  # provenance never mutates after capture

    source_type: SourceType
    source: str = Field(description="Human-readable source id, e.g. 'openFDA/drug/event'.")
    query: str = Field(description="The exact query string used to retrieve this record.")
    retrieved_at: datetime = Field(description="UTC timestamp of retrieval.")
    source_version: str | None = Field(
        default=None,
        description="Source snapshot version, e.g. openFDA 'last_updated' or a FAERS quarter.",
    )
    source_date: date | None = Field(
        default=None,
        description="Effective date of the source content, e.g. a label's effective date.",
    )
    url: str | None = Field(default=None, description="Direct URL to the source, if any.")
    is_synthetic: bool = Field(
        default=False,
        description="True for clearly-labeled synthetic fixtures (edge cases, tool-failure tests).",
    )
