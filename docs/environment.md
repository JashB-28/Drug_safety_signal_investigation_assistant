# Local environment (confirmed working)

This records the environment confirmed at the end of Phase 1 setup, for reproducibility.
The README (Phase 10) will fold this into one-command setup instructions.

## Confirmed on this machine (2026-09-03)

| Component | Value |
|---|---|
| OS | Windows 11 Home (10.0.26200) |
| Python (venv) | CPython **3.13.12** (chosen over 3.14 for full wheel availability across LangGraph/MCP) |
| Env manager | `uv` 0.10.9 → virtualenv at `.venv/` |
| Ollama | 0.33.2 |
| Pinned model | **`mistral:7b-instruct`** (ID `6577803aa9a0`, 4.4 GB) — pulled & smoke-tested |
| Model JSON smoke test | returns valid JSON; Ollama reports `prompt_eval_count` / `eval_count` (token counters the metrics spine uses) |

## Resolved dependency versions (installed & import-verified)

| Package | Version | Role |
|---|---|---|
| pydantic | 2.13.5 | typed schemas + structured-output validation |
| langgraph | 1.2.11 | single-agent orchestration graph + resume |
| mcp | 1.29.1 | official MCP SDK — **pinned `<2`** for the stable FastMCP API |
| httpx | 0.28.1 | HTTP client (bounded timeouts/retries) |
| ollama | 0.6.2 | local model client |
| structlog | 26.1.0 | structured JSON logging |
| psutil | 7.2.2 | peak-memory metric |
| python-dotenv | 1.2.3 | load `.env` (no secrets committed) |
| pytest / pytest-asyncio | 9.1.1 / 1.4.0 | tests (MCP tools are async) |
| respx | 0.23.1 | mock httpx in tool failure/empty/malformed tests |

> **Note on the `mcp` pin:** `mcp>=1.2` now resolves to `2.x`, which renamed
> `FastMCP` → `MCPServer` and changed APIs. We pin `mcp<2` (resolved 1.29.1) to
> use the stable, widely-documented FastMCP interface. Revisit if the project
> later standardizes on the 2.x `MCPServer` API.

## Recreate from scratch

```bash
uv venv --python 3.13 .venv
source .venv/Scripts/activate      # Windows Git Bash; PowerShell: .venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"          # once the dsi package skeleton exists (Phase 2)
ollama pull mistral:7b-instruct
```

Until the `dsi` package skeleton exists (Phase 2), dependencies were installed
directly from the pinned list in `pyproject.toml`. Phase 2's first step is to
add the package skeleton and generate `uv.lock` for exact-version reproducibility.
