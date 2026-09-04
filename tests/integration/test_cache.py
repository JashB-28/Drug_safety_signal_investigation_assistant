"""Snapshot cache: hit/miss, fetch-once, and query-change invalidation."""

from __future__ import annotations

from dsi.domain.evidence import AdverseEventReport
from dsi.domain.tools import FaersSearchData, FaersSearchRequest
from dsi.persistence.cache import SnapshotCache, make_cache_key


def _response(n: int) -> FaersSearchData:
    return FaersSearchData(
        reports=[AdverseEventReport(report_id=f"R{i}") for i in range(n)],
        total_matched=n, returned=n,
    )


def test_miss_then_hit_calls_fetch_once(db):
    cache = SnapshotCache(db)
    req = FaersSearchRequest(drug="montelukast", event="depression")
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return _response(3)

    r1, hit1 = cache.get_or_fetch("faers_search", req, fetch, FaersSearchData)
    r2, hit2 = cache.get_or_fetch("faers_search", req, fetch, FaersSearchData)

    assert hit1 is False and hit2 is True       # first miss, second hit
    assert calls["n"] == 1                       # fetch ran exactly once
    assert r1.returned == r2.returned == 3


def test_different_query_is_a_cache_miss(db):
    cache = SnapshotCache(db)
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return _response(1)

    cache.get_or_fetch("faers_search", FaersSearchRequest(drug="montelukast"), fetch, FaersSearchData)
    cache.get_or_fetch("faers_search", FaersSearchRequest(drug="semaglutide"), fetch, FaersSearchData)
    assert calls["n"] == 2  # different query -> different key -> re-fetch


def test_invalidate_forces_refetch(db):
    cache = SnapshotCache(db)
    req = FaersSearchRequest(drug="montelukast")
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return _response(2)

    cache.get_or_fetch("faers_search", req, fetch, FaersSearchData)
    cache.invalidate(make_cache_key("faers_search", req))
    cache.get_or_fetch("faers_search", req, fetch, FaersSearchData)
    assert calls["n"] == 2
