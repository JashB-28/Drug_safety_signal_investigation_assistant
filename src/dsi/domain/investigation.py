"""The investigation --- the top-level input the analyst poses.

Input (per the assessment): a marketed drug, a suspected adverse event, and a
review period. We keep the analyst's *raw* strings distinct from any normalized
forms (normalization is a deterministic Phase-5 step, and its output is stored
separately so the original request is never lost).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from dsi.common import new_id, utcnow


class ReviewPeriod(BaseModel):
    """A closed date interval [start, end] for the reports under review."""

    start: date
    end: date

    @model_validator(mode="after")
    def _check_order(self) -> "ReviewPeriod":
        if self.end < self.start:
            raise ValueError(f"review period end ({self.end}) precedes start ({self.start})")
        return self

    def contains(self, d: date) -> bool:
        return self.start <= d <= self.end


class Investigation(BaseModel):
    """One investigation of a drug + suspected adverse-event pair over a period.

    The `drug` and `event` here are the analyst's exact words. Normalized product
    names / MedDRA-style event terms are produced by deterministic analysis and
    stored as analysis results, not written back over these fields.
    """

    investigation_id: str = Field(default_factory=lambda: new_id("inv"))
    drug: str = Field(description="Marketed drug as entered by the analyst (brand or generic).")
    event: str = Field(description="Suspected adverse event as entered by the analyst.")
    review_period: ReviewPeriod
    question: str | None = Field(
        default=None,
        description="Optional free-text investigation question; a default is derived if absent.",
    )
    created_at: datetime = Field(default_factory=utcnow)

    def default_question(self) -> str:
        """A neutral, non-leading phrasing of the investigation question."""
        return (
            f"For {self.drug}, what does public evidence show about reports of "
            f"{self.event} during {self.review_period.start} to {self.review_period.end}, "
            f"and is the evidence sufficient to warrant deeper human review?"
        )
