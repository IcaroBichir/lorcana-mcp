"""Tests for server.py — tool registration and format filtering (no network)."""
from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# ── tool registration ──────────────────────────────────────────────────────────

def test_all_tools_registered():
    from lorcana_mcp.server import mcp
    names = {t.name for t in mcp._tool_manager.list_tools()}
    assert names == {
        "enrich_csv", "lookup_card", "resolve_card", "search_cards", "find_song_synergies",
        "filter_collection", "audit_csv", "analyze_deck", "what_am_i_missing", "build_deck",
    }


# ── filter_collection — poorcana (no network needed) ──────────────────────────

_ENRICHED_HEADER = [
    "Product ID", "TCGplayer Id", "Product Line", "Set Name", "Product Name",
    "Ink", "Ink Cost", "Card Type", "Subtypes", "Strength", "Willpower", "Lore Points",
    "Inkable", "Keywords", "Abilities",
    "Title", "Number", "Rarity", "Condition", "Printing",
    "TCG Market Price", "TCG Direct Low", "TCG Low Price With Shipping", "TCG Low Price",
    "Total Quantity", "Add to Quantity", "TCG Marketplace Price", "Photo URL",
]


def _make_csv(*card_rows: dict) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_ENRICHED_HEADER, extrasaction="ignore")
    writer.writeheader()
    for r in card_rows:
        row = {h: "" for h in _ENRICHED_HEADER}
        row.update(r)
        writer.writerow(row)
    return buf.getvalue()


@pytest.fixture()
def csv_file(tmp_path):
    def _make(cards):
        p = tmp_path / "collection.csv"
        p.write_text(_make_csv(*cards))
        return str(p)
    return _make


class TestFilterCollectionPoorcana:
    def test_common_cards_included(self, csv_file):
        from lorcana_mcp.server import filter_collection
        path = csv_file([{
            "Product Name": "Goofy - Musketeer", "Ink": "Steel", "Ink Cost": "2",
            "Card Type": "Character", "Rarity": "Common",
            "Set Name": "The First Chapter", "Add to Quantity": "4",
        }])
        result = filter_collection(path, "poorcana")
        assert "Goofy - Musketeer" in result

    def test_legendary_cards_excluded(self, csv_file):
        from lorcana_mcp.server import filter_collection
        path = csv_file([{
            "Product Name": "Elsa - Spirit of Winter", "Ink": "Amethyst", "Ink Cost": "8",
            "Card Type": "Character", "Rarity": "Legendary",
            "Set Name": "The First Chapter", "Add to Quantity": "1",
        }])
        result = filter_collection(path, "poorcana")
        assert "Elsa - Spirit of Winter" not in result

    def test_mixed_rarities(self, csv_file):
        from lorcana_mcp.server import filter_collection
        path = csv_file([
            {"Product Name": "Common Card", "Ink": "Amber", "Ink Cost": "1",
             "Card Type": "Character", "Rarity": "Common",
             "Set Name": "The First Chapter", "Add to Quantity": "2"},
            {"Product Name": "Rare Card", "Ink": "Ruby", "Ink Cost": "4",
             "Card Type": "Character", "Rarity": "Rare",
             "Set Name": "The First Chapter", "Add to Quantity": "1"},
        ])
        result = filter_collection(path, "poorcana")
        assert "Common Card" in result
        assert "Rare Card" not in result

    def test_invalid_format_returns_error(self, csv_file):
        from lorcana_mcp.server import filter_collection
        path = csv_file([])
        result = filter_collection(path, "standard")
        assert "Unknown format" in result

    def test_missing_file_returns_error(self):
        from lorcana_mcp.server import filter_collection
        result = filter_collection("/nonexistent/path.csv", "poorcana")
        assert "Error" in result


# ── resolve_card ───────────────────────────────────────────────────────────────

