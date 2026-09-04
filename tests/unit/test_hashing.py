"""Tests for deterministic content hashing --- the backbone of dedup and recompute."""

from __future__ import annotations

from dsi.hashing import canonical_hash, canonical_json, hash_of_hashes
from dsi.domain.evidence import AdverseEventReport


def test_canonical_json_is_key_order_independent():
    a = {"b": 1, "a": 2, "c": {"y": 1, "x": 2}}
    b = {"c": {"x": 2, "y": 1}, "a": 2, "b": 1}
    assert canonical_json(a) == canonical_json(b)


def test_canonical_hash_is_deterministic():
    payload = {"drug": "montelukast", "n": 3}
    assert canonical_hash(payload) == canonical_hash(dict(payload))


def test_canonical_hash_changes_with_content():
    assert canonical_hash({"n": 1}) != canonical_hash({"n": 2})


def test_hash_of_hashes_is_order_independent():
    h = ["aaa", "bbb", "ccc"]
    assert hash_of_hashes(h) == hash_of_hashes(list(reversed(h)))


def test_hash_of_hashes_distinguishes_sets():
    assert hash_of_hashes(["a", "b"]) != hash_of_hashes(["a", "c"])


def test_pydantic_model_hashes_stably():
    r1 = AdverseEventReport(report_id="1", report_version=1)
    r2 = AdverseEventReport(report_id="1", report_version=1)
    assert canonical_hash(r1) == canonical_hash(r2)
    r3 = AdverseEventReport(report_id="1", report_version=2)
    assert canonical_hash(r1) != canonical_hash(r3)
