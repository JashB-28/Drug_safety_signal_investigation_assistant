# Phase 2 — Domain & schemas (how it works, where to change it)

## What this layer is
Pure data definitions — no I/O, no LLM, no database. Every other phase speaks in
these types. The layer physically encodes the core principle "evidence over
generation" by giving each of the three data categories its own module:

| Category | Module | Never edited by |
|---|---|---|
| (a) raw evidence | `domain/evidence.py` + `domain/provenance.py` | the LLM |
| (b) deterministic analysis | `domain/analysis.py` | the LLM |
| (c) LLM prose | `domain/memo.py` | — (but rebuildable from a + b) |

Plus the plumbing: `domain/investigation.py` (input), `domain/tools.py` (typed
tool I/O envelope), `domain/state.py` (agent working memory + decision log +
budget), and two root utilities `hashing.py` and `common.py`.

## The three ideas that make later phases work
1. **Content hashing (`hashing.py`).** `EvidenceRecord.create` hashes the *payload
   only*. Re-fetching identical content yields the same hash — that is literally
   how Scenario A detects "nothing changed." `hash_of_hashes` fingerprints a *set*
   of inputs order-independently, which the dependency graph (Phase 3) uses.
2. **Analysis carries its inputs (`analysis.py`).** Every `AnalysisResult` stores
   `consumed_evidence_hashes`, `inputs_hash`, and `output_hash`. That is the whole
   basis of selective recompute + the output-hash short-circuit.
3. **Citations are structured (`memo.py`).** A memo is sections → claims →
   citations, not free text, so `memo.uncited_material_claims()` makes citation
   completeness a mechanical check, not a vibe.

## Safety already visible in the schema
- `ToolResult` makes failure a *value* (structured `ToolError`), never an
  exception — the agent branches on `error.code`, and a `model_validator` enforces
  the ok⇔data / not-ok⇔error invariant.
- `TemporalComparison` reports report-count *direction* with a built-in disclaimer
  that these are not incidence/occurrence rates.
- `DuplicateGroupCertainty` forces the confirmed-vs-likely distinction.
- `SourceType.SYNTHETIC` + `Provenance.is_synthetic` keep test fixtures
  distinguishable from real FDA data forever.

## Where I would change each thing
| To change… | Edit… |
|---|---|
| A FAERS/label/literature field | the payload model in `domain/evidence.py` |
| What counts as a tool failure | `ToolErrorCode` in `domain/tools.py` |
| A new analysis output | add an `AnalysisResult` subclass in `domain/analysis.py` |
| The required memo sections | `MemoSectionKind` in `domain/memo.py` |
| The actions the agent may take | `ActionType` in `domain/state.py` |
| How content is hashed | `hashing.py` (single choke point) |

## Tests
`tests/unit/` — 32 tests covering hash determinism/order-independence,
content-only hashing, discriminated-union round-trip, missingness-as-None, tool
envelope invariants, citation completeness, and state/budget transitions.
Run: `pytest -q`.
