"""Tests for cache.py."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Redirect cache I/O to a temp directory for every test."""
    cf = tmp_path / "test_cache.json"
    monkeypatch.setattr("lorcana_mcp.cache._CACHE_DIR", tmp_path)
    monkeypatch.setattr("lorcana_mcp.cache._CACHE_FILE", cf)


# ── get / set round-trip ───────────────────────────────────────────────────────

def test_set_get_list():
    from lorcana_mcp import cache as c
    c.set("key", [{"a": 1}, {"b": 2}])
    assert c.get("key") == [{"a": 1}, {"b": 2}]


def test_get_missing_key_returns_none():
    from lorcana_mcp import cache as c
    assert c.get("does_not_exist") is None


def test_two_keys_are_independent():
    from lorcana_mcp import cache as c
    c.set("k1", [1])
    c.set("k2", [2])
    assert c.get("k1") == [1]
    assert c.get("k2") == [2]


def test_overwrite_key():
    from lorcana_mcp import cache as c
    c.set("k", [1, 2, 3])
    c.set("k", [9, 8, 7])
    assert c.get("k") == [9, 8, 7]


# ── TTL expiry ─────────────────────────────────────────────────────────────────

def test_get_returns_none_after_ttl_expired():
    from lorcana_mcp import cache as c
    with patch("lorcana_mcp.cache.time") as t:
        t.time.return_value = 1_000_000.0
        c.set("expiring", [1, 2])
    with patch("lorcana_mcp.cache.time") as t:
        t.time.return_value = 1_000_000.0 + 86_401  # just past 24h
        assert c.get("expiring") is None


def test_get_returns_value_before_ttl():
    from lorcana_mcp import cache as c
    with patch("lorcana_mcp.cache.time") as t:
        t.time.return_value = 1_000_000.0
        c.set("fresh", [42])
    with patch("lorcana_mcp.cache.time") as t:
        t.time.return_value = 1_000_000.0 + 3_600  # 1 hour later
        assert c.get("fresh") == [42]


# ── clear ──────────────────────────────────────────────────────────────────────

def test_clear_returns_count():
    from lorcana_mcp import cache as c
    c.set("a", [1])
    c.set("b", [2])
    c.set("d", [3])
    assert c.clear() == 3


def test_clear_on_empty_returns_zero():
    from lorcana_mcp import cache as c
    assert c.clear() == 0


def test_clear_removes_all_entries():
    from lorcana_mcp import cache as c
    c.set("x", [1])
    c.clear()
    assert c.get("x") is None


# ── stats ──────────────────────────────────────────────────────────────────────

def test_stats_keys():
    from lorcana_mcp import cache as c
    s = c.stats()
    assert set(s.keys()) == {"entries", "expired", "size_bytes"}


def test_stats_empty_cache():
    from lorcana_mcp import cache as c
    s = c.stats()
    assert s["entries"] == 0
    assert s["expired"] == 0
    assert s["size_bytes"] == 0


def test_stats_counts_expired():
    from lorcana_mcp import cache as c
    with patch("lorcana_mcp.cache.time") as t:
        t.time.return_value = 1_000_000.0
        c.set("live", [1])
        c.set("dead", [2])

    with patch("lorcana_mcp.cache.time") as t:
        t.time.return_value = 1_000_000.0 + 86_401
        s = c.stats()

    assert s["entries"] == 2
    assert s["expired"] == 2