def _lj(name, version, setCode="1", **extra):
    full_name = f"{name} - {version}" if version else name
    card = {"name": name, "version": version, "fullName": full_name, "setCode": setCode,
            "cost": extra.pop("cost", 3), "strength": None, "willpower": None, "lore": None,
            "inkwell": True, "color": "Amber", "type": "Character", "subtypes": [], "abilities": []}
    card.update(extra)
    return card


_RESOLVE_CARDS = [
    _lj("Goofy", "Musketeer", setCode="1"),
    _lj("Goofy", "Musketeer Swordsman", setCode="4"),
    _lj("Elsa", "Snow Queen", setCode="9"),
    _lj("Elsa", "Spirit of Winter", setCode="5"),
    _lj("Pete", "Bad Guy", setCode="1"),
    _lj("Pete", "Freebooter", setCode="6"),
]


class TestResolveCard:
    def test_unambiguous_query_returns_full_detail(self):
        from lorcana_mcp.server import resolve_card
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_RESOLVE_CARDS), \
             patch("lorcana_mcp.server._duels_lookup_card", return_value=None):
            result = resolve_card("goofy musketeer")
        assert "Goofy - Musketeer" in result
        assert "Goofy - Musketeer Swordsman" not in result

    def test_ambiguous_query_lists_top_candidates_with_confidence(self):
        from lorcana_mcp.server import resolve_card
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_RESOLVE_CARDS):
            result = resolve_card("elsa")
        assert "Multiple cards could match" in result
        assert "% match" in result
        assert "Elsa - Snow Queen" in result
        assert "Elsa - Spirit of Winter" in result

    def test_nonsense_query_not_found(self):
        from lorcana_mcp.server import resolve_card
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_RESOLVE_CARDS):
            result = resolve_card("xyzabc123")
        assert "No card found" in result


# ── search_cards ────────────────────────────────────────────────────────────────

def _lj_card(name, cost, ctype, color, rarity="Common", setCode="12",
             strength=None, willpower=None, lore=None, subtypes=None,
             colors=None, abilities=None, fullText=""):
    return {
        "fullName": name, "cost": cost, "type": ctype, "color": color, "colors": colors,
        "rarity": rarity, "setCode": setCode, "strength": strength, "willpower": willpower,
        "lore": lore, "subtypes": subtypes or [], "abilities": abilities or [], "fullText": fullText,
    }


_SEARCH_CARDS = [
    _lj_card("Goofy - Musketeer", 2, "Character", "Steel", strength=2, willpower=3, lore=1),
    _lj_card("Elsa - Spirit of Winter", 8, "Character", "Amethyst",
             rarity="Legendary", strength=6, willpower=8, lore=3,
             abilities=[{"type": "keyword", "keyword": "Evasive", "fullText": "Evasive"}]),
    _lj_card("Rhino - Motivational Speaker", 3, "Character", "Amber-Steel",
             colors=["Amber", "Steel"], strength=2, willpower=2, lore=1),
]


class TestSearchCards:
    def test_no_filters_lists_all_grouped_by_ink(self):
        from lorcana_mcp.server import search_cards
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=_SEARCH_CARDS):
            result = search_cards()
        assert "Goofy - Musketeer" in result
        assert "Elsa - Spirit of Winter" in result
        assert "Rhino - Motivational Speaker" in result
        assert "### Steel" in result
        assert "### Amethyst" in result
        assert "### Amber/Steel" in result

    def test_filter_by_color(self):
        from lorcana_mcp.server import search_cards
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=_SEARCH_CARDS):
            result = search_cards(colors="Amethyst")
        assert "Elsa - Spirit of Winter" in result
        assert "Goofy - Musketeer" not in result

    def test_no_matches(self):
        from lorcana_mcp.server import search_cards
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=_SEARCH_CARDS):
            result = search_cards(rarity="Epic")
        assert "No cards matched" in result

    def test_pagination_limit(self):
        from lorcana_mcp.server import search_cards
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=_SEARCH_CARDS):
            result = search_cards(limit=1)
        assert "3 match(es)" in result
        assert "more match(es)" in result

    def test_fetch_failure_returns_error(self):
        from lorcana_mcp.server import search_cards
        with patch("lorcana_mcp.server.fetch_lorcana_json", side_effect=RuntimeError("network down")):
            result = search_cards()
        assert "Failed to fetch card data" in result


