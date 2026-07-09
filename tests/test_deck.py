"""Tests for deck.py — deck list parsing and analysis (search_card mocked, no network)."""
from __future__ import annotations

from unittest.mock import patch

from lorcana_mcp.deck import parse_deck_list, analyze_deck, combine_deck_lines, what_am_i_missing


# ── parse_deck_list ─────────────────────────────────────────────────────────────

class TestParseDeckList:
    def test_x_suffix_format(self):
        assert parse_deck_list("4x Goofy - Musketeer") == [(4, "Goofy - Musketeer")]

    def test_space_format(self):
        assert parse_deck_list("4 Goofy - Musketeer") == [(4, "Goofy - Musketeer")]

    def test_implicit_qty_one(self):
        assert parse_deck_list("Goofy - Musketeer") == [(1, "Goofy - Musketeer")]

    def test_blank_lines_skipped(self):
        result = parse_deck_list("4x Goofy - Musketeer\n\n\n2x Elsa - Spirit of Winter")
        assert result == [(4, "Goofy - Musketeer"), (2, "Elsa - Spirit of Winter")]

    def test_comment_lines_skipped(self):
        text = "# My deck\n4x Goofy - Musketeer\n// another comment\n2x Elsa - Spirit of Winter"
        result = parse_deck_list(text)
        assert result == [(4, "Goofy - Musketeer"), (2, "Elsa - Spirit of Winter")]

    def test_uppercase_x(self):
        assert parse_deck_list("3X Mickey Mouse - True Friend") == [(3, "Mickey Mouse - True Friend")]

    def test_empty_text(self):
        assert parse_deck_list("") == []


# ── analyze_deck ─────────────────────────────────────────────────────────────────

def _card(name, cost, ctype, inkwell, colors, lore=0, strength=0, willpower=0, subtypes=None):
    return {
        "fullName": name,
        "cost": cost,
        "type": ctype,
        "inkwell": inkwell,
        "colors": colors if len(colors) > 1 else None,
        "color": "-".join(colors),
        "lore": lore,
        "strength": strength,
        "willpower": willpower,
        "subtypes": subtypes or [],
    }


class TestAnalyzeDeck:
    def test_empty_deck(self):
        result = analyze_deck("")
        assert result["total_cards"] == 0

    @patch("lorcana_mcp.deck.search_card")
    def test_basic_curve_and_composition(self, mock_search):
        cards = {
            "goofy": _card("Goofy - Musketeer", 2, "Character", True, ["Steel"], lore=1),
            "elsa": _card("Elsa - Spirit of Winter", 8, "Character", False, ["Amethyst"], lore=3),
        }
        mock_search.side_effect = lambda name, set_name="": (
            cards["goofy"] if "goofy" in name.lower() else cards["elsa"]
        )
        result = analyze_deck("4x Goofy - Musketeer\n2x Elsa - Spirit of Winter")

        assert result["total_cards"] == 6
        assert result["unique_cards"] == 2
        assert result["curve"]["1-2"] == 4
        assert result["curve"]["7+"] == 2
        assert result["inkable_count"] == 4
        assert result["uninkable_count"] == 2
        assert result["color_counts"] == {"Steel": 4, "Amethyst": 2}
        assert result["lore_per_turn"] == 4 * 1 + 2 * 3

    @patch("lorcana_mcp.deck.search_card")
    def test_dual_ink_card_tracked_as_combined_key(self, mock_search):
        mock_search.return_value = _card("Rhino - Motivational Speaker", 3, "Character", True, ["Amber", "Steel"])
        result = analyze_deck("4x Rhino - Motivational Speaker")
        assert result["color_counts"] == {"Amber/Steel": 4}
        assert result["legality"]["ink_colors_used"] == ["Amber", "Steel"]

    @patch("lorcana_mcp.deck.search_card")
    def test_song_type_display(self, mock_search):
        mock_search.return_value = _card("Be Our Guest", 5, "Action", True, ["Amber"], subtypes=["Song"])
        result = analyze_deck("4x Be Our Guest")
        assert result["type_counts"] == {"Action - Song": 4}

    @patch("lorcana_mcp.deck.search_card")
    def test_unresolved_card_flagged(self, mock_search):
        mock_search.return_value = None
        result = analyze_deck("4x Totally Fake Card")
        assert result["unresolved"] == [{"name": "Totally Fake Card", "qty": 4}]
        assert result["total_cards"] == 4
        assert result["curve"] == {"1-2": 0, "3-4": 0, "5-6": 0, "7+": 0}

    @patch("lorcana_mcp.deck.search_card")
    def test_over_4_copies_flagged(self, mock_search):
        mock_search.return_value = _card("Goofy - Musketeer", 2, "Character", True, ["Steel"])
        result = analyze_deck("5x Goofy - Musketeer")
        assert result["legality"]["max_4_copies"] is False
        assert result["legality"]["over_limit_cards"] == [("Goofy - Musketeer", 5)]

    @patch("lorcana_mcp.deck.search_card")
    def test_duplicate_lines_combined(self, mock_search):
        mock_search.return_value = _card("Goofy - Musketeer", 2, "Character", True, ["Steel"])
        result = analyze_deck("2x Goofy - Musketeer\n2x Goofy - Musketeer")
        assert result["unique_cards"] == 1
        assert result["total_cards"] == 4

    @patch("lorcana_mcp.deck.search_card")
    def test_three_ink_colors_fails_legality(self, mock_search):
        cards = {
            "a": _card("A", 1, "Character", True, ["Amber"]),
            "b": _card("B", 1, "Character", True, ["Ruby"]),
            "c": _card("C", 1, "Character", True, ["Sapphire"]),
        }
        mock_search.side_effect = lambda name, set_name="": cards[name.lower()]
        result = analyze_deck("4x A\n4x B\n4x C")
        assert result["legality"]["two_ink_colors_or_fewer"] is False
        assert result["legality"]["ink_colors_used"] == ["Amber", "Ruby", "Sapphire"]

    @patch("lorcana_mcp.deck.search_card")
    def test_60_card_minimum(self, mock_search):
        mock_search.return_value = _card("Goofy - Musketeer", 2, "Character", True, ["Steel"])
        result = analyze_deck("4x Goofy - Musketeer")
        assert result["legality"]["min_60_cards"] is False


