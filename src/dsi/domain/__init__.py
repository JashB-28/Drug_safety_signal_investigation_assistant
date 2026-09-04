"""Domain models. Import the concrete schemas from here for convenience."""

from __future__ import annotations

from dsi.domain.analysis import (
    AggregationResult,
    AnalysisKind,
    AnalysisResult,
    ConflictFinding,
    DedupResult,
    DuplicateGroup,
    DuplicateGroupCertainty,
    MissingnessSummary,
    NormalizationResult,
    PeriodCount,
    SeriousnessSummary,
    TemporalComparison,
    make_provenance_fields,
)
from dsi.domain.evidence import (
    AdverseEventReport,
    DrugEntry,
    DrugRole,
    EvidencePayload,
    EvidenceRecord,
    LabelSection,
    LabelSectionName,
    LiteratureReference,
    ReactionEntry,
)
from dsi.domain.investigation import Investigation, ReviewPeriod
from dsi.domain.memo import (
    Citation,
    CitationKind,
    Claim,
    Memo,
    MemoSection,
    MemoSectionKind,
    MemoValidationStatus,
)
from dsi.domain.provenance import Provenance, SourceType
from dsi.domain.state import (
    ActionType,
    AgentState,
    Budget,
    Decision,
    InvestigationStatus,
)
from dsi.domain.tools import (
    FaersSearchData,
    FaersSearchRequest,
    LabelFetchData,
    LabelFetchRequest,
    LiteratureSearchData,
    LiteratureSearchRequest,
    ToolError,
    ToolErrorCode,
    ToolResult,
)

__all__ = [
    # provenance
    "Provenance", "SourceType",
    # evidence
    "AdverseEventReport", "DrugEntry", "DrugRole", "EvidencePayload", "EvidenceRecord",
    "LabelSection", "LabelSectionName", "LiteratureReference", "ReactionEntry",
    # investigation
    "Investigation", "ReviewPeriod",
    # tools
    "FaersSearchRequest", "FaersSearchData", "LabelFetchRequest", "LabelFetchData",
    "LiteratureSearchRequest", "LiteratureSearchData", "ToolError", "ToolErrorCode", "ToolResult",
    # analysis
    "AnalysisKind", "AnalysisResult", "NormalizationResult", "AggregationResult",
    "SeriousnessSummary", "MissingnessSummary", "DedupResult", "DuplicateGroup",
    "DuplicateGroupCertainty", "TemporalComparison", "PeriodCount", "ConflictFinding",
    "make_provenance_fields",
    # memo
    "Memo", "MemoSection", "MemoSectionKind", "Claim", "Citation", "CitationKind",
    "MemoValidationStatus",
    # state
    "AgentState", "Decision", "ActionType", "InvestigationStatus", "Budget",
]