# ── find_song_synergies ──────────────────────────────────────────────────────────

def _character(name, cost, color="Amber", singer=None):
    abilities = []
    if singer is not None:
        abilities.append({"type": "keyword", "keyword": "Singer", "keywordValueNumber": singer,
                           "fullText": f"Singer {singer}"})
    base, _, version = name.partition(" - ")
    return {"fullName": name, "name": base, "version": version or None, "type": "Character",
            "cost": cost, "color": color, "colors": None, "abilities": abilities}


def _song(name, cost, setCode="11"):
    return {"fullName": name, "name": name, "version": None, "type": "Action",
            "subtypes": ["Song"], "cost": cost, "abilities": [], "setCode": setCode}


_SONG_POOL = [
    _character("Cheap Singer - Big Voice", 2, singer=5),
    _character("Plain Expensive - Heavy Hitter", 6),
    _character("Too Cheap - Small Fry", 1),
    _song("Be Our Guest", 5),
]


class TestFindSongSynergies:
    def test_resolve_by_song_name(self):
        from lorcana_mcp.server import find_song_synergies
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=_SONG_POOL), \
             patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_SONG_POOL):
            result = find_song_synergies(song_name="Be Our Guest")
        assert "Be Our Guest" in result
        assert "Cheap Singer - Big Voice" in result
        assert "Plain Expensive - Heavy Hitter" in result
        assert "Too Cheap - Small Fry" not in result

    def test_resolve_by_cost_threshold(self):
        from lorcana_mcp.server import find_song_synergies
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=_SONG_POOL):
            result = find_song_synergies(cost=5)
        assert "Cheap Singer - Big Voice" in result
        assert "Plain Expensive - Heavy Hitter" in result
        assert "Too Cheap - Small Fry" not in result

    def test_song_name_and_cost_both_given_errors(self):
        from lorcana_mcp.server import find_song_synergies
        result = find_song_synergies(song_name="Be Our Guest", cost=5)
        assert "not both" in result

    def test_neither_song_name_nor_cost_errors(self):
        from lorcana_mcp.server import find_song_synergies
        result = find_song_synergies()
        assert "Provide either" in result

    def test_resolved_non_song_card_errors(self):
        from lorcana_mcp.server import find_song_synergies
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_SONG_POOL):
            result = find_song_synergies(song_name="Plain Expensive - Heavy Hitter")
        assert "is not a Song card" in result

    def test_song_not_found(self):
        from lorcana_mcp.server import find_song_synergies
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_SONG_POOL):
            result = find_song_synergies(song_name="Xyzabc123")
        assert "No card found" in result

    def test_no_matching_characters(self):
        from lorcana_mcp.server import find_song_synergies
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=_SONG_POOL):
            result = find_song_synergies(cost=99)
        assert "No characters can sing" in result

    def test_color_filter(self):
        from lorcana_mcp.server import find_song_synergies
        pool = _SONG_POOL + [_character("Steel Body - Tank", 6, color="Steel")]
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=pool):
            result = find_song_synergies(cost=5, colors="Steel")
        assert "Steel Body - Tank" in result
        assert "Cheap Singer - Big Voice" not in result

    def test_ownership_flagged_when_collection_given(self, csv_file):
        from lorcana_mcp.server import find_song_synergies
        path = csv_file([
            {"Product Name": "Cheap Singer - Big Voice", "Add to Quantity": "3"},
        ])
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=_SONG_POOL):
            result = find_song_synergies(cost=5, collection_csv=path)
        assert "3x" in result
        assert "Not owned" in result  # Plain Expensive isn't in the CSV

    def test_fetch_failure_returns_error(self):
        from lorcana_mcp.server import find_song_synergies
        with patch("lorcana_mcp.server.fetch_lorcana_json", side_effect=RuntimeError("network down")):
            result = find_song_synergies(cost=5)
        assert "Failed to fetch card data" in result


