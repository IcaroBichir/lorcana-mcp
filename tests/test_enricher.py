"""Tests for enricher.py — pure helper functions (no network calls)."""
from __future__ import annotations

import csv
import io
from unittest.mock import patch

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


# ── enrich_csv — refresh_prices ─────────────────────────────────────────────────

_RAW_HEADER = [
    "Product ID", "TCGplayer Id", "Product Line", "Set Name", "Product Name",
    "Title", "Number", "Rarity", "Condition", "Printing",
    "TCG Market Price", "TCG Direct Low", "TCG Low Price With Shipping", "TCG Low Price",
    "Total Quantity", "Add to Quantity", "TCG Marketplace Price", "Photo URL",
]


def _write_raw_csv(tmp_path, product_id="692010", market_price="3.00"):
    row = {h: "" for h in _RAW_HEADER}
    row.update({
        # Product ID is TCGPlayer's actual product/listing ID — the one that
        # matches LorcanaJSON's externalLinks.tcgPlayerId and tcgcsv.com's
        # productId. TCGplayer Id is a different, unrelated secondary ID —
        # deliberately set to something that would never match, to catch any
        # regression back to keying off the wrong column.
        "Product ID": product_id, "TCGplayer Id": "9272345", "Product Line": "Disney Lorcana",
        "Set Name": "The First Chapter", "Product Name": "Goofy - Musketeer",
        "Number": "4/204", "Rarity": "Uncommon", "Condition": "Near Mint", "Printing": "Normal",
        "TCG Market Price": market_price, "Add to Quantity": "2",
    })
    path = tmp_path / "raw.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_RAW_HEADER)
        writer.writeheader()
        writer.writerow(row)
    return path


def _api_card():
    return {
        "Color": "Amber", "Cost": 5, "Type": "Character", "Classifications": "Dreamborn/Hero",
        "Strength": 3, "Willpower": 6, "Lore": 1, "Inkable": True, "Body_Text": "",
    }


class TestEnrichCsvRefreshPrices:
    def test_refresh_prices_overwrites_market_price(self, tmp_path):
        from lorcana_mcp.enricher import enrich_csv
        raw = _write_raw_csv(tmp_path, product_id="692010", market_price="3.00")

        with patch("lorcana_mcp.enricher.load_all_data",
                   return_value=({("The First Chapter", 4): _api_card()}, {}, [])), \
             patch("lorcana_mcp.enricher.fetch_tcgcsv_prices", return_value={692010: 9.99}):
            result = enrich_csv(str(raw), refresh_prices=True)

        assert result["prices_refreshed"] == 1
        with open(result["enriched_path"]) as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["TCG Market Price"] == "9.99"

    def test_refresh_prices_false_leaves_original_price(self, tmp_path):
        from lorcana_mcp.enricher import enrich_csv
        raw = _write_raw_csv(tmp_path, product_id="692010", market_price="3.00")

        with patch("lorcana_mcp.enricher.load_all_data",
                   return_value=({("The First Chapter", 4): _api_card()}, {}, [])), \
             patch("lorcana_mcp.enricher.fetch_tcgcsv_prices") as mock_prices:
            result = enrich_csv(str(raw), refresh_prices=False)

        mock_prices.assert_not_called()
        assert result["prices_refreshed"] is None
        with open(result["enriched_path"]) as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["TCG Market Price"] == "3.00"

    def test_refresh_prices_no_match_keeps_original(self, tmp_path):
        from lorcana_mcp.enricher import enrich_csv
        raw = _write_raw_csv(tmp_path, product_id="692010", market_price="3.00")

        with patch("lorcana_mcp.enricher.load_all_data",
                   return_value=({("The First Chapter", 4): _api_card()}, {}, [])), \
             patch("lorcana_mcp.enricher.fetch_tcgcsv_prices", return_value={99999: 1.0}):
            result = enrich_csv(str(raw), refresh_prices=True)

        assert result["prices_refreshed"] == 0
        with open(result["enriched_path"]) as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["TCG Market Price"] == "3.00"

    def test_refresh_prices_missing_product_id_skipped(self, tmp_path):
        from lorcana_mcp.enricher import enrich_csv
        raw = _write_raw_csv(tmp_path, product_id="", market_price="3.00")

        with patch("lorcana_mcp.enricher.load_all_data",
                   return_value=({("The First Chapter", 4): _api_card()}, {}, [])), \
             patch("lorcana_mcp.enricher.fetch_tcgcsv_prices", return_value={692010: 9.99}):
            result = enrich_csv(str(raw), refresh_prices=True)

        assert result["prices_refreshed"] == 0
        with open(result["enriched_path"]) as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["TCG Market Price"] == "3.00"

    def test_refresh_prices_does_not_match_on_tcgplayer_id_column(self, tmp_path):
        # regression guard: "TCGplayer Id" (9272345) must NOT be used for matching
        from lorcana_mcp.enricher import enrich_csv
        raw = _write_raw_csv(tmp_path, product_id="692010", market_price="3.00")

        with patch("lorcana_mcp.enricher.load_all_data",
                   return_value=({("The First Chapter", 4): _api_card()}, {}, [])), \
             patch("lorcana_mcp.enricher.fetch_tcgcsv_prices", return_value={9272345: 9.99}):
            result = enrich_csv(str(raw), refresh_prices=True)

        assert result["prices_refreshed"] == 0
        with open(result["enriched_path"]) as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["TCG Market Price"] == "3.00"
