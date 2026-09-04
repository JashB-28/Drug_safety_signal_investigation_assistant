"""`dsi investigate` --- run the agent on a drug + suspected event + review period
supplied by the user, fetching evidence LIVE from openFDA/PubMed and caching it.

This is the command that takes the assessment's input triple from the command line.
Unlike `dsi eval` (pinned + offline), this one touches the network: the first run of
a pair fetches from the public APIs (no key needed) and snapshots the responses into
`data/db/dsi.sqlite`, so re-running the same pair is served from cache.

Note on the event term: openFDA matches the reaction against MedDRA preferred terms.
A specific term ("depression", "suicidal ideation") finds reports; a vague phrase
may match nothing, in which case the memo honestly reports insufficient evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dsi.agent.graph import RunContext, run_investigation
from dsi.agent.llm import OllamaClient
from dsi.config import get_settings
from dsi.domain.investigation import Investigation, ReviewPeriod
from dsi.mcp_server.server import ToolClients
from dsi.memo.render import render_memo
from dsi.persistence.db import Database
from dsi.trace.models import TraceKind


@dataclass
class InvestigateResult:
    status: str
    memo_path: Path
    sections: int
    uncited_material_claims: int
    validation: str
    model_tokens: int
    tool_calls: int
    cache_hits: int
    evidence_records: int


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")[:40]


def investigate(drug: str, event: str, start: date, end: date,
                out_dir: str | Path = "data/outputs") -> InvestigateResult:
    settings = get_settings()
    db = Database.create(settings.db_path)          # persistent DB -> cache survives runs
    inv = Investigation(drug=drug, event=event,
                        review_period=ReviewPeriod(start=start, end=end))
    ctx = RunContext(
        db=db,
        llm=OllamaClient(settings.model_tag, settings.ollama_host),
        tool_clients=ToolClients.from_settings(settings),   # real, LIVE openFDA/PubMed
    )
    result = run_investigation(ctx, inv)
    memo = ctx.memos.get_for_run(inv.investigation_id, result.state.run_id)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    memo_path = out / f"memo_{_slug(drug)}_{_slug(event)}.md"
    memo_path.write_text(render_memo(memo), encoding="utf-8")

    events = ctx.spine.events_for(inv.investigation_id, result.state.run_id)
    model = [e for e in events if e.kind is TraceKind.MODEL_CALL]
    tool = [e for e in events if e.kind is TraceKind.TOOL_CALL]
    return InvestigateResult(
        status=result.state.status.value,
        memo_path=memo_path,
        sections=len(memo.sections),
        uncited_material_claims=len(memo.uncited_material_claims()),
        validation=memo.validation_status.value,
        model_tokens=sum(e.tokens_total or 0 for e in model),
        tool_calls=len(tool),
        cache_hits=sum(1 for e in tool if e.cache_hit),
        evidence_records=ctx.evidence.count_for(inv.investigation_id),
    )