# ── what_am_i_missing ─────────────────────────────────────────────────────────────

def _wam_card(name, cost=2):
    return {"fullName": name, "type": "Character", "cost": cost, "color": "Steel", "colors": None,
            "inkwell": True, "subtypes": [], "abilities": []}


class TestWhatAmIMissing:
    def test_missing_collection_file_returns_error(self):
        from lorcana_mcp.server import what_am_i_missing
        result = what_am_i_missing("4x Goofy - Musketeer", "/nonexistent/path.csv")
        assert "Error" in result

    def test_empty_deck_list(self, csv_file):
        from lorcana_mcp.server import what_am_i_missing
        path = csv_file([])
        result = what_am_i_missing("", path)
        assert "No cards found" in result

    def test_fully_owned_card_listed_under_already_have(self, csv_file):
        from lorcana_mcp.server import what_am_i_missing
        path = csv_file([{"Product Name": "Goofy - Musketeer", "Add to Quantity": "4"}])
        with patch("lorcana_mcp.deck.search_card", return_value=_wam_card("Goofy - Musketeer")):
            result = what_am_i_missing("4x Goofy - Musketeer", path)
        assert "Already have" in result
        assert "Missing or short" not in result
        assert "Goofy - Musketeer" in result

    def test_missing_card_priced_and_totaled(self, csv_file):
        from lorcana_mcp.server import what_am_i_missing
        path = csv_file([])  # own nothing
        with patch("lorcana_mcp.deck.search_card", return_value=_wam_card("Goofy - Musketeer")), \
             patch("lorcana_mcp.server.fetch_lorcana_json", return_value=[]), \
             patch("lorcana_mcp.server.fetch_tcgcsv_prices", return_value={}), \
             patch("lorcana_mcp.server.cheapest_price_for_card", return_value=2.5):
            result = what_am_i_missing("4x Goofy - Musketeer", path)
        assert "Missing or short" in result
        assert "missing 4" in result
        assert "$10.00" in result  # 4 * $2.50
        assert "Estimated cost to complete: $10.00" in result

    def test_unpriceable_card_shows_unknown_price(self, csv_file):
        from lorcana_mcp.server import what_am_i_missing
        path = csv_file([])
        with patch("lorcana_mcp.deck.search_card", return_value=_wam_card("Goofy - Musketeer")), \
             patch("lorcana_mcp.server.fetch_lorcana_json", return_value=[]), \
             patch("lorcana_mcp.server.fetch_tcgcsv_prices", return_value={}), \
             patch("lorcana_mcp.server.cheapest_price_for_card", return_value=None):
            result = what_am_i_missing("4x Goofy - Musketeer", path)
        assert "price unknown" in result
        assert "Could not fetch live TCGPlayer prices" not in result

    def test_price_fetch_failure_does_not_crash(self, csv_file):
        from lorcana_mcp.server import what_am_i_missing
        path = csv_file([])
        with patch("lorcana_mcp.deck.search_card", return_value=_wam_card("Goofy - Musketeer")), \
             patch("lorcana_mcp.server.fetch_lorcana_json", side_effect=RuntimeError("network down")):
            result = what_am_i_missing("4x Goofy - Musketeer", path)
        assert "Could not fetch live TCGPlayer prices" in result

    def test_unresolved_card_listed_separately(self, csv_file):
        from lorcana_mcp.server import what_am_i_missing
        path = csv_file([])
        with patch("lorcana_mcp.deck.search_card", return_value=None):
            result = what_am_i_missing("2x Totally Fake Card", path)
        assert "Unrecognized card names" in result
        assert "2x Totally Fake Card" in result

    def test_short_card_uses_local_csv_price_no_network_call(self, csv_file):
        from lorcana_mcp.server import what_am_i_missing
        path = csv_file([
            {"Product Name": "Goofy - Musketeer", "Add to Quantity": "1", "TCG Market Price": "2.50"},
        ])
        with patch("lorcana_mcp.deck.search_card", return_value=_wam_card("Goofy - Musketeer")), \
             patch("lorcana_mcp.server.fetch_lorcana_json") as mock_lj, \
             patch("lorcana_mcp.server.fetch_tcgcsv_prices") as mock_prices:
            result = what_am_i_missing("4x Goofy - Musketeer", path)
        mock_lj.assert_not_called()
        mock_prices.assert_not_called()
        assert "missing 3" in result
        assert "$7.50" in result  # 3 missing * $2.50
        assert "Prices from your own collection CSV." in result

    def test_local_price_is_cheapest_across_owned_printings(self, csv_file):
        from lorcana_mcp.server import what_am_i_missing
        path = csv_file([
            {"Product Name": "Goofy - Musketeer", "Add to Quantity": "1", "TCG Market Price": "5.00"},
            {"Product Name": "Goofy - Musketeer", "Add to Quantity": "1", "TCG Market Price": "1.25"},
        ])
        with patch("lorcana_mcp.deck.search_card", return_value=_wam_card("Goofy - Musketeer")), \
             patch("lorcana_mcp.server.fetch_lorcana_json") as mock_lj:
            result = what_am_i_missing("4x Goofy - Musketeer", path)
        mock_lj.assert_not_called()
        assert "$2.50" in result  # 2 missing * $1.25

    def test_mixed_local_and_live_pricing_notes_both_sources(self, csv_file):
        from lorcana_mcp.server import what_am_i_missing
        path = csv_file([
            {"Product Name": "Goofy - Musketeer", "Add to Quantity": "1", "TCG Market Price": "2.50"},
        ])

        def fake_search(name, set_name=""):
            return _wam_card(name)

        with patch("lorcana_mcp.deck.search_card", side_effect=fake_search), \
             patch("lorcana_mcp.server.fetch_lorcana_json", return_value=[]), \
             patch("lorcana_mcp.server.fetch_tcgcsv_prices", return_value={}), \
             patch("lorcana_mcp.server.cheapest_price_for_card", return_value=1.0):
            result = what_am_i_missing("4x Goofy - Musketeer\n2x Elsa - Spirit of Winter", path)
        assert "live TCGPlayer snapshot" in result and "your collection where" in result


