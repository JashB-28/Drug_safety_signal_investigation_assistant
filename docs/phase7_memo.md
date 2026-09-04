# Phase 7 — Memo generation (how it works, where to change it)

## What this phase added
Phase 6 already produced a complete, cited, safe memo. Phase 7 makes it
analyst-ready and wires it into selective recompute:

1. **Per-section dependency fingerprints.** `_attach_consumed_hashes` (in
   `memo/builder.py`) resolves each section's citations to the content/output hashes
   it was built from and stores them on `MemoSection.consumed_output_hashes`. This is
   what lets the dependency graph mark *exactly* the sections that consumed changed
   evidence as stale.
2. **Memo-section nodes in the dependency graph.** `_persist_memo_depnodes` (in
   `agent/graph.py`) adds a `memo:<section>` node per section, linked to the analysis
   nodes (matched by output hash) and evidence slots it consumed — completing
   `evidence → analysis → memo_section`. Scenario A (Phase 8) walks this to recompute
   only affected sections.
3. **Markdown renderer** (`memo/render.py`): a human-readable view with every
   material claim showing its citations inline as `[ref: <kind>:<id>]`, plus the
   advisory disclaimer. Pure formatting — no new facts. Produces the sample-memo
   deliverable (`data/outputs/sample_memo.md`).

## Why the memo is safe *by construction* (not just by scanning)
- Facts are deterministic and cited; the only LLM prose is one framing line, which
  is validated and replaced by a safe deterministic line if it trips the scanner.
- Raw retrieved free text (label bodies, indications) is never quoted into claims;
  sections are described neutrally and cited by id. So words like "incidence" that
  might appear in a real label never leak into the memo.
- The independent `validate_memo` scan is the backstop, and the rendered document is
  re-scanned in tests to confirm no prohibited pattern survives formatting.

## Where I would change each thing
| To change… | Edit… |
|---|---|
| Section wording / which claims appear | `memo/builder.py` |
| How a section's inputs are fingerprinted | `_attach_consumed_hashes` in `builder.py` |
| Rendered layout / citation format | `memo/render.py` |
| Memo→graph linkage | `_persist_memo_depnodes` in `agent/graph.py` |
| Prohibited-claim patterns | `memo/validator.py` |

## Tests (3 new; 125 total)
`test_memo_render_depgraph.py`: rendered memo is readable + carries all section
titles + citations + passes the safety scan; section `consumed_output_hashes` are
populated; memo-section nodes are wired into the dependency graph with upstream
analysis edges.
