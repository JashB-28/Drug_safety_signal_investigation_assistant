"""Tiny shared helpers with no domain knowledge: id generation and a clock.

Kept separate so tests can monkeypatch time/ids deterministically and so no
module grows a hidden dependency on `datetime.now`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware current UTC time. The single clock used across the package."""
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    """A short, collision-resistant identifier like ``evd_9f2a1c4b7d0e``.

    The prefix names the entity type so ids are self-describing in logs and the DB.
    """
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