# ── enrich_csv — missing file ──────────────────────────────────────────────────

def test_enrich_csv_missing_file():
    from lorcana_mcp.server import enrich_csv
    result = enrich_csv("/nonexistent/path.csv")
    assert "Error" in result


# ── audit_csv — missing file ───────────────────────────────────────────────────

def test_audit_csv_missing_file():
    from lorcana_mcp.server import audit_csv
    result = audit_csv("/nonexistent/path.csv")
    assert "Error" in result


# ── analyze_deck — empty list (no network needed) ──────────────────────────────

def test_analyze_deck_empty_list():
    from lorcana_mcp.server import analyze_deck
    result = analyze_deck("")
    assert "No cards found" in result


# ── build_deck ──────────────────────────────────────────────────────────────────

def _bd_card(name, cost, ctype, color, set_code="9", number=1, rarity="Common",
             strength=1, willpower=1, lore=1, subtypes=None, keywords=None, full_text=""):
    abilities = [{"type": "keyword", "keyword": kw} for kw in (keywords or [])]
    return {
        "fullName": name, "cost": cost, "type": ctype, "color": color, "colors": None,
        "inkwell": True, "strength": strength, "willpower": willpower, "lore": lore,
        "subtypes": subtypes or [], "abilities": abilities, "fullText": full_text,
        "setCode": set_code, "number": number, "rarity": rarity,
    }


def _bd_duels(set_code, number, legality=("core", "infinity")):
    return {"id": f"{set_code}-{number}", "legality": list(legality)}


