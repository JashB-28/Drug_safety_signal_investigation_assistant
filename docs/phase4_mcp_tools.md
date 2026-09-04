# Phase 4 — MCP tools (how it works, where to change it)

## What this layer is
Three **read-only** evidence-retrieval tools exposed on a local MCP server. They
are *pure retrieval*: bounded timeouts, bounded retries with backoff, structured
errors. Caching and tracing are deliberately NOT here — the agent (Phase 6) owns
those so every tool call is measured and cached uniformly.

## The tools
| MCP tool | Source | Returns |
|---|---|---|
| `faers_search` | openFDA drug/event | `FaersSearchData` (typed `AdverseEventReport`s) |
| `label_fetch` | openFDA drug/label | `LabelFetchData` (typed `LabelSection`s) |
| `literature_search` | PubMed eutils (esearch + esummary) | `LiteratureSearchData` |

## Design choices that matter
- **Failure is a value, never an exception.** `BoundedHttpClient` converts every
  failure (timeout, connection error, 5xx, 429, malformed JSON) into a structured
  `ToolError` inside a `ToolResult`. The graph branches on `error.code`; nothing
  crashes.
- **Retry policy — exactly three triggers, and 429 respects the server.**
  Retried: **timeouts**, **5xx**, and **429**. For **429** (and **503**, which can
  also carry it) the client **honors the `Retry-After` header** — seconds or
  HTTP-date — capped by `max_retry_after` so a hostile/huge value can't stall the
  run; only when no header is present does it fall back to exponential backoff.
  This matters because openFDA and NCBI eutils both send timing hints on
  throttling, and backing off on our own curve while ignoring the header gets you
  throttled harder. **404** is terminal (openFDA "no matches"); other **4xx** are
  terminal. All sleeps go through an injectable `sleep_fn` → instant tests.
- **openFDA 404 = graceful empty.** openFDA returns 404 when a query matches
  nothing, so both openFDA tools translate 404 into a valid empty result
  (`returned=0`, `ok=True`), not an error — "no matching records" is a complete
  answer.
- **Parsing separated from I/O.** `openfda.py` / `pubmed.py` keep pure
  `build_*`/`parse_*` functions, unit-tested against synthetic fixtures with no
  network. Missingness is preserved as `None` (e.g. a report with no patient age).
- **Injectable clients.** `build_server(clients=...)` and every tool function take
  an `HttpClient`, so tests drive them with a `FakeHttpClient` or
  `httpx.MockTransport`. The eval/demo never depends on a live API.
- **No secrets in source.** An openFDA key is optional, read from the environment
  only (dev-time rate limits); absent by default.

## Untrusted-input handling (prompt injection)
`test_prompt_injection.py` injects an instruction-like string into a fixture and
proves the tools capture it **verbatim as typed DATA** (a drug-indication field, a
label section body) and are otherwise unaffected. The end-to-end confirmation that
the *agent ignores* the instruction — because retrieved text enters the model only
inside a delimited data field — is added in Phase 6 with the context builder.

## Where I would change each thing
| To change… | Edit… |
|---|---|
| Retry/timeout/backoff policy | `mcp_server/http_client.py` |
| openFDA query construction | `build_faers_query` / `build_label_query` in `openfda.py` |
| How a response field maps to a model | the `parse_*` functions |
| Which label sections are fetched | `_LABEL_FIELDS` in `openfda.py` |
| Add/replace a tool | add a `parse_*` + tool fn, register in `server.py::build_server` |

## Tests (18 new; 75 total)
`test_http_client.py` (retry/timeout/malformed/404/429), `test_mcp_tools.py`
(parse + empty/malformed/timeout for all three tools), `test_mcp_server.py`
(server exposes exactly 3 tools + invoke), `test_prompt_injection.py`.
Run: `pytest -q`.
