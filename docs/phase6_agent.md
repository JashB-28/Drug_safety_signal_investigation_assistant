# Phase 6 — The agent (how it works, where to change it)

## What this layer is
The single investigation agent, orchestrated with LangGraph. It ties together the
tools (Phase 4), analysis (Phase 5), persistence + trace (Phase 3), and memo, and
is where the LLM actually makes decisions — bounded by deterministic controls.

## The graph
```
START → initialize → normalize → decide ⇄ {retrieve_faers | retrieve_label |
        retrieve_literature | run_analysis | sufficiency | conflicts} → decide
        decide → finalize (on generate_memo / stop) → END
```
`decide` is the **agentic** node: `available_actions(state)` computes the LEGAL next
actions, the LLM chooses one and gives a rationale (logged with the exact observed
state), and if the model returns junk or an illegal action, a deterministic policy
picks a legal one. Deterministic guards bound everything: a step limit and a token
budget force safe termination; an insufficient-evidence verdict routes to a halt.

## The five safety/quality mechanisms
1. **Structured output** (`structured_output.py`): every model output is
   JSON-extracted and Pydantic-validated, with **one bounded re-ask** then a
   **deterministic fallback** — a malformed reply never crashes the graph and never
   passes through unchecked. Recorded as `outcome=invalid` on fallback.
2. **Context control** (`context_builder.py`): the decision prompt contains only a
   compact state *summary* (counts), never raw evidence. The memo framing prompt
   includes only the **top-N most serious cases** as structured lines. We never dump
   the cache into a prompt.
3. **Injection defense**: retrieved text enters the model **only inside delimited
   `<<<DATA:…>>>` blocks**, and the system preamble declares that block content is
   untrusted data. Free-text fields (label bodies, drug indications) are never placed
   in prompts at all. Proven in `test_agent_injection.py`.
4. **Deterministic safety validator** (`memo/validator.py`): scans the final memo
   for prohibited patterns (causal/rate/incidence/treatment/certainty) with negation
   awareness, and fails the run if any survive. The only LLM prose in the memo is a
   single framing line; if it trips the validator it is replaced by a safe
   deterministic line and the memo re-validated.
5. **Full trace + resumable state**: every tool and model call is a spine span;
   `AgentState` (decisions, evidence ids, retries, budget, status) is persisted at
   each node, so a run resumes via the Phase-3 machinery.

## Tool failure / empty / retry
Retrieval nodes call tools through the snapshot cache (`cache_if=r.ok` so failures
aren't cached). On a retryable failure the source is **kept pending** so `decide`
re-offers it — bounded agent-level retry — then given up after `max_tool_retries`.
Empty results are a valid outcome that flows into the sufficiency check; zero cases
→ safe halt with a memo documenting why.

## Verified with the real model
A live `mistral:7b-instruct` run (synthetic offline tools) chose the full action
sequence itself, produced a 14-section memo that PASSED validation with 0 uncited
claims, in ~1.8k tokens.

## Where I would change each thing
| To change… | Edit… |
|---|---|
| Legal next-action rules | `available_actions` in `agent/decisions.py` |
| The decision prompt / policy | `decide` / `deterministic_policy` in `decisions.py` |
| Context size / case selection | `agent/context_builder.py` (top-N, digest) |
| Re-ask/fallback behavior | `agent/structured_output.py` |
| Sufficiency / conflict rules | `agent/sufficiency.py` / `agent/conflicts.py` |
| Prohibited-claim patterns | `memo/validator.py` |
| Memo sections / wording | `memo/builder.py` |
| Step/retry/budget bounds, top-N | `RunContext` fields in `agent/graph.py` |

## Tests (27 new; 122 total)
`test_validator.py`, `test_structured_output.py`, `test_decisions_and_context.py`,
`test_agent_graph.py` (happy path, empty-evidence safe stop, tool-failure retry,
agentic-decision logged, full-trace persisted), `test_agent_injection.py`
(data-block isolation + subverted-framing neutralized). All offline.
