"""Tests for the investigation input model and the tool request/response envelope."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from dsi.domain.investigation import Investigation, ReviewPeriod
from dsi.domain.tools import (
    FaersSearchData,
    FaersSearchRequest,
    ToolError,
    ToolErrorCode,
    ToolResult,
)
from dsi.domain.evidence import AdverseEventReport


# --- investigation --------------------------------------------------------- #
def test_review_period_rejects_reversed_dates():
    with pytest.raises(ValidationError):
        ReviewPeriod(start=date(2021, 1, 1), end=date(2019, 1, 1))


def test_review_period_contains():
    rp = ReviewPeriod(start=date(2019, 1, 1), end=date(2021, 12, 31))
    assert rp.contains(date(2020, 6, 1))
    assert not rp.contains(date(2018, 12, 31))


def test_investigation_default_question_mentions_pair_and_period():
    inv = Investigation(
        drug="montelukast",
        event="neuropsychiatric events",
        review_period=ReviewPeriod(start=date(2019, 1, 1), end=date(2021, 12, 31)),
    )
    q = inv.default_question()
    assert "montelukast" in q and "neuropsychiatric events" in q
    assert "2019-01-01" in q and "2021-12-31" in q
    assert inv.investigation_id.startswith("inv_")


# --- tool requests --------------------------------------------------------- #
def test_faers_request_bounds_limit():
    with pytest.raises(ValidationError):
        FaersSearchRequest(drug="montelukast", limit=0)
    with pytest.raises(ValidationError):
        FaersSearchRequest(drug="montelukast", limit=5000)
    ok = FaersSearchRequest(drug="montelukast", limit=100)
    assert ok.skip == 0


# --- tool result envelope invariants --------------------------------------- #
def test_tool_result_ok_requires_data():
    data = FaersSearchData(reports=[AdverseEventReport(report_id="1")], total_matched=1, returned=1)
    res = ToolResult[FaersSearchData](tool_name="faers_search", ok=True, data=data)
    assert res.data.returned == 1
    assert res.error is None


def test_tool_result_ok_without_data_raises():
    with pytest.raises(ValidationError):
        ToolResult[FaersSearchData](tool_name="faers_search", ok=True, data=None)


def test_tool_result_error_requires_error_object():
    with pytest.raises(ValidationError):
        ToolResult[FaersSearchData](tool_name="faers_search", ok=False, error=None)


def test_tool_result_error_path_carries_structured_error():
    err = ToolError(code=ToolErrorCode.TIMEOUT, message="deadline exceeded", retryable=True)
    res = ToolResult[FaersSearchData](
        tool_name="faers_search", ok=False, error=err, retry_count=2
    )
    assert res.error.code is ToolErrorCode.TIMEOUT
    assert res.error.retryable is True
    assert res.retry_count == 2


def test_tool_result_cannot_have_both_data_and_error():
    err = ToolError(code=ToolErrorCode.UNKNOWN, message="x", retryable=False)
    data = FaersSearchData()
    with pytest.raises(ValidationError):
        ToolResult[FaersSearchData](tool_name="t", ok=True, data=data, error=err)
