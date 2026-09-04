"""The before/after evidence-update trace artifact generates offline and contains
the required parts: the change, reused-vs-recomputed, before/after, preservation."""

from __future__ import annotations

from dsi.scenarios.trace_report import generate_trace


def test_evidence_update_trace_artifact(tmp_path):
    path = generate_trace(out_dir=tmp_path)
    assert path.exists()
    text = path.read_text(encoding="utf-8")

    # the change + effect
    assert "EV-002" in text
    assert "Serious cases:" in text
    # reused vs recomputed breakdown
    assert "Recomputed" in text and "Reused" in text and "Short-circuited" in text
    assert "analysis:seriousness" in text          # a recomputed node
    assert "memo:label_evidence" in text           # a reused node
    # before/after + preservation + full memos
    assert "What actually changed in the memo" in text
    assert "**Before:**" in text and "**After:**" in text
    assert "Prior run preserved" in text
    assert "Full memo BEFORE" in text and "Full memo AFTER" in text
