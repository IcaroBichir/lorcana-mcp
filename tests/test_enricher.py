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

    def test_promo_with_known_dreamborn_row_is_resolved(self):
        # Verified against a real dreamborn.ink export (promos-only), not just the
        # card browser display — Set Number is the plain LJ set code the promo drop
        # is tied to, and Card Number is the full "N/Series" string as one field.
        rows = [{
            "Set Name": "Disney Lorcana Promo Cards",
            "Number": "57",
            "Printing": "Holofoil",
            "Add to Quantity": "1",
            "Product Name": "Buzz Lightyear - Space Ranger",
            "Ink": "Emerald",
        }]
        result = _build_dreamborn_rows(rows)
        assert result["promos"] == []
        assert result["rows"] == [{
            "Set Number": 12, "Card Number": "57/P3", "Variant": "foil", "Count": 1,
        }]

    def test_promo_disambiguated_by_tcgplayer_number(self):
        # "Minnie Mouse - Pirate Lookout" has two distinct promo prints in dreamborn's
        # export (12/P2 and 17/P3) — TCGPlayer's own promo Number ("12" here) is what
        # picks the right one.
        rows = [{
            "Set Name": "Disney Lorcana Promo Cards",
            "Number": "12",
            "Printing": "Cold Foil",
            "Add to Quantity": "1",
            "Product Name": "Minnie Mouse - Pirate Lookout",
            "Ink": "Ruby",
        }]
        result = _build_dreamborn_rows(rows)
        assert result["promos"] == []
        assert result["rows"] == [{
            "Set Number": 6, "Card Number": "12/P2", "Variant": "foil", "Count": 1,
        }]

    def test_promo_name_with_trailing_paren_suffix_is_normalized(self):
        # TCGPlayer names this printing "Woody - Jungle Guide (Store Championship
        # Participant)" — dreamborn's export just calls it "Woody - Jungle Guide".
        rows = [{
            "Set Name": "Disney Lorcana Promo Cards",
            "Number": "53",
            "Printing": "Normal",
            "Add to Quantity": "5",
            "Product Name": "Woody - Jungle Guide (Store Championship Participant)",
            "Ink": "Amber",
        }]
        result = _build_dreamborn_rows(rows)
        assert result["promos"] == []
        assert result["rows"] == [{
            "Set Number": 12, "Card Number": "53/P3", "Variant": "normal", "Count": 5,
        }]

    def test_unknown_promo_goes_to_skipped(self):
        rows = [{
            "Set Name": "Disney Lorcana Promo Cards",
            "Number": "4",
            "Printing": "Holofoil",
            "Add to Quantity": "1",
            "Product Name": "Maleficent - Not A Real Promo",
            "Ink": "Amethyst",
        }]
        result = _build_dreamborn_rows(rows)
        assert result["rows"] == []
        assert len(result["promos"]) == 1
        assert result["promos"][0]["name"] == "Maleficent - Not A Real Promo"


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


# ── Illumineer's Quest rows: playable reprints vs quest-only cards ─────────────

_IQ = "Illumineer's Quest: The Great Hunny Rescue"
_FOIL = {"Set Name": _IQ, "Number": "243/204", "Printing": "Cold Foil", "Add to Quantity": "1",
         "Product Name": "Mr. Incredible - Super Strong", "Ink": "Ruby", "Card Type": "Character",
         "Rarity": "Common"}
_VINE = {"Set Name": _IQ, "Number": "7/37", "Printing": "Normal", "Add to Quantity": "1",
         "Product Name": "Yzma - Made by the Vine", "Ink": "", "Card Type": "", "Rarity": "Common"}


class TestQuestCards:
    def test_set_and_row_classification(self):
        from lorcana_mcp.api import is_quest_set, is_quest_only_row
        assert is_quest_set(_IQ) and is_quest_set("Illumineer's Quest: Deep Trouble")
        assert not is_quest_set("Hyperia City") and not is_quest_set("")
        assert not is_quest_only_row(_FOIL)
        assert is_quest_only_row(_VINE)
        assert not is_quest_only_row({"Set Name": "Hyperia City", "Card Type": ""})

    def test_dreamborn_rows(self):
        lj = [{"fullName": "Mr. Incredible - Super Strong", "setCode": "12", "number": 127},
              {"fullName": "Mr. Incredible - Super Strong", "setCode": "12", "number": 243}]
        result = _build_dreamborn_rows([_FOIL, _VINE], lj)
        # Reprint filed under the set/number printed on the card; quest-only card left out.
        assert result["rows"] == [{"Set Number": 12, "Card Number": 243, "Variant": "foil", "Count": 1}]
        status = {q["name"]: (q["playable"], q["dreamborn"]) for q in result["quest"]}
        assert status == {"Mr. Incredible - Super Strong": (True, "12, 243"),
                          "Yzma - Made by the Vine": (False, "")}

    def test_reprint_without_exact_number_is_listed_not_guessed(self):
        lj = [{"fullName": "Mr. Incredible - Super Strong", "setCode": "12", "number": 127}]
        result = _build_dreamborn_rows([_FOIL], lj)
        assert result["rows"] == [] and result["quest"][0]["dreamborn"] == ""

    def test_foil_borrows_regular_printing_stats(self):
        from lorcana_mcp.enricher import _resolve_quest
        lj = [{"fullName": "Mr. Incredible - Super Strong", "color": "Ruby", "cost": 5,
               "type": "Character", "strength": 5, "willpower": 5, "lore": 2, "inkwell": True}]
        unmatched = []
        out = _resolve_quest(_IQ, "243", "Mr. Incredible - Super Strong", lj, unmatched)
        assert out[0] == "Ruby" and str(out[1]) == "5" and not unmatched

    def test_vine_card_reported_quest_only(self):
        from lorcana_mcp.enricher import _resolve_quest
        unmatched = []
        _resolve_quest(_IQ, "7", "Yzma - Made by the Vine", [], unmatched)
        assert "quest-only" in unmatched[0]

    def test_poorcana(self):
        assert "1 unique" in _filter_poorcana([_FOIL]) or "Mr. Incredible" in _filter_poorcana([_FOIL])
        assert "No Common or Uncommon" in _filter_poorcana([_VINE])

    def test_owned_counts(self, tmp_path):
        from lorcana_mcp.server import _load_collection_csv
        p = tmp_path / "c.csv"
        cols = ["Set Name", "Product Name", "Card Type", "Add to Quantity", "TCG Market Price"]
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerow({"Set Name": "Wilds Unknown", "Product Name": "Mr. Incredible - Super Strong",
                        "Card Type": "Character", "Add to Quantity": "3", "TCG Market Price": "1.00"})
            w.writerow({k: _FOIL.get(k, "7.53") for k in cols})
            w.writerow({k: _VINE.get(k, "0.50") for k in cols})
        counts, _ = _load_collection_csv(str(p))
        assert counts["mr. incredible - super strong"] == 4
        assert "yzma - made by the vine" not in counts
