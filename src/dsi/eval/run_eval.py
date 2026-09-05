"""The one-command evaluation.

Seeds the pinned offline snapshot, runs the investigation N times (cold vs warm),
runs the constrained comparison and the Scenario-A recompute, and writes a results
summary (Markdown + JSON) with raw measurements, method, sample size, and hardware.
Reads only from the trace spine for metrics --- numbers cannot drift from behaviour.
"""

from __future__ import annotations

import json
import platform
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from dsi.agent.graph import RunContext, run_investigation
from dsi.agent.llm import LLMClient, OllamaClient
from dsi.config import get_settings
from dsi.domain.state import Budget
from dsi.eval.metrics import compute_run_metrics, latency_summary, peak_memory_mb
from dsi.eval.quality_checks import check_memo
from dsi.eval.seed import OfflineGuardClient
from dsi.eval.fixtures import REAL_EVAL_INVESTIGATION
from dsi.eval.snapshot import first_report_target, load_into_cache, snapshot_captured_at
from dsi.mcp_server.server import ToolClients
from dsi.persistence.db import Database
from dsi.scenarios import corrected_version_record, run_scenario_a


def _offline_clients() -> ToolClients:
    return ToolClients(openfda=OfflineGuardClient(), pubmed=OfflineGuardClient())


def _hardware() -> dict:
    import psutil
    return {
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "python": platform.python_version(),
        "logical_cpus": psutil.cpu_count(logical=True),
        "vram": "not measured (CPU-only run; report VRAM from `ollama ps` if GPU is used)",
    }


