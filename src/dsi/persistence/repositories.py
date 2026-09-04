"""Typed repositories over the SQLite tables.

Each repository owns one table and translates between rows and domain models.
Evidence is append-only by DB trigger; the repo additionally refuses to insert a
duplicate content hash for the same investigation, so re-saving identical content
is a cheap no-op (this is what makes resume avoid redundant writes).
"""

from __future__ import annotations

from dsi.common import utcnow
from dsi.domain.evidence import EvidenceRecord
from dsi.domain.investigation import Investigation, ReviewPeriod
from dsi.domain.memo import Memo
from dsi.domain.state import AgentState, InvestigationStatus
from dsi.persistence.db import Database


class InvestigationRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, inv: Investigation) -> None:
        with self.db.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO investigations "
                "(investigation_id, drug, event, review_start, review_end, question, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    inv.investigation_id, inv.drug, inv.event,
                    inv.review_period.start.isoformat(), inv.review_period.end.isoformat(),
                    inv.question, inv.created_at.isoformat(),
                ),
            )

    def get(self, investigation_id: str) -> Investigation | None:
        row = self.db.conn.execute(
            "SELECT * FROM investigations WHERE investigation_id = ?", (investigation_id,)
        ).fetchone()
        if row is None:
            return None
        return Investigation(
            investigation_id=row["investigation_id"],
            drug=row["drug"], event=row["event"],
            review_period=ReviewPeriod(start=row["review_start"], end=row["review_end"]),
            question=row["question"], created_at=row["created_at"],
        )


class EvidenceRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    def exists_hash(self, investigation_id: str, content_hash: str) -> bool:
        row = self.db.conn.execute(
            "SELECT 1 FROM evidence WHERE investigation_id = ? AND content_hash = ? LIMIT 1",
            (investigation_id, content_hash),
        ).fetchone()
        return row is not None

    def save(self, investigation_id: str, record: EvidenceRecord) -> bool:
        """Insert an evidence record. Returns False (no-op) if identical content
        for this investigation already exists --- avoiding redundant writes on resume."""
        if self.exists_hash(investigation_id, record.content_hash):
            return False
        with self.db.transaction() as c:
            c.execute(
                "INSERT INTO evidence "
                "(evidence_id, investigation_id, payload_kind, content_hash, payload_json, "
                " provenance_json, is_synthetic, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    record.evidence_id, investigation_id, record.payload.kind,
                    record.content_hash, record.payload.model_dump_json(),
                    record.provenance.model_dump_json(),
                    int(record.provenance.is_synthetic), record.created_at.isoformat(),
                ),
            )
        return True

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        row = self.db.conn.execute(
            "SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)
        ).fetchone()
        return self._row_to_record(row) if row else None

    def list_for(self, investigation_id: str) -> list[EvidenceRecord]:
        rows = self.db.conn.execute(
            "SELECT * FROM evidence WHERE investigation_id = ? ORDER BY created_at, evidence_id",
            (investigation_id,),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def count_for(self, investigation_id: str) -> int:
        return self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM evidence WHERE investigation_id = ?", (investigation_id,)
        ).fetchone()["n"]

    @staticmethod
    def _row_to_record(row) -> EvidenceRecord:
        # Reconstruct via the full-record JSON shape the model expects.
        import json
        return EvidenceRecord(
            evidence_id=row["evidence_id"],
            payload=json.loads(row["payload_json"]),
            provenance=json.loads(row["provenance_json"]),
            content_hash=row["content_hash"],
            created_at=row["created_at"],
        )


class AnalysisRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, investigation_id: str, run_id: str, result) -> None:
        """Persist an AnalysisResult subclass. `result_json` stores the full model."""
        with self.db.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO analysis_results "
                "(result_id, investigation_id, run_id, kind, inputs_hash, output_hash, "
                " consumed_hashes_json, result_json, computed_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    result.result_id, investigation_id, run_id, result.kind.value,
                    result.inputs_hash, result.output_hash,
                    __import__("json").dumps(result.consumed_evidence_hashes),
                    result.model_dump_json(), result.computed_at.isoformat(),
                ),
            )

    def get_raw_for_run(self, investigation_id: str, run_id: str) -> list[dict]:
        """Return result rows as dicts (kind + json) for a run; typed rehydration
        is the caller's job since results are a family of subclasses."""
        rows = self.db.conn.execute(
            "SELECT kind, output_hash, result_json FROM analysis_results "
            "WHERE investigation_id = ? AND run_id = ?",
            (investigation_id, run_id),
        ).fetchall()
        return [dict(r) for r in rows]


class MemoRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, memo: Memo) -> None:
        with self.db.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO memos "
                "(memo_id, investigation_id, run_id, model_tag, validation_status, memo_json, generated_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    memo.memo_id, memo.investigation_id, memo.run_id, memo.model_tag,
                    memo.validation_status.value, memo.model_dump_json(), memo.generated_at.isoformat(),
                ),
            )

    def get_for_run(self, investigation_id: str, run_id: str) -> Memo | None:
        row = self.db.conn.execute(
            "SELECT memo_json FROM memos WHERE investigation_id = ? AND run_id = ? "
            "ORDER BY generated_at DESC LIMIT 1",
            (investigation_id, run_id),
        ).fetchone()
        return Memo.model_validate_json(row["memo_json"]) if row else None

    def count_for(self, investigation_id: str) -> int:
        return self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM memos WHERE investigation_id = ?", (investigation_id,)
        ).fetchone()["n"]


class StateRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, state: AgentState) -> None:
        with self.db.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO agent_state "
                "(investigation_id, run_id, status, state_json, updated_at) VALUES (?,?,?,?,?)",
                (
                    state.investigation_id, state.run_id, state.status.value,
                    state.model_dump_json(), utcnow().isoformat(),
                ),
            )

    def load(self, investigation_id: str, run_id: str) -> AgentState | None:
        row = self.db.conn.execute(
            "SELECT state_json FROM agent_state WHERE investigation_id = ? AND run_id = ?",
            (investigation_id, run_id),
        ).fetchone()
        return AgentState.model_validate_json(row["state_json"]) if row else None

    def latest_run(self, investigation_id: str) -> AgentState | None:
        """Most recently updated run for an investigation --- the one to resume."""
        row = self.db.conn.execute(
            "SELECT state_json FROM agent_state WHERE investigation_id = ? "
            "ORDER BY updated_at DESC LIMIT 1",
            (investigation_id,),
        ).fetchone()
        return AgentState.model_validate_json(row["state_json"]) if row else None
