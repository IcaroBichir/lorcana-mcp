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
    assert names == {"enrich_csv", "lookup_card", "filter_collection", "audit_csv", "analyze_deck"}


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
