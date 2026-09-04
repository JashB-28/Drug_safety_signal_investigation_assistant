"""SQLite connection management and schema initialization.

Deliberately thin: one connection per `Database`, row access by column name,
foreign keys on, and a `transaction()` context manager. Everything else is in
the repositories. Keeping this small means the storage engine is easy to reason
about and swap.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class Database:
    """A single SQLite connection plus schema setup."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        is_memory = self.path == ":memory:"
        if not is_memory:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        if not is_memory:
            # WAL improves concurrent read/write and survives crashes cleanly
            # (relevant to the restart/resume requirement). Not valid for :memory:.
            self._conn.execute("PRAGMA journal_mode = WAL")

    @classmethod
    def create(cls, path: str | Path) -> "Database":
        """Open (creating the file if needed) and ensure the schema exists."""
        db = cls(path)
        db.init_schema()
        return db

    def init_schema(self) -> None:
        self._conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        self._conn.commit()

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Commit on success, roll back on any exception."""
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def close(self) -> None:
        self._conn.close()
