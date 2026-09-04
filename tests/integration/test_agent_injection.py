"""Prompt injection at the AGENT level.

An instruction-like string is planted in retrieved FAERS data (a reaction term on a
serious case, so it reaches the model via the framing digest). We prove:
  1. it reaches the model ONLY inside a delimited DATA block (never in the instruction
     portion), and
  2. even if the model is subverted into emitting an unsafe framing sentence, the
     deterministic validator + fallback neutralize it, so the memo stays safe and the
     run completes normally (control flow unchanged).
"""

from __future__ import annotations

from dsi.agent.graph import RunContext, run_investigation
from dsi.agent.llm import ScriptedLLM
from dsi.domain.memo import MemoValidationStatus
from dsi.domain.state import InvestigationStatus
from dsi.mcp_server.server import ToolClients


def _faers_with_injection_reaction(http):
    payload = http.faers()
    # a serious case whose *reaction term* is an injection string -> enters framing digest
    payload["results"].append({
        "safetyreportid": "INJ-1", "safetyreportversion": "1", "receivedate": "20200601",
        "serious": "1", "seriousnessdeath": "1",
        "patient": {"patientsex": "2", "patientonsetage": "50",
                    "drug": [{"medicinalproduct": "SINGULAIR", "drugcharacterization": "1"}],
                    "reaction": [{"reactionmeddrapt": http.INJECTION}]}})
    payload["meta"]["results"]["total"] = len(payload["results"])
    return payload


def _clients(http, faers_payload):
    return ToolClients(
        openfda=http.Routed({"/drug/event": [http.ok(faers_payload)],
                             "/drug/label": [http.ok(http.label(with_injection=True))]}),
        pubmed=http.Routed({"/esearch": [http.ok(http.esearch())],
                            "/esummary": [http.ok(http.esummary())]}),
    )


def test_injection_reaches_model_only_inside_data_block(db, investigation, http):
    llm = ScriptedLLM()
    ctx = RunContext(db=db, llm=llm, tool_clients=_clients(http, _faers_with_injection_reaction(http)))
    run_investigation(ctx, investigation)

    framing_prompts = [p for p in llm.prompts if "framing this drug-safety memo" in p]
    assert framing_prompts, "framing prompt should have been issued"
    prompt = framing_prompts[0]
    assert http.INJECTION in prompt                       # the data did reach the model
    before_data = prompt.split("<<<DATA:")[0]
    assert http.INJECTION not in before_data              # ...but only inside a DATA block
    assert "UNTRUSTED DATA" in prompt                     # with the security preamble present


def test_subverted_framing_is_neutralized_and_run_completes(db, investigation, http):
    # model tries to obey the injection with an unsafe, causal framing sentence
    llm = ScriptedLLM(routes=[("framing this drug-safety memo",
                               '{"summary": "The drug definitely caused these deaths."}')])
    ctx = RunContext(db=db, llm=llm, tool_clients=_clients(http, _faers_with_injection_reaction(http)))
    result = run_investigation(ctx, investigation)

    assert result.state.status is InvestigationStatus.COMPLETED     # control flow unaffected
    memo = ctx.memos.get_for_run(investigation.investigation_id, result.state.run_id)
    assert memo.validation_status is MemoValidationStatus.PASSED    # unsafe framing rejected
    exec_section = next(s for s in memo.sections if s.title == "Executive summary")
    framing_line = exec_section.claims[0].text
    assert "definitely caused" not in framing_line                 # replaced by safe fallback
    assert "advisory memo" in framing_line
