"""Tests for api.py — pure helper functions only (no network calls)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from lorcana_mcp.api import (
    extract_keywords_from_text,
    extract_keywords_from_lj_abilities,
    abilities_from_lj,
    pick_lj_card,
    build_lj_lookup,
    build_duels_lookup,
    enrich_from_lj,
    enrich_from_api,
    filter_cards,
    _tokenize,
    _token_match,
    _card_score,
    score_candidates,
    resolve_card,
    search_card,
)


# ── extract_keywords_from_text ─────────────────────────────────────────────────

class TestExtractKeywordsFromText:
    def test_evasive(self):
        assert extract_keywords_from_text("Evasive (Only challenged by Evasive.)") == "Evasive"

    def test_bodyguard(self):
        assert extract_keywords_from_text("Bodyguard (An opponent must challenge this first.)") == "Bodyguard"

    def test_rush(self):
        assert extract_keywords_from_text("Rush (Can challenge the turn played.)") == "Rush"

    def test_ward(self):
        assert extract_keywords_from_text("Ward (Can't be chosen by opponent's actions.)") == "Ward"

    def test_alert(self):
        assert extract_keywords_from_text("Alert (When challenged, you may draw a card.)") == "Alert"

    def test_shift_with_number(self):
        assert extract_keywords_from_text("Shift 3 (You may pay 3 ⬡ to play this on top of...)") == "Shift 3"

    def test_singer_with_number(self):
        assert extract_keywords_from_text("Singer 5 (This character can sing songs for free...)") == "Singer 5"

    def test_challenger_with_modifier(self):
        assert extract_keywords_from_text("Challenger +2 (Gets +2 ¤ while challenging.)") == "Challenger +2"

    def test_resist_with_modifier(self):
        assert extract_keywords_from_text("Resist +1 (Damage dealt to this is reduced by 1.)") == "Resist +1"

    def test_multiple_keywords(self):
        result = extract_keywords_from_text("Evasive (Only Evasive can challenge.)\nBodyguard (Must challenge this first.)")
        assert "Evasive" in result
        assert "Bodyguard" in result

    def test_empty_text(self):
        assert extract_keywords_from_text("") == ""

    def test_no_keywords(self):
        assert extract_keywords_from_text("When you play this card, draw a card.") == ""


# ── extract_keywords_from_lj_abilities ────────────────────────────────────────

class TestExtractKeywordsFromLjAbilities:
    def test_keyword_type_no_number(self):
        abilities = [{"type": "keyword", "keyword": "Evasive", "fullText": "Evasive (Only Evasive can challenge.)"}]
        assert extract_keywords_from_lj_abilities(abilities) == "Evasive"

    def test_keyword_type_with_number(self):
        abilities = [{"type": "keyword", "keyword": "Shift", "fullText": "Shift 3 (Pay 3 to play on top of...)"}]
        assert extract_keywords_from_lj_abilities(abilities) == "Shift 3"

    def test_keyword_with_plus_modifier(self):
        abilities = [{"type": "keyword", "keyword": "Resist", "fullText": "Resist +1 (Damage reduced by 1.)"}]
        assert extract_keywords_from_lj_abilities(abilities) == "Resist +1"

    def test_non_keyword_type_ignored(self):
        abilities = [{"type": "activated", "keyword": "", "fullText": "⟳, 2 ⬡ — Draw a card."}]
        assert extract_keywords_from_lj_abilities(abilities) == ""

    def test_multiple_keywords(self):
        abilities = [
            {"type": "keyword", "keyword": "Evasive", "fullText": "Evasive"},
            {"type": "keyword", "keyword": "Shift", "fullText": "Shift 4"},
        ]
        result = extract_keywords_from_lj_abilities(abilities)
        assert "Evasive" in result
        assert "Shift 4" in result

    def test_empty_list(self):
        assert extract_keywords_from_lj_abilities([]) == ""


# ── pick_lj_card ───────────────────────────────────────────────────────────────

class TestPickLjCard:
    def test_single_candidate_returned_regardless_of_name(self):
        card = {"fullName": "Solo Card", "name": "Solo"}
        assert pick_lj_card([card], "Anything") == card

    def test_empty_list_returns_none(self):
        assert pick_lj_card([], "Name") is None

    def test_exact_fullname_match_wins(self):
        a = {"fullName": "Mirage - Super Recruiter", "name": "Mirage"}
        b = {"fullName": "Mirage - Alternate Version", "name": "Mirage"}
        assert pick_lj_card([b, a], "Mirage - Super Recruiter") == a

    def test_name_prefix_match_as_fallback(self):
        a = {"fullName": "Woody - Jungle Guide", "name": "Woody"}
        b = {"fullName": "Woody - Sheriff of Toy Story", "name": "Woody"}
        # Neither is an exact fullName match for "Woody - Some Other"
        # but both start with "Woody" — first matching prefix wins
        result = pick_lj_card([a, b], "Woody - Some Other")
        assert result in (a, b)

    def test_no_match_falls_back_to_first(self):
        a = {"fullName": "Card A", "name": "A"}
        b = {"fullName": "Card B", "name": "B"}
        assert pick_lj_card([a, b], "Completely Different") == a


# ── build_lj_lookup ────────────────────────────────────────────────────────────

class TestBuildLjLookup:
    def test_single_card(self):
        cards = [{"setCode": 1, "number": 61, "fullName": "Zeus"}]
        lookup = build_lj_lookup(cards)
        assert ("1", 61) in lookup
        assert lookup[("1", 61)] == [cards[0]]

    def test_duplicate_numbers_stored_as_list(self):
        cards = [
            {"setCode": 12, "number": 47, "fullName": "Will o' the Wisp - Forest Spirit"},
            {"setCode": 12, "number": 47, "fullName": "Will o' the Wisp - Alternate Art"},
        ]
        lookup = build_lj_lookup(cards)
        assert len(lookup[("12", 47)]) == 2

    def test_invalid_entries_skipped(self):
        cards = [{"setCode": "x", "number": "not_a_number"}]
        assert build_lj_lookup(cards) == {}


# ── build_duels_lookup ─────────────────────────────────────────────────────────

class TestBuildDuelsLookup:
    def test_regular_id_indexed(self):
        cards = [{"id": "1-61", "fullName": "Zeus - God of Lightning", "legality": ["infinity"]}]
        lookup = build_duels_lookup(cards)
        assert ("1", 61) in lookup

    def test_promo_variant_id_skipped(self):
        cards = [{"id": "13-PD1-4", "fullName": "Some Promo"}]
        assert build_duels_lookup(cards) == {}

    def test_mixed_ids(self):
        cards = [
            {"id": "1-61", "fullName": "Zeus"},
            {"id": "13-PD1-4", "fullName": "Promo"},
            {"id": "12-47", "fullName": "Will o' the Wisp"},
        ]
        lookup = build_duels_lookup(cards)
        assert ("1", 61) in lookup
        assert ("12", 47) in lookup
        assert len(lookup) == 2


# ── enrich_from_lj ────────────────────────────────────────────────────────────

def test_enrich_from_lj_character():
    card = {
        "color": "Amethyst",
        "cost": 4,
        "type": "Character",
        "subtypes": ["Storyborn", "Ally"],
        "strength": 3,
        "willpower": 3,
        "lore": 1,
        "inkwell": True,
        "abilities": [
            {"type": "keyword", "keyword": "Evasive", "fullText": "Evasive"},
            {"type": "activated", "fullText": "BUSINESS ARRANGEMENT — Do a thing."},
        ],
    }
    result = enrich_from_lj(card)
    ink, cost, ctype, subtypes, strength, willpower, lore, inkable, keywords, abilities = result
    assert ink == "Amethyst"
    assert cost == "4"
    assert ctype == "Character"
    assert subtypes == "Storyborn, Ally"
    assert strength == "3"
    assert willpower == "3"
    assert lore == "1"
    assert inkable == "Yes"
    assert "Evasive" in keywords
    assert "BUSINESS ARRANGEMENT" in abilities


def test_enrich_from_lj_action_has_blank_stats():
    card = {
        "color": "Ruby",
        "cost": 3,
        "type": "Action",
        "subtypes": [],
        "strength": "",
        "willpower": "",
        "lore": "",
        "inkwell": True,
        "abilities": [],
    }
    _, _, _, _, strength, willpower, lore, _, _, _ = enrich_from_lj(card)
    assert strength == ""
    assert willpower == ""
    assert lore == ""


# ── enrich_from_api ────────────────────────────────────────────────────────────

def test_enrich_from_api_basic():
    card = {
        "Color": "Steel",
        "Cost": 5,
        "Type": "Character",
        "Classifications": "Floodborn/Hero",
        "Strength": 4,
        "Willpower": 6,
        "Lore": 2,
        "Inkable": True,
        "Body_Text": "Ward (Opponents can't choose this character with their actions.)",
    }
    result = enrich_from_api(card)
    ink, cost, ctype, subtypes, strength, willpower, lore, inkable, keywords, abilities = result
    assert ink == "Steel"
    assert cost == "5"
    assert inkable == "Yes"
    assert "Ward" in keywords
    assert "Ward" in abilities


def test_enrich_from_api_not_inkable():
    card = {
        "Color": "Amber", "Cost": 2, "Type": "Character",
        "Classifications": "", "Strength": 1, "Willpower": 3, "Lore": 1,
        "Inkable": False, "Body_Text": "",
    }
    _, _, _, _, _, _, _, inkable, _, _ = enrich_from_api(card)
    assert inkable == "No"


# ── filter_cards ───────────────────────────────────────────────────────────────

def _lj_card(name, cost, ctype, color, rarity="Common", setCode="12",
             strength=None, willpower=None, lore=None, subtypes=None,
             colors=None, abilities=None, fullText=""):
    return {
        "fullName": name, "cost": cost, "type": ctype, "color": color, "colors": colors,
        "rarity": rarity, "setCode": setCode, "strength": strength, "willpower": willpower,
        "lore": lore, "subtypes": subtypes or [], "abilities": abilities or [], "fullText": fullText,
    }


_CARDS = [
    _lj_card("Goofy - Musketeer", 2, "Character", "Steel", rarity="Common",
             strength=2, willpower=3, lore=1),
    _lj_card("Elsa - Spirit of Winter", 8, "Character", "Amethyst", rarity="Legendary",
             strength=6, willpower=8, lore=3,
             abilities=[{"type": "keyword", "keyword": "Evasive", "fullText": "Evasive"}]),
    _lj_card("Be Our Guest", 5, "Action", "Amber", rarity="Uncommon", subtypes=["Song"]),
    _lj_card("Rhino - Motivational Speaker", 3, "Character", "Amber-Steel",
             colors=["Amber", "Steel"], rarity="Rare", strength=2, willpower=2, lore=1,
             subtypes=["Storyborn", "Ally", "Toy"]),
    _lj_card("Cleansing Rainwater", 1, "Item", "Sapphire", rarity="Common",
             fullText="Banish this item to remove up to 3 damage from chosen character."),
]


class TestFilterCards:
    def test_no_filters_returns_all_sorted_by_cost(self):
        result = filter_cards(_CARDS)
        assert [c["fullName"] for c in result] == [
            "Cleansing Rainwater", "Goofy - Musketeer", "Rhino - Motivational Speaker",
            "Be Our Guest", "Elsa - Spirit of Winter",
        ]

    def test_filter_by_color_single(self):
        result = filter_cards(_CARDS, colors=["Steel"])
        names = {c["fullName"] for c in result}
        assert names == {"Goofy - Musketeer", "Rhino - Motivational Speaker"}

    def test_filter_by_color_matches_dual_ink_on_either_half(self):
        result = filter_cards(_CARDS, colors=["Amber"])
        names = {c["fullName"] for c in result}
        assert "Rhino - Motivational Speaker" in names
        assert "Be Our Guest" in names

    def test_filter_by_card_type(self):
        result = filter_cards(_CARDS, card_type="Item")
        assert [c["fullName"] for c in result] == ["Cleansing Rainwater"]

    def test_filter_by_card_type_song(self):
        result = filter_cards(_CARDS, card_type="Song")
        assert [c["fullName"] for c in result] == ["Be Our Guest"]

    def test_filter_by_rarity(self):
        result = filter_cards(_CARDS, rarity="legendary")
        assert [c["fullName"] for c in result] == ["Elsa - Spirit of Winter"]

    def test_filter_by_cost_range(self):
        result = filter_cards(_CARDS, cost_min=2, cost_max=3)
        names = {c["fullName"] for c in result}
        assert names == {"Goofy - Musketeer", "Rhino - Motivational Speaker"}

    def test_filter_by_keyword(self):
        result = filter_cards(_CARDS, keyword="Evasive")
        assert [c["fullName"] for c in result] == ["Elsa - Spirit of Winter"]

    def test_filter_by_ability_text_substring(self):
        result = filter_cards(_CARDS, ability_text="remove up to 3 damage")
        assert [c["fullName"] for c in result] == ["Cleansing Rainwater"]

    def test_filter_by_subtype(self):
        result = filter_cards(_CARDS, subtype="toy")
        assert [c["fullName"] for c in result] == ["Rhino - Motivational Speaker"]

    def test_combined_filters(self):
        result = filter_cards(_CARDS, colors=["Steel"], cost_max=2)
        assert [c["fullName"] for c in result] == ["Goofy - Musketeer"]

    def test_no_matches(self):
        assert filter_cards(_CARDS, rarity="Epic") == []


# ── fuzzy card resolution: _tokenize / _token_match / _card_score ──────────────

class TestTokenize:
    def test_splits_on_punctuation(self):
        assert _tokenize("Goofy - Musketeer") == ["goofy", "musketeer"]

    def test_lowercases(self):
        assert _tokenize("ELSA") == ["elsa"]

    def test_apostrophe_splits_word(self):
        assert _tokenize("Will o' the Wisp") == ["will", "o", "the", "wisp"]

    def test_empty_string(self):
        assert _tokenize("") == []


class TestTokenMatch:
    def test_exact_match(self):
        assert _token_match("elsa", "elsa") is True

    def test_short_tokens_require_exact(self):
        # "te" must not match as a substring of "musketeer" — this was a real
        # false-positive bug (short tokens are common substrings of long words).
        assert _token_match("te", "musketeer") is False

    def test_substring_requires_both_3plus_chars(self):
        assert _token_match("of", "wolf") is False

    def test_substring_match_3plus_chars(self):
        assert _token_match("muske", "musketeer") is True

    def test_fuzzy_typo_5plus_chars(self):
        assert _token_match("musketer", "musketeer") is True

    def test_fuzzy_does_not_collide_short_lookalikes(self):
        # "elsa" (4 chars) vs "elisa" (5 chars) scores 0.89 by ratio alone —
        # below the 5-char minimum this must NOT match, or "Elsa" queries
        # would surface unrelated "Elisa Maza" cards.
        assert _token_match("elsa", "elisa") is False

    def test_no_match(self):
        assert _token_match("goofy", "pete") is False


class TestCardScore:
    def _card(self, name, version):
        return {"name": name, "version": version}

    def test_exact_tokens_match_name_and_version(self):
        card = self._card("Goofy", "Musketeer")
        assert _card_score(["goofy", "musketeer"], card) == pytest.approx(0.7875)

    def test_bare_name_single_token_full_recall(self):
        card = self._card("Elsa", "Spirit of Winter")
        assert _card_score(["elsa"], card) == 1.0

    def test_no_overlap_scores_zero(self):
        card = self._card("Goofy", "Musketeer")
        assert _card_score(["totally", "unrelated"], card) == 0.0

    def test_partial_match_scores_between_zero_and_one(self):
        card = self._card("Pete", "Bad Guy")
        score = _card_score(["big", "pete"], card)
        assert 0.0 < score < 1.0

    def test_extra_card_tokens_lower_precision(self):
        tighter = self._card("Goofy", "Musketeer")
        looser = self._card("Goofy", "Musketeer Swordsman")
        assert _card_score(["goofy", "musketeer"], tighter) > _card_score(["goofy", "musketeer"], looser)


# ── fuzzy card resolution: score_candidates / resolve_card / search_card ───────

def _lj(name, version, setCode="1", **extra):
    full_name = f"{name} - {version}" if version else name
    card = {"name": name, "version": version, "fullName": full_name, "setCode": setCode}
    card.update(extra)
    return card


_FUZZY_CARDS = [
    _lj("Goofy", "Musketeer", setCode="1"),
    _lj("Goofy", "Musketeer Swordsman", setCode="4"),
    _lj("Elsa", "Snow Queen", setCode="9"),
    _lj("Elsa", "Spirit of Winter", setCode="5"),
    _lj("Elsa", "Ice Maker", setCode="12"),
    _lj("Pete", "Bad Guy", setCode="1"),
    _lj("Pete", "Freebooter", setCode="6"),
    _lj("Jafar", "Newly Crowned", setCode="7"),
    _lj("Unrelated Card", "Nothing Alike", setCode="1"),
]


class TestScoreCandidates:
    def test_dashless_query_resolves_to_exact_full_name_match(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            result = score_candidates("goofy musketeer")
        assert result[0][1]["fullName"] == "Goofy - Musketeer"
        assert result[0][0] == 1.0

    def test_missing_dash_and_word_order_normalized_to_exact(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            result = score_candidates("jafar newly crowned")
        assert result[0][1]["fullName"] == "Jafar - Newly Crowned"
        assert result[0][0] == 1.0

    def test_bare_name_ties_broken_by_set_recency(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            result = score_candidates("elsa")
        elsa_results = [c for score, c in result if c["name"] == "Elsa"]
        assert len(elsa_results) == 3
        assert result[0][1]["fullName"] == "Elsa - Ice Maker"  # setCode 12, most recent
        assert result[0][0] == result[1][0] == 1.0  # tied scores

    def test_deduplicated_by_full_name(self):
        dupes = _FUZZY_CARDS + [_lj("Goofy", "Musketeer", setCode="1")]
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=dupes):
            result = score_candidates("goofy musketeer")
        matches = [c for score, c in result if c["fullName"] == "Goofy - Musketeer"]
        assert len(matches) == 1

    def test_set_name_filter_restricts_candidates(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            result = score_candidates("elsa", set_name="The First Chapter")
        assert result == []  # no Elsa card is in setCode "1"

    def test_no_query_tokens_returns_empty(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            assert score_candidates("") == []

    def test_nonsense_query_scores_low_or_nothing(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            result = score_candidates("xyzabc123")
        assert result == []


class TestResolveCard:
    def test_unambiguous_query_resolves(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            result = resolve_card("goofy musketeer")
        assert result["match_type"] == "resolved"
        assert len(result["candidates"]) == 1
        assert result["candidates"][0][1]["fullName"] == "Goofy - Musketeer"

    def test_bare_name_with_multiple_versions_is_ambiguous(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            result = resolve_card("elsa")
        assert result["match_type"] == "ambiguous"
        assert len(result["candidates"]) == 3

    def test_vague_qualifier_is_ambiguous_not_resolved(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            result = resolve_card("big pete")
        assert result["match_type"] == "ambiguous"
        names = {c["fullName"] for _, c in result["candidates"]}
        assert "Pete - Bad Guy" in names or "Pete - Freebooter" in names

    def test_nonsense_query_not_found(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            result = resolve_card("xyzabc123")
        assert result["match_type"] == "not_found"
        assert result["candidates"] == []


class TestSearchCardUsesScoring:
    def test_returns_top_scoring_card(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            card = search_card("goofy musketeer")
        assert card["fullName"] == "Goofy - Musketeer"

    def test_no_match_returns_none(self):
        with patch("lorcana_mcp.api.fetch_lorcana_json", return_value=_FUZZY_CARDS):
            assert search_card("xyzabc123") is None
