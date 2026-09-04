"""Change detection driving cache invalidation / staleness."""

from __future__ import annotations

from dsi.persistence.staleness import detect_changes, snapshot_is_stale


def test_detect_changes_added_changed_removed():
    old = {"faers:R1": "h1", "label:boxed": "hb", "faers:R2": "h2"}
    new = {"faers:R1": "h1", "label:boxed": "hb2", "faers:R3": "h3"}
    cs = detect_changes(old, new)
    assert cs.added == ["faers:R3"]
    assert cs.changed == ["label:boxed"]   # same key, new content hash
    assert cs.removed == ["faers:R2"]
    assert cs.any is True
    assert cs.affected_keys() == ["faers:R2", "faers:R3", "label:boxed"]


def test_no_changes():
    snap = {"a": "1", "b": "2"}
    cs = detect_changes(snap, dict(snap))
    assert cs.any is False
    assert cs.affected_keys() == []


def test_snapshot_version_staleness():
    assert snapshot_is_stale("2020Q1", "2020Q2") is True
    assert snapshot_is_stale("2020Q1", "2020Q1") is False
    assert snapshot_is_stale(None, "2020Q1") is True
