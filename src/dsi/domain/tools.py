"""Typed request/response schemas for the three MCP tools.

Every tool call has a typed input and a typed, envelope-wrapped output. The
envelope (`ToolResult`) always carries the same operational metadata --- retries,
cache hit, latency, outcome --- so the metrics spine (Phase 1) can record a tool
call uniformly regardless of which tool ran, and so a failure is a *value* the
graph inspects, never an exception that crashes it.

The response payloads reuse the evidence models directly (an FAERS search returns
`AdverseEventReport`s), keeping one representation for each kind of record.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, model_validator

from dsi.domain.evidence import (
    AdverseEventReport,
    LabelSection,
    LabelSectionName,
    LiteratureReference,
)


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #
class FaersSearchRequest(BaseModel):
    """Search the openFDA adverse-event endpoint."""

    drug: str
    event: str | None = None
    date_start: date | None = None
    date_end: date | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    skip: int = Field(default=0, ge=0)


class LabelFetchRequest(BaseModel):
    """Fetch sections of the current public drug label."""

    drug: str
    sections: list[LabelSectionName] | None = Field(
        default=None, description="Specific sections to fetch; None = all supported sections."
    )


class LiteratureSearchRequest(BaseModel):
    """Search PubMed for external evidence (third source)."""

    query: str
    max_results: int = Field(default=20, ge=1, le=100)
    date_start: date | None = None
    date_end: date | None = None


# --------------------------------------------------------------------------- #
# Structured errors
# --------------------------------------------------------------------------- #
class ToolErrorCode(str, Enum):
    """A closed set of failure modes so the agent can branch on them deterministically."""

    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    RATE_LIMITED = "rate_limited"
    EMPTY_RESULT = "empty_result"
    MALFORMED_RESPONSE = "malformed_response"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"


class ToolError(BaseModel):
    """A structured error object returned inside a `ToolResult` (never raised)."""

    code: ToolErrorCode
    message: str
    retryable: bool = Field(description="Whether a bounded retry could plausibly succeed.")
    details: dict[str, str] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Response payloads
# --------------------------------------------------------------------------- #
class FaersSearchData(BaseModel):
    reports: list[AdverseEventReport] = Field(default_factory=list)
    total_matched: int = Field(default=0, description="Total matches reported by the source.")
    returned: int = Field(default=0, description="Count returned in this page.")


class LabelFetchData(BaseModel):
    drug_name: str
    sections: list[LabelSection] = Field(default_factory=list)
    spl_set_id: str | None = None
    spl_version: str | None = None


class LiteratureSearchData(BaseModel):
    references: list[LiteratureReference] = Field(default_factory=list)
    total: int = 0


# --------------------------------------------------------------------------- #
# Envelope
# --------------------------------------------------------------------------- #
DataT = TypeVar("DataT")


class ToolResult(BaseModel, Generic[DataT]):
    """Uniform success/failure envelope for every tool call.

    Exactly one of `data` / `error` is populated (enforced by the validator).
    The operational fields feed the metrics spine directly.
    """

    tool_name: str
    ok: bool
    data: DataT | None = None
    error: ToolError | None = None

    # Operational metadata (recorded by the metrics spine on every call).
    retry_count: int = 0
    cache_hit: bool = False
    latency_ms: float | None = None
    query: str | None = Field(default=None, description="Serialized request, for the audit trail.")

    @model_validator(mode="after")
    def _check_envelope_invariant(self) -> "ToolResult[DataT]":
        # Guard the invariant: ok<=>data present, not-ok<=>error present.
        if self.ok and self.data is None:
            raise ValueError("ToolResult.ok is True but data is None")
        if not self.ok and self.error is None:
            raise ValueError("ToolResult.ok is False but error is None")
        if self.ok and self.error is not None:
            raise ValueError("ToolResult has both data and error")
        return self
