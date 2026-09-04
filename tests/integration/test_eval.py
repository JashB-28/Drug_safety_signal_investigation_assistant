"""The evaluation harness runs offline, emits the required metrics, and its numbers
are internally consistent."""

from __future__ import annotations

from dsi.agent.llm import ScriptedLLM
from dsi.eval.run_eval import run_eval


def test_eval_runs_offline_and_reports_required_metrics(tmp_path):
    report = run_eval(llm_factory=lambda: ScriptedLLM(), reps=2, out_dir=tmp_path,
                      reduction_target=0.4)

    # required metric families present
    for key in ("method", "hardware", "latency", "baseline_metrics", "baseline_quality",
                "baseline_vs_constrained", "evidence_update_recompute", "peak_memory_mb"):
        assert key in report

    m = report["baseline_metrics"]
    assert m["tokens_total"] > 0
    assert m["cache_hits"] >= 3                         # all three tools served from cache (offline)
    assert m["tool_calls_attempted"] >= 3
    assert report["latency"]["cold_ms"] > 0

    # quality floor on the baseline memo
    q = report["baseline_quality"]
    assert q["uncited_material_claims"] == 0
    assert q["unsupported_claims"] == 0
    assert q["all_required_sections"] is True
    assert q["safety_boundary_compliant"] is True

    # constrained run is cheaper and still holds the floor
    bc = report["baseline_vs_constrained"]
    assert bc["constrained_tokens"] <= bc["baseline_tokens"]
    assert bc["token_reduction_pct"] >= 30.0
    assert bc["quality_floor_held"] is True

    # evidence update reused most work, recomputed some, preserved the prior run
    er = report["evidence_update_recompute"]
    assert er["reused_count"] > 0 and er["recomputed_count"] > 0
    assert er["prior_run_preserved"] is True

    # artifacts written
    assert (tmp_path / "eval_results.md").exists()
    assert (tmp_path / "eval_results.json").exists()
