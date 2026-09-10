"""Tests for meta.py — no network involved, this is a static snapshot."""
from __future__ import annotations

from lorcana_mcp.meta import (
    CORE_TIER_LIST, RECENT_TOURNAMENTS, META_SNAPSHOT_DATE, format_meta_snapshot,
)


def test_tier_list_covers_all_15_two_ink_pairs_exactly_once():
    inks = {"Amber", "Amethyst", "Emerald", "Ruby", "Sapphire", "Steel"}
    seen = set()
    for row in CORE_TIER_LIST:
        pair = frozenset(p for p in row["pair"])
        assert len(pair) == 2, row["pair"]
        assert pair <= inks, row["pair"]
        assert pair not in seen, f"duplicate pair {row['pair']}"
        seen.add(pair)
    # 6 inks choose 2 = 15 combinations
    assert len(seen) == 15


def test_every_row_has_required_fields():
    required = {"pair", "archetype", "tier", "meta_share", "style", "verified_recent_event"}
    for row in CORE_TIER_LIST:
        assert required <= row.keys(), row


def test_format_meta_snapshot_no_filter_includes_date_and_all_rows():
    out = format_meta_snapshot()
    assert META_SNAPSHOT_DATE in out
    assert "not live data" in out
    for row in CORE_TIER_LIST:
        a, b = row["pair"]
        assert f"{a}/{b}" in out


def test_format_meta_snapshot_includes_tournament_summary():
    out = format_meta_snapshot()
    for t in RECENT_TOURNAMENTS:
        assert t["name"] in out
        assert t["headline"] in out


def test_format_meta_snapshot_filters_to_one_pair():
    out = format_meta_snapshot("Emerald,Steel")
    assert "Emerald/Steel" in out
    assert "Amethyst/Sapphire" not in out
    # tournament summary still included even when filtered
    assert "Recent tournament results" in out


def test_format_meta_snapshot_filter_is_order_and_case_insensitive():
    a = format_meta_snapshot("emerald, steel")
    b = format_meta_snapshot("Steel/Emerald")
    assert a == b
    assert "Emerald/Steel" in a


def test_format_meta_snapshot_rejects_wrong_arity():
    out = format_meta_snapshot("Emerald")
    assert "exactly two ink colors" in out
    out = format_meta_snapshot("Emerald,Steel,Ruby")
    assert "exactly two ink colors" in out


def test_format_meta_snapshot_unknown_pair_lists_valid_options():
    out = format_meta_snapshot("Fire,Water")
    assert "No tier-list entry" in out
    assert "Emerald/Steel" in out  # valid pairs listed as a hint
