-- SQLite schema for the Drug Safety Signal Investigation Assistant.
-- One file, executed at startup. All timestamps are ISO-8601 UTC strings.
--
-- Separation of concerns is visible in the tables:
--   evidence        = raw retrieved data (category a) -- IMMUTABLE (triggers below)
--   analysis_results= deterministic computation (category b)
--   memos           = LLM prose (category c), versioned
--   dep_nodes/edges = the selective-recompute dependency graph
--   snapshot_cache  = cached tool responses for offline reproducibility
--   trace_events    = the metrics/trace spine (every tool + model call)

PRAGMA foreign_keys = ON;

-- --------------------------------------------------------------------------
-- Investigations (the analyst's input)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS investigations (
    investigation_id TEXT PRIMARY KEY,
    drug             TEXT NOT NULL,
    event            TEXT NOT NULL,
    review_start     TEXT NOT NULL,
    review_end       TEXT NOT NULL,
    question         TEXT,
    created_at       TEXT NOT NULL
);

-- --------------------------------------------------------------------------
-- Evidence (category a) -- raw, provenance-bearing, content-hashed, IMMUTABLE.
-- A follow-up case version or a corrected report is a NEW row (new id + hash),
-- never an update to an existing one. The triggers enforce append-only so the
-- LLM (or any code path) can never silently modify persisted evidence.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id      TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    payload_kind     TEXT NOT NULL,
    content_hash     TEXT NOT NULL,
    payload_json     TEXT NOT NULL,
    provenance_json  TEXT NOT NULL,
    is_synthetic     INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations (investigation_id)
);
CREATE INDEX IF NOT EXISTS idx_evidence_inv  ON evidence (investigation_id);
CREATE INDEX IF NOT EXISTS idx_evidence_hash ON evidence (investigation_id, content_hash);

CREATE TRIGGER IF NOT EXISTS evidence_no_update
BEFORE UPDATE ON evidence
BEGIN
    SELECT RAISE(ABORT, 'evidence is immutable (append-only)');
END;

CREATE TRIGGER IF NOT EXISTS evidence_no_delete
BEFORE DELETE ON evidence
BEGIN
    SELECT RAISE(ABORT, 'evidence is immutable (append-only)');
END;

-- --------------------------------------------------------------------------
-- Analysis results (category b) -- deterministic; records what it consumed.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analysis_results (
    result_id            TEXT PRIMARY KEY,
    investigation_id     TEXT NOT NULL,
    run_id               TEXT NOT NULL,
    kind                 TEXT NOT NULL,
    inputs_hash          TEXT NOT NULL,
    output_hash          TEXT NOT NULL,
    consumed_hashes_json TEXT NOT NULL,
    result_json          TEXT NOT NULL,
    computed_at          TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations (investigation_id)
);
CREATE INDEX IF NOT EXISTS idx_analysis_run ON analysis_results (investigation_id, run_id);

-- --------------------------------------------------------------------------
-- Memos (category c) -- versioned prose; prior versions preserved.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memos (
    memo_id           TEXT PRIMARY KEY,
    investigation_id  TEXT NOT NULL,
    run_id            TEXT NOT NULL,
    model_tag         TEXT,
    validation_status TEXT,
    memo_json         TEXT NOT NULL,
    generated_at      TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations (investigation_id)
);
CREATE INDEX IF NOT EXISTS idx_memos_inv ON memos (investigation_id, run_id);

-- --------------------------------------------------------------------------
-- Agent state -- one row per (investigation, run); supports restart/resume.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_state (
    investigation_id TEXT NOT NULL,
    run_id           TEXT NOT NULL,
    status           TEXT NOT NULL,
    state_json       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    PRIMARY KEY (investigation_id, run_id),
    FOREIGN KEY (investigation_id) REFERENCES investigations (investigation_id)
);

-- --------------------------------------------------------------------------
-- Dependency graph -- evidence -> analysis -> memo_section, per run.
-- Prior runs are preserved (new run_id), giving the audit trail.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dep_nodes (
    run_id           TEXT NOT NULL,
    node_id          TEXT NOT NULL,
    investigation_id TEXT NOT NULL,
    node_type        TEXT NOT NULL,   -- 'evidence' | 'analysis' | 'memo_section'
    content_hash     TEXT,            -- evidence nodes
    output_hash      TEXT,            -- analysis / memo_section nodes
    inputs_hash      TEXT,
    stale            INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, node_id)
);

CREATE TABLE IF NOT EXISTS dep_edges (
    run_id             TEXT NOT NULL,
    upstream_node_id   TEXT NOT NULL,
    downstream_node_id TEXT NOT NULL,
    PRIMARY KEY (run_id, upstream_node_id, downstream_node_id)
);

-- --------------------------------------------------------------------------
-- Snapshot cache -- cached tool responses so the eval/demo run fully offline.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS snapshot_cache (
    cache_key      TEXT PRIMARY KEY,
    tool_name      TEXT NOT NULL,
    request_json   TEXT NOT NULL,
    response_json  TEXT NOT NULL,
    source_version TEXT,
    content_hash   TEXT NOT NULL,
    retrieved_at   TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

-- --------------------------------------------------------------------------
-- Trace spine -- every tool call and model call, uniformly.
-- Phase 8C (constrained run) and Phase 9 (eval) read ONLY from here.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trace_events (
    event_id            TEXT PRIMARY KEY,
    investigation_id    TEXT,
    run_id              TEXT,
    span_id             TEXT,
    parent_span_id      TEXT,
    kind                TEXT NOT NULL,   -- node | tool_call | model_call | analysis
    name                TEXT NOT NULL,
    ts_start            TEXT NOT NULL,
    ts_end              TEXT,
    latency_ms          REAL,
    tokens_in           INTEGER,
    tokens_out          INTEGER,
    tokens_total        INTEGER,
    context_size_tokens INTEGER,
    retry_count         INTEGER DEFAULT 0,
    cache_hit           INTEGER DEFAULT 0,
    outcome             TEXT,            -- ok | error | empty | invalid | redundant
    error_type          TEXT,
    bytes_read          INTEGER DEFAULT 0,
    bytes_written       INTEGER DEFAULT 0,
    records_read        INTEGER DEFAULT 0,
    records_written     INTEGER DEFAULT 0,
    cold                INTEGER DEFAULT 0,
    attributes_json     TEXT
);
CREATE INDEX IF NOT EXISTS idx_trace_run ON trace_events (investigation_id, run_id);