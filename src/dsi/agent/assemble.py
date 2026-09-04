"""Assemble memo inputs from evidence records + a dict of analysis results.

Shared by the agent's finalize node and Scenario A's selective recompute, so the
two never diverge on how records map into a memo.
"""

from __future__ import annotations

from dsi.agent.context_builder import select_serious_cases
from dsi.analysis.dedup import collapse_to_latest_versions
from dsi.domain.evidence import (
    AdverseEventReport,
    EvidenceRecord,
    LabelSection,
    LiteratureReference,
)
from dsi.domain.investigation import Investigation
from dsi.domain.memo import Memo
from dsi.memo.builder import MemoInputs, build_memo


def build_memo_from_parts(
    *,
    investigation: Investigation,
    run_id: str,
    model_tag: str,
    analyses: dict,
    records: list[EvidenceRecord],
    conflict,
    framing: str,
    sufficiency_reasons: list[str],
    top_n_serious: int = 5,
) -> Memo:
    collapsed = collapse_to_latest_versions(records)
    ae_records = [r for r in collapsed if isinstance(r.payload, AdverseEventReport)]
    serious_payloads = select_serious_cases([r.payload for r in ae_records], top_n_serious)
    serious_ids = {p.report_id for p in serious_payloads}
    serious_records = [r for r in ae_records if r.payload.report_id in serious_ids]
    label_records = [r for r in records if isinstance(r.payload, LabelSection)]
    literature_records = [r for r in records if isinstance(r.payload, LiteratureReference)]

    inp = MemoInputs(
        investigation=investigation, run_id=run_id, model_tag=model_tag,
        normalization=analyses["normalization"], sufficiency_reasons=sufficiency_reasons,
        framing_text=framing,
        aggregation=analyses.get("aggregation"), seriousness=analyses.get("seriousness"),
        missingness=analyses.get("missingness"), dedup=analyses.get("dedup"),
        temporal=analyses.get("temporal"),
        label_records=label_records, literature_records=literature_records,
        serious_case_records=serious_records, conflict=conflict)
    return build_memo(inp)