# ── combine_deck_lines ────────────────────────────────────────────────────────────

class TestCombineDeckLines:
    def test_combines_duplicate_case_insensitive_lines(self):
        combined, name_by_key = combine_deck_lines([(2, "Goofy - Musketeer"), (2, "goofy - musketeer")])
        assert combined == {"goofy - musketeer": 4}
        assert name_by_key == {"goofy - musketeer": "Goofy - Musketeer"}  # first-seen casing wins

    def test_preserves_insertion_order(self):
        combined, _ = combine_deck_lines([(1, "B"), (1, "A"), (1, "B")])
        assert list(combined.keys()) == ["b", "a"]

    def test_empty_input(self):
        combined, name_by_key = combine_deck_lines([])
        assert combined == {} and name_by_key == {}


# ── what_am_i_missing ───────────────────────────────────────────────────────────

class TestWhatAmIMissing:
    @patch("lorcana_mcp.deck.search_card")
    def test_fully_owned_card_has_zero_missing(self, mock_search):
        mock_search.return_value = _card("Goofy - Musketeer", 2, "Character", True, ["Steel"])
        result = what_am_i_missing("4x Goofy - Musketeer", {"goofy - musketeer": 4})
        assert result["entries"] == [{"name": "Goofy - Musketeer", "needed": 4, "owned": 4, "missing": 0}]

    @patch("lorcana_mcp.deck.search_card")
    def test_owned_more_than_needed_still_zero_missing(self, mock_search):
        mock_search.return_value = _card("Goofy - Musketeer", 2, "Character", True, ["Steel"])
        result = what_am_i_missing("2x Goofy - Musketeer", {"goofy - musketeer": 6})
        assert result["entries"][0]["missing"] == 0

    @patch("lorcana_mcp.deck.search_card")
    def test_partially_owned_reports_missing_count(self, mock_search):
        mock_search.return_value = _card("Goofy - Musketeer", 2, "Character", True, ["Steel"])
        result = what_am_i_missing("4x Goofy - Musketeer", {"goofy - musketeer": 1})
        assert result["entries"][0] == {"name": "Goofy - Musketeer", "needed": 4, "owned": 1, "missing": 3}

    @patch("lorcana_mcp.deck.search_card")
    def test_not_owned_at_all(self, mock_search):
        mock_search.return_value = _card("Elsa - Spirit of Winter", 8, "Character", False, ["Amethyst"])
        result = what_am_i_missing("2x Elsa - Spirit of Winter", {})
        assert result["entries"][0] == {"name": "Elsa - Spirit of Winter", "needed": 2, "owned": 0, "missing": 2}

    @patch("lorcana_mcp.deck.search_card")
    def test_unresolved_card_flagged_separately(self, mock_search):
        mock_search.return_value = None
        result = what_am_i_missing("3x Totally Fake Card", {})
        assert result["entries"] == []
        assert result["unresolved"] == [{"name": "Totally Fake Card", "qty": 3}]

    @patch("lorcana_mcp.deck.search_card")
    def test_owned_lookup_uses_resolved_full_name_not_raw_query(self, mock_search):
        # user typed an informal name, but ownership must match the resolved fullName
        mock_search.return_value = _card("Goofy - Musketeer", 2, "Character", True, ["Steel"])
        result = what_am_i_missing("4x goofy musketeer", {"goofy - musketeer": 4})
        assert result["entries"][0]["owned"] == 4

    @patch("lorcana_mcp.deck.search_card")
    def test_empty_deck_list(self, mock_search):
        result = what_am_i_missing("", {})
        assert result == {"entries": [], "unresolved": []}
        mock_search.assert_not_called()
