# AI Coding Assistant Disclosure

## What was used
This project was built with the assistance of an AI coding assistant (Claude Code,
Anthropic). The assistant contributed to design discussion, code drafting across all
phases, test drafting, and documentation.

## How the work was structured and reviewed
- **Phase-gated build.** Work proceeded in explicit phases (architecture → schemas →
  evidence layer → tools → analysis → agent → memo → scenarios → evaluation → docs),
  pausing for human review and approval at the load-bearing gates (Phase 1, 3, 6, 8).
- **Tests as the review harness.** Every component landed with tests (130 total);
  changes were only accepted when the suite passed. Failure modes (tool errors, empty/
  malformed responses, restart/resume, prompt injection, safety violations) have
  dedicated tests, not just happy paths.
- **Real execution, not just claims.** Load-bearing behaviour was verified by actually
  running it: the agent end-to-end on the real `mistral:7b-instruct` model; a live
  openFDA query returning real data; the eval producing real measurements. Reported
  numbers come from the trace spine and generated artifacts, not from narration.
- **Human challenge on domain correctness.** Reviewer questions drove real fixes —
  e.g. the FAERS `safetyreportid` = CASEID identifier check (preventing count
  inflation), honoring `Retry-After` on 429/503, and the quoted-source exemption in
  the safety validator (surfaced by a real PubMed title failing validation). These
  are recorded in the design docs.
- **Honesty about limits.** Where a metric couldn't be measured (VRAM on CPU) or a
  choice was weakly justified (LangGraph vs. a custom orchestrator; synthetic eval
  data), the docs say so plainly rather than overclaiming; an earlier doc overstatement
  (crediting LangGraph for resume) was corrected.

## What the human is responsible for
Final architecture decisions, acceptance at each gate, the drug–event pair choice,
and verifying that the behaviour and measurements are real. Any use in a genuine
pharmacovigilance setting requires review by a qualified safety professional; this
tool is advisory only.
