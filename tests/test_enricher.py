"""Tests for enricher.py — pure helper functions (no network calls)."""
from __future__ import annotations

import csv
import io

import pytest

from lorcana_mcp.enricher import _num_str, _num_int, _build_dreamborn_rows
from lorcana_mcp.server import _filter_poorcana


# ── number parsing ─────────────────────────────────────────────────────────────

class TestNumStr:
    def test_strips_denominator(self):
        assert _num_str("61/204") == "61"

    def test_epic_card_number(self):
        assert _num_str("206/204") == "206"

    def test_already_plain(self):
        assert _num_str("61") == "61"

    def test_empty(self):
        assert _num_str("") == ""

    def test_whitespace_stripped(self):
        assert _num_str(" 42/204 ") == "42"


class TestNumInt:
    def test_parses_with_denominator(self):
        assert _num_int("61/204") == 61

    def test_parses_plain(self):
        assert _num_int("61") == 61

    def test_returns_none_on_non_numeric(self):
        assert _num_int("abc") is None

    def test_returns_none_on_empty(self):
        assert _num_int("") is None


# ── _filter_poorcana ───────────────────────────────────────────────────────────

_BASE_ROW = {
    "Product Name": "Test Card",
    "Ink": "Amber",
    "Ink Cost": "2",
    "Rarity": "Common",
    "Add to Quantity": "1",
    "Card Type": "Character",
    "Set Name": "The First Chapter",
}


def _row(**kwargs):
    return {**_BASE_ROW, **kwargs}


class TestFilterPoorcana:
    def test_includes_common(self):
        rows = [_row(Rarity="Common")]
        result = _filter_poorcana(rows)
        assert "Test Card" in result

    def test_includes_uncommon(self):
        rows = [_row(Rarity="Uncommon")]
        result = _filter_poorcana(rows)
        assert "Test Card" in result

    def test_excludes_rare(self):
        rows = [_row(Rarity="Rare")]
        result = _filter_poorcana(rows)
        assert "Test Card" not in result

    def test_excludes_legendary(self):
        rows = [_row(Rarity="Legendary")]
        result = _filter_poorcana(rows)
        assert "Test Card" not in result

    def test_counts_unique_and_copies(self):
        rows = [
            _row(Product_Name="Card A", **{"Product Name": "Card A", "Add to Quantity": "3", "Rarity": "Common"}),
            _row(Product_Name="Card B", **{"Product Name": "Card B", "Add to Quantity": "2", "Rarity": "Uncommon"}),
            _row(Product_Name="Card C", **{"Product Name": "Card C", "Add to Quantity": "1", "Rarity": "Rare"}),
        ]
        result = _filter_poorcana(rows)
        assert "2 unique cards" in result
        assert "5 total copies" in result

    def test_empty_collection_message(self):
        rows = [_row(Rarity="Legendary"), _row(Rarity="Super Rare")]
        result = _filter_poorcana(rows)
        assert "No Common or Uncommon" in result


# ── _build_dreamborn_rows ──────────────────────────────────────────────────────

class TestBuildDreambornRows:
    def _make_row(self, set_name, number, printing="Normal", qty="2"):
        return {
            "Set Name": set_name,
            "Number": number,
            "Printing": printing,
            "Add to Quantity": qty,
            "Product Name": "Test Card",
            "Ink": "Amber",
        }

    def test_normal_printing(self):
        rows = [self._make_row("The First Chapter", "61/204", "Normal", "2")]
        result = _build_dreamborn_rows(rows)
        assert result["rows"][0]["Variant"] == "normal"
        assert result["rows"][0]["Count"] == 2

    def test_holofoil_printing(self):
        rows = [self._make_row("The First Chapter", "61/204", "Holofoil", "1")]
        result = _build_dreamborn_rows(rows)
        assert result["rows"][0]["Variant"] == "foil"

    def test_cold_foil_printing(self):
        rows = [self._make_row("The First Chapter", "61/204", "Cold Foil", "1")]
        result = _build_dreamborn_rows(rows)
        assert result["rows"][0]["Variant"] == "foil"

    def test_correct_set_number(self):
        rows = [self._make_row("Rise of the Floodborn", "10/204", "Normal", "1")]
        result = _build_dreamborn_rows(rows)
        assert result["rows"][0]["Set Number"] == 2

    def test_zero_quantity_excluded(self):
        rows = [self._make_row("The First Chapter", "61/204", "Normal", "0")]
        result = _build_dreamborn_rows(rows)
        assert result["rows"] == []

    def test_promo_goes_to_skipped(self):
        rows = [{
            "Set Name": "Disney Lorcana Promo Cards",
            "Number": "57",
            "Printing": "Holofoil",
            "Add to Quantity": "1",
            "Product Name": "Buzz Lightyear - Space Ranger",
            "Ink": "Emerald",
        }]
        result = _build_dreamborn_rows(rows)
        assert result["rows"] == []
        assert len(result["promos"]) == 1
        assert result["promos"][0]["name"] == "Buzz Lightyear - Space Ranger"
