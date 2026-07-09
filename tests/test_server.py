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
        "enrich_csv", "lookup_card", "resolve_card", "search_cards", "filter_collection",
        "audit_csv", "analyze_deck",
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
