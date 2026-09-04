"""Command-line entry point.

Commands:
  dsi investigate ...      Investigate a drug + event + period (LIVE openFDA/PubMed).
  dsi eval                 Run the reproducible offline evaluation (writes data/outputs/).
  dsi scenarios            Run the three challenge scenarios and print a summary.
  dsi --version            Print the version.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from dsi import __version__


def _cmd_investigate(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="dsi investigate",
                                description="Investigate a drug + suspected adverse event over a "
                                            "review period, fetching evidence live from openFDA/PubMed.")
    p.add_argument("--drug", required=True, help='e.g. "montelukast"')
    p.add_argument("--event", required=True,
                   help='suspected adverse event; a MedDRA-style term works best, e.g. "depression"')
    p.add_argument("--start", required=True, help="review period start, YYYY-MM-DD")
    p.add_argument("--end", required=True, help="review period end, YYYY-MM-DD")
    args = p.parse_args(argv)

    from dsi.investigate import investigate
    try:
        res = investigate(args.drug, args.event, date.fromisoformat(args.start),
                          date.fromisoformat(args.end))
    except ValueError as exc:
        print(f"error: {exc}")
        return 2
    print(f"Investigation: {args.drug} / {args.event} / {args.start}..{args.end}")
    print(f"  status: {res.status} | validation: {res.validation} | sections: {res.sections}")
    print(f"  evidence records: {res.evidence_records} | tool calls: {res.tool_calls} "
          f"(cache hits: {res.cache_hits}) | model tokens: {res.model_tokens}")
    print(f"  uncited material claims: {res.uncited_material_claims}")
    print(f"  memo written to: {res.memo_path}")
    return 0


def _cmd_eval() -> int:
    from dsi.eval.run_eval import main as eval_main
    return eval_main()


def _cmd_scenarios() -> int:
    # Runs the scenarios against the pinned offline snapshot with the real model.
    from datetime import date

    from dsi.agent.graph import RunContext
    from dsi.agent.llm import OllamaClient
    from dsi.config import get_settings
    from dsi.eval import fixtures
    from dsi.eval.seed import OfflineGuardClient, seed_cache
    from dsi.mcp_server.server import ToolClients
    from dsi.persistence.db import Database
    from dsi.scenarios import corrected_version_record, run_scenario_a, run_scenario_b

    settings = get_settings()
    inv = fixtures.EVAL_INVESTIGATION

    def ctx():
        db = Database.create(":memory:")
        seed_cache(db, inv)
        return RunContext(db=db, llm=OllamaClient(settings.model_tag, settings.ollama_host),
                          tool_clients=ToolClients(OfflineGuardClient(), OfflineGuardClient()))

    a = run_scenario_a(ctx(), inv, corrected_version_record(
        "EV-002", 2, serious=True, reactions=["Insomnia", "Depression"],
        receive_date=date(2019, 7, 15)))
    print(f"[A] recomputed={len(a.recomputed_nodes)} reused={len(a.reused_nodes)} "
          f"prior_run_preserved={a.run1_preserved} serious {a.seriousness_before[1]}->{a.seriousness_after[1]}")
    b = run_scenario_b(ctx(), inv)
    print(f"[B] conflict unresolved={b.unresolved} positions={len(b.positions)}")
    print("[C] see `dsi eval` for the constrained-run comparison.")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] in {"-v", "--version"}:
        print(f"dsi {__version__}")
        return 0
    if argv and argv[0] == "investigate":
        return _cmd_investigate(argv[1:])
    if argv and argv[0] == "eval":
        return _cmd_eval()
    if argv and argv[0] == "scenarios":
        return _cmd_scenarios()
    print(
        "dsi (Drug Safety Signal Investigation Assistant)\n"
        f"version {__version__}\n"
        "Commands:\n"
        '  dsi investigate --drug "montelukast" --event "depression" '
        "--start 2019-01-01 --end 2021-12-31\n"
        "                  Investigate a pair with LIVE openFDA/PubMed evidence\n"
        "  dsi eval        Run the reproducible offline evaluation\n"
        "  dsi scenarios   Run the three challenge scenarios\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
