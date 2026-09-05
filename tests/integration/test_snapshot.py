"""The committed real-data eval snapshot loads into the cache and is replayable
offline (so `dsi eval` runs on real public data with no network)."""

from __future__ import annotations

from datetime import date

from dsi.domain.tools import FaersSearchRequest
from dsi.eval.fixtures import REAL_EVAL_INVESTIGATION
from dsi.eval.snapshot import (
    first_report_target,
    load_into_cache,
    snapshot_captured_at,
    snapshot_exists,
)
from dsi.persistence.cache import SnapshotCache, make_cache_key
from dsi.persistence.db import Database


def test_snapshot_replays_into_cache(tmp_path):
    assert snapshot_exists(), "committed real-data snapshot should be present"
    db = Database.create(tmp_path / "s.sqlite")
    load_into_cache(db, REAL_EVAL_INVESTIGATION)

    # the exact FAERS request the agent will build is now a cache hit (offline)
    req = FaersSearchRequest(drug="montelukast", event="depression",
                             date_start=date(2019, 1, 1), date_end=date(2021, 12, 31))
    hit = SnapshotCache(db).get(make_cache_key("faers_search", req))
    assert hit is not None and hit.cache_hit is True

    # a real report id/reactions are available for the evidence-update scenario
    rid, ver, reactions, _ = first_report_target()
    assert rid and ver >= 1 and reactions
    assert snapshot_captured_at() != "unknown"
