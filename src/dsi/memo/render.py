"""Render a `Memo` to analyst-readable Markdown.

Pure formatting --- no new facts. Every material claim shows its citations inline as
`[ref: <id>]` so a reader can trace each statement back to an evidence record or a
named calculation. The renderer never invents content; it is a view over the
structured memo, which is itself rebuildable from evidence + analysis.
"""

from __future__ import annotations

from dsi.domain.memo import Claim, Memo


def _render_claim(claim: Claim) -> str:
    if claim.citations:
        refs = "; ".join(f"{c.kind.value}:{c.ref_id}" for c in claim.citations)
        return f"- {claim.text}  \n  _[ref: {refs}]_"
    return f"- {claim.text}"


def render_memo(memo: Memo) -> str:
    """Return a Markdown document for the memo."""
    lines: list[str] = []
    lines.append("# Drug Safety Signal Investigation Memo")
    lines.append("")
    lines.append(f"_Investigation `{memo.investigation_id}` | run `{memo.run_id}` | "
                 f"model `{memo.model_tag}` | generated {memo.generated_at.date()} | "
                 f"validation: **{memo.validation_status.value}**_")
    lines.append("")
    lines.append("> Advisory only. A human safety professional is the decision-maker. "
                 "This memo does not establish causation or rates and is not a treatment "
                 "recommendation.")
    lines.append("")
    for section in memo.sections:
        lines.append(f"## {section.title}")
        if not section.claims:
            lines.append("_(no content)_")
        for claim in section.claims:
            lines.append(_render_claim(claim))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