def _bd_abundant_pool(color="Amber", set_code="9"):
    """Enough cards spread across cost buckets and types for allocate_deck
    to reach a full 60-card deck on its own, all format-legal."""
    cards, duels = [], []
    n = 1
    for cost in (1, 2, 3, 4, 5, 6, 7):
        for ctype in ("Character", "Action", "Item", "Location"):
            for i in range(6):
                cards.append(_bd_card(f"{color} {ctype} {cost}-{i}", cost, ctype, color,
                                       set_code=set_code, number=n))
                duels.append(_bd_duels(set_code, n))
                n += 1
    return cards, duels


class TestBuildDeckValidation:
    def test_unknown_mode(self):
        from lorcana_mcp.server import build_deck
        assert "Unknown mode" in build_deck("Amber", mode="bogus")

    def test_unknown_format(self):
        from lorcana_mcp.server import build_deck
        assert "Unknown format" in build_deck("Amber", format="bogus")

    def test_unknown_ink_color(self):
        from lorcana_mcp.server import build_deck
        assert "Unknown ink color" in build_deck("NotAColor")

    def test_too_many_colors_for_core(self):
        from lorcana_mcp.server import build_deck
        result = build_deck("Amber,Ruby,Steel", format="core")
        assert "allows at most 2" in result

    def test_up_to_6_colors_allowed_for_infinity(self):
        from lorcana_mcp.server import build_deck
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=[]), \
             patch("lorcana_mcp.server.fetch_duels_ink", return_value=[]):
            result = build_deck("Amber,Amethyst,Emerald,Ruby,Sapphire,Steel", format="infinity")
        assert "allows at most" not in result

    def test_collection_mode_requires_csv(self):
        from lorcana_mcp.server import build_deck
        result = build_deck("Amber", mode="collection")
        assert "collection_csv" in result


class TestBuildDeckIdealMode:
    def test_no_csv_builds_deck_without_ownership_section(self):
        from lorcana_mcp.server import build_deck
        cards, duels = _bd_abundant_pool()
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=cards), \
             patch("lorcana_mcp.server.fetch_duels_ink", return_value=duels):
            result = build_deck("Amber", mode="ideal", format="core")
        assert "Decklist (60 cards)" in result
        assert "duels.ink import" in result
        assert "Ownership & cost to complete" not in result
        assert "Pass collection_csv" in result
        assert "heuristic curve/keyword-value deck builder" in result

    def test_with_csv_shows_ownership_and_cost_to_complete(self, csv_file):
        from lorcana_mcp.server import build_deck
        cards, duels = _bd_abundant_pool()
        path = csv_file([])  # own nothing

        def fake_search(name, set_name=""):
            return {"fullName": name}

        with patch("lorcana_mcp.deck.search_card", side_effect=fake_search), \
             patch("lorcana_mcp.server.fetch_lorcana_json", return_value=cards), \
             patch("lorcana_mcp.server.fetch_duels_ink", return_value=duels), \
             patch("lorcana_mcp.server.fetch_tcgcsv_prices", return_value={}), \
             patch("lorcana_mcp.server.cheapest_price_for_card", return_value=1.5):
            result = build_deck("Amber", mode="ideal", format="core", collection_csv=path)
        assert "Ownership & cost to complete" in result
        assert "Missing or short" in result
        assert "Estimated cost to complete" in result


