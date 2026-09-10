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


# ── event mode (full standings + decklists) ──────────────────────────────────

def test_get_meta_event_returns_full_decklists():
    from lorcana_mcp.server import get_meta
    out = get_meta(event="nac")
    assert "North American Championship 2026" in out
    assert "## Final standings" in out
    assert "## Decklists" in out
    assert "4x Darkwing Duck - Crime Fighter" in out  # a real card line
    assert "(60 cards)" in out                        # per-list total footer


def test_get_meta_event_key_and_fragment_both_resolve():
    from lorcana_mcp.server import get_meta
    by_key = get_meta(event="dlc-kobe-2026")
    by_frag = get_meta(event="kobe")
    assert by_key == by_frag
    assert "Core JA" in by_key


def test_get_meta_ambiguous_event_lists_candidates():
    from lorcana_mcp.server import get_meta
    out = get_meta(event="2026")
    assert "matches several events" in out
    assert "nac-2026" in out


def test_get_meta_unknown_event_lists_all():
    from lorcana_mcp.server import get_meta
    out = get_meta(event="does-not-exist")
    assert "No tournament matches" in out
    assert "nac-2026" in out


def test_get_meta_plain_output_points_at_events():
    from lorcana_mcp.server import get_meta
    out = get_meta()
    assert "Full standings + decklists" in out
    assert 'get_meta(event="nac")' in out


def test_every_unflagged_bundled_decklist_sums_to_60():
    """Any bundled list whose count is off from 60 must say so in its label
    or note (a '⚠'), so consumers aren't misled."""
    from lorcana_mcp.tournaments import TOURNAMENTS, _leading_count
    for key, t in TOURNAMENTS.items():
        for d in t["decklists"]:
            total = sum(_leading_count(c) for c in d["cards"])
            if total == 0:
                continue  # partial "notable cards" list, no counts on purpose
            flagged = "⚠" in (d["label"] + (d.get("note") or ""))
            if flagged:
                assert total != 60, f'{key} / {d["label"]}: flagged but actually 60'
            else:
                assert total == 60, f'{key} / {d["label"]}: {total} cards, not flagged'