def run_eval(*, llm_factory: Callable[[], LLMClient], reps: int = 3,
             out_dir: str | Path = "data/outputs", reduction_target: float = 0.4) -> dict:
    settings = get_settings()
    inv = REAL_EVAL_INVESTIGATION

    # --- baseline reps (cold vs warm latency), fully offline from the REAL snapshot ---
    db = Database.create(":memory:")
    load_into_cache(db, inv)
    latencies: list[float] = []
    last: RunContext | None = None
    last_run = ""
    for i in range(reps):
        ctx = RunContext(db=db, llm=llm_factory(), tool_clients=_offline_clients())
        t0 = time.perf_counter()
        res = run_investigation(ctx, inv)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        last, last_run = ctx, res.state.run_id

    base_metrics = compute_run_metrics(last, inv, last_run)
    base_memo = last.memos.get_for_run(inv.investigation_id, last_run)
    base_quality = check_memo(base_memo)

    # --- constrained comparison ---
    budget = Budget(max_total_tokens=int(base_metrics["tokens_total"] * (1 - reduction_target)))
    con_ctx = RunContext(db=db, llm=llm_factory(), tool_clients=_offline_clients(),
                         deterministic_framing=True, top_n_serious=2)
    con_res = run_investigation(con_ctx, inv, budget=budget)
    con_metrics = compute_run_metrics(con_ctx, inv, con_res.state.run_id)
    con_quality = check_memo(con_ctx.memos.get_for_run(inv.investigation_id, con_res.state.run_id))
    reduction = ((base_metrics["tokens_total"] - con_metrics["tokens_total"])
                 / base_metrics["tokens_total"] if base_metrics["tokens_total"] else 0.0)

    # --- Scenario A: work reused vs recomputed after an evidence update ---
    # Correct an ACTUAL case from the real snapshot (flip it to serious).
    db_a = Database.create(":memory:")
    load_into_cache(db_a, inv)
    ctx_a = RunContext(db=db_a, llm=llm_factory(), tool_clients=_offline_clients())
    rid, ver, reacts, rdate = first_report_target()
    a = run_scenario_a(ctx_a, inv, corrected_version_record(
        rid, ver, serious=True, reactions=reacts, receive_date=rdate))

    report = {
        "method": {
            "description": "Offline eval from a pinned REAL openFDA/PubMed snapshot; metrics "
                           "read from the SQLite trace spine.",
            "snapshot": "real-openfda-pubmed", "snapshot_date": snapshot_captured_at(),
            "drug_event": f"{inv.drug} / {inv.event}", "reps": reps,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "hardware": _hardware(),
        "latency": {
            "cold_ms": round(latencies[0], 2),
            "warm": latency_summary(latencies[1:]) if len(latencies) > 1 else "n/a (reps<2)",
            "all_ms": [round(x, 2) for x in latencies],
        },
        "baseline_metrics": base_metrics,
        "baseline_quality": base_quality,
        "constrained_metrics": con_metrics,
        "constrained_quality": con_quality,
        "baseline_vs_constrained": {
            "baseline_tokens": base_metrics["tokens_total"],
            "constrained_tokens": con_metrics["tokens_total"],
            "token_reduction_pct": round(reduction * 100, 1),
            "quality_floor_held": con_quality["passed"] and con_quality["all_required_sections"],
        },
        "evidence_update_recompute": {
            "recomputed_nodes": a.recomputed_nodes,
            "reused_nodes": a.reused_nodes,
            "short_circuited_nodes": a.short_circuited_nodes,
            "reused_count": len(a.reused_nodes),
            "recomputed_count": len(a.recomputed_nodes),
            "seriousness_before": list(a.seriousness_before),
            "seriousness_after": list(a.seriousness_after),
            "prior_run_preserved": a.run1_preserved,
        },
        "peak_memory_mb": peak_memory_mb(),
    }

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "eval_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "eval_results.md").write_text(_render_markdown(report), encoding="utf-8")
    return report


def _fmt_warm(warm) -> str:
    if not isinstance(warm, dict):
        return str(warm)
    return (f"p50 **{warm['p50_ms']} ms** | p90 {warm['p90_ms']} ms | p95 {warm['p95_ms']} ms "
            f"(n={warm['n']}, min {warm['min_ms']} / max {warm['max_ms']} ms)")


def _render_markdown(r: dict) -> str:
    m = r["baseline_metrics"]
    q = r["baseline_quality"]
    bc = r["baseline_vs_constrained"]
    er = r["evidence_update_recompute"]
    L = [
        "# Evaluation Results",
        "",
        f"_Method: {r['method']['description']}_",
        f"_Snapshot: {r['method']['snapshot']} ({r['method']['snapshot_date']}) | "
        f"pair: {r['method']['drug_event']} | reps: {r['method']['reps']} | "
        f"generated {r['method']['generated_at']}_",
        "",
        "## Hardware",
        f"- {r['hardware']['platform']} | {r['hardware']['logical_cpus']} logical CPUs | "
        f"Python {r['hardware']['python']}",
        f"- VRAM: {r['hardware']['vram']}",
        "",
        "## Latency (end-to-end)",
        f"- Cold: **{r['latency']['cold_ms']} ms**",
        f"- Warm: {_fmt_warm(r['latency']['warm'])}",
        "",
        "## Tokens & I/O (baseline run)",
        f"- Model calls: {m['model_calls']} | tokens in/out/total: "
        f"{m['tokens_input']}/{m['tokens_output']}/**{m['tokens_total']}** | "
        f"retry tokens: {m['retry_tokens']} | max context: {m['context_size_max']}",
        f"- Tool calls attempted/succeeded/failed/empty/retried: "
        f"{m['tool_calls_attempted']}/{m['tool_calls_succeeded']}/{m['tool_calls_failed']}/"
        f"{m['tool_calls_empty']}/{m['tool_calls_retried']} | invalid model outputs: "
        f"{m['model_calls_invalid']}",
        f"- Cache hits: {m['cache_hits']} | records read/written: "
        f"{m['records_read']}/{m['records_written']}",
        f"- Peak process memory: **{r['peak_memory_mb']} MB**",
        "",
        "## Quality (baseline memo)",
        f"- Material claims: {q['material_claims']} | uncited: **{q['uncited_material_claims']}** | "
        f"citation completeness: **{q['citation_completeness']}**",
        f"- Unsupported (prohibited-pattern) claims: **{q['unsupported_claims']}** | "
        f"all required sections: {q['all_required_sections']} | "
        f"safety-boundary compliant: **{q['safety_boundary_compliant']}** | "
        f"schema valid: {q['output_schema_valid']}",
        "",
        "## Baseline vs constrained",
        f"- Tokens: {bc['baseline_tokens']} -> {bc['constrained_tokens']} "
        f"(**{bc['token_reduction_pct']}%** reduction)",
        f"- Quality floor held: **{bc['quality_floor_held']}**",
        "",
        "## Evidence update: work reused vs recomputed",
        f"- Recomputed ({er['recomputed_count']}): {er['recomputed_nodes']}",
        f"- Reused ({er['reused_count']}): {er['reused_nodes']}",
        f"- Short-circuited: {er['short_circuited_nodes']}",
        f"- Serious count before/after: {er['seriousness_before']} -> {er['seriousness_after']} | "
        f"prior run preserved: **{er['prior_run_preserved']}**",
    ]
    return "\n".join(L) + "\n"


def main() -> int:
    """Entry point for `dsi eval` --- uses the real pinned local model.

    Imposes a 50% model-token budget on the constrained run; with real (variable)
    per-call token sizes the guard overshoots slightly, so a 50% imposed budget is
    what reliably yields the >=40% achieved reduction the assessment asks for."""
    settings = get_settings()
    report = run_eval(llm_factory=lambda: OllamaClient(settings.model_tag, settings.ollama_host),
                      reduction_target=0.5)
    print(f"Eval complete. Baseline tokens={report['baseline_metrics']['tokens_total']}, "
          f"constrained reduction={report['baseline_vs_constrained']['token_reduction_pct']}%, "
          f"quality floor held={report['baseline_vs_constrained']['quality_floor_held']}.")
    print("Wrote data/outputs/eval_results.md and eval_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