class TestBuildDeckCollectionMode:
    def test_never_exceeds_owned_quantity_and_reports_honest_shortfall(self, csv_file):
        from lorcana_mcp.server import build_deck
        cards, duels = _bd_abundant_pool()
        # Own only a handful of copies across a few unique cards -> real ceiling well under 60.
        owned_rows = [
            {"Product Name": "Amber Character 1-0", "Add to Quantity": "4"},
            {"Product Name": "Amber Character 1-1", "Add to Quantity": "2"},
            {"Product Name": "Amber Item 1-0", "Add to Quantity": "1"},
        ]
        path = csv_file(owned_rows)
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=cards), \
             patch("lorcana_mcp.server.fetch_duels_ink", return_value=duels):
            result = build_deck("Amber", mode="collection", format="core", collection_csv=path)
        assert "Decklist (7 cards)" in result  # 4 + 2 + 1
        assert "Collection coverage" in result
        assert "Built 7/60" in result
        assert "Amber Character 1-2" not in result  # not owned, must not appear

    def test_full_collection_reaches_60_with_no_shortfall_note(self, csv_file):
        from lorcana_mcp.server import build_deck
        cards, duels = _bd_abundant_pool()
        owned_rows = [{"Product Name": c["fullName"], "Add to Quantity": "4"} for c in cards]
        path = csv_file(owned_rows)
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=cards), \
             patch("lorcana_mcp.server.fetch_duels_ink", return_value=duels):
            result = build_deck("Amber", mode="collection", format="core", collection_csv=path)
        assert "Decklist (60 cards)" in result
        assert "nothing to buy" in result


class TestBuildDeckMarketMode:
    def test_prices_every_card_not_just_missing(self, csv_file):
        from lorcana_mcp.server import build_deck
        cards, duels = _bd_abundant_pool()
        path = csv_file([{"Product Name": "Amber Character 1-0", "Add to Quantity": "4"}])
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=cards), \
             patch("lorcana_mcp.server.fetch_duels_ink", return_value=duels), \
             patch("lorcana_mcp.server.fetch_tcgcsv_prices", return_value={}), \
             patch("lorcana_mcp.server.cheapest_price_for_card", return_value=2.0):
            result = build_deck("Amber", mode="market", format="core", collection_csv=path)
        assert "Full deck cost" in result
        assert "collection_csv was ignored" in result
        assert "Estimated total: $120.00" in result  # 60 cards * $2.00


class TestBuildDeckRotationSafe:
    def test_restricts_to_newest_legal_group(self):
        from lorcana_mcp.server import build_deck
        safe_cards, safe_duels = _bd_abundant_pool(set_code="9")
        unsafe_card = _bd_card("Amber Old Set Card", 3, "Character", "Amber", set_code="5", number=999)
        unsafe_duels = _bd_duels("5", 999)
        sets_meta = {
            "9": {"allowedInFormats": {"Core": {"allowed": True, "rotationGroup": 3}}},
            "5": {"allowedInFormats": {"Core": {"allowed": True, "rotationGroup": 2}}},
        }
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=safe_cards + [unsafe_card]), \
             patch("lorcana_mcp.server.fetch_duels_ink", return_value=safe_duels + [unsafe_duels]), \
             patch("lorcana_mcp.server.fetch_lorcana_sets", return_value=sets_meta):
            result = build_deck("Amber", mode="ideal", format="core", rotation_safe=True)
        assert "Amber Old Set Card" not in result

    def test_noop_for_non_core_format_with_note(self):
        from lorcana_mcp.server import build_deck
        cards, duels = _bd_abundant_pool()
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=cards), \
             patch("lorcana_mcp.server.fetch_duels_ink", return_value=duels):
            result = build_deck("Amber", mode="ideal", format="infinity", rotation_safe=True)
        assert "rotation_safe is a Core-only concept" in result


class TestBuildDeckDualInkRegression:
    def test_dual_ink_card_excluded_when_second_color_outside_pair(self):
        from lorcana_mcp.server import build_deck
        cards, duels = _bd_abundant_pool()
        dual = _bd_card("Ruby Emerald Dual", 3, "Character", "Ruby-Emerald", set_code="9", number=9001)
        dual["colors"] = ["Ruby", "Emerald"]
        dual_duels = _bd_duels("9", 9001)
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=cards + [dual]), \
             patch("lorcana_mcp.server.fetch_duels_ink", return_value=duels + [dual_duels]):
            result = build_deck("Amber", mode="ideal", format="core")
        assert "Ruby Emerald Dual" not in result
