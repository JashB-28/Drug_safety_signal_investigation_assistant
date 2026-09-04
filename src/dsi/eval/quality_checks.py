"""Deterministic quality checks over a produced memo.

Simple, exact checks --- no LLM judgment. These are the "simple quality checks"
the assessment asks for: citation completeness, unsupported claims, valid output
structure, and safety-boundary compliance.
"""

from __future__ import annotations

from dsi.domain.memo import Memo, MemoSectionKind, MemoValidationStatus
from dsi.memo.validator import validate_memo

REQUIRED_SECTIONS = set(MemoSectionKind)


def check_memo(memo: Memo) -> dict:
    report = validate_memo(memo)
    material = memo.material_claims()
    uncited = memo.uncited_material_claims()
    return {
        "material_claims": len(material),
        "uncited_material_claims": len(uncited),          # 0 == citation-complete
        "citation_completeness": round(1 - len(uncited) / len(material), 4) if material else 1.0,
        "unsupported_claims": len(report.violations),     # prohibited-pattern hits
        "output_schema_valid": isinstance(memo, Memo) and bool(memo.sections),
        "all_required_sections": {s.kind for s in memo.sections} == REQUIRED_SECTIONS,
        "safety_boundary_compliant": report.ok,
        "validation_status": memo.validation_status.value,
        "passed": (report.ok and not uncited
                   and memo.validation_status is MemoValidationStatus.PASSED),
    }
