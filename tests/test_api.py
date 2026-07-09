"""Tests for api.py — pure helper functions only (no network calls)."""
from __future__ import annotations

import json
from unittest.mock import call, patch

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
    singer_value,
    is_song,
    find_song_singers,
    dedupe_by_full_name,
    fetch_tcgcsv_groups,
    fetch_tcgcsv_prices,
    cheapest_price_for_card,
    fetch_lorcana_json,
    fetch_lorcana_sets,
    lj_card_format_legal,
    filter_by_format,
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

    def test_duplicate_printings_deduplicated(self):
        enchanted_reprint = _lj_card("Goofy - Musketeer", 2, "Character", "Steel",
                                      rarity="Enchanted", setCode="1", strength=2, willpower=3, lore=1)
        result = filter_cards(_CARDS + [enchanted_reprint], colors=["Steel"])
        matches = [c for c in result if c["fullName"] == "Goofy - Musketeer"]
        assert len(matches) == 1


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


# ── song synergies: singer_value / is_song / find_song_singers ─────────────────

def _character(name, cost, color="Amber", singer=None, colors=None):
    abilities = []
    if singer is not None:
        abilities.append({"type": "keyword", "keyword": "Singer", "keywordValueNumber": singer,
                           "fullText": f"Singer {singer}"})
    return {
        "fullName": name, "type": "Character", "cost": cost, "color": color, "colors": colors,
        "abilities": abilities,
    }


def _song(name, cost):
    return {"fullName": name, "type": "Action", "subtypes": ["Song"], "cost": cost, "abilities": []}


class TestSingerValue:
    def test_has_singer_keyword(self):
        card = _character("Ariel - Spectacular Singer", 3, singer=5)
        assert singer_value(card) == 5

    def test_no_singer_keyword(self):
        card = _character("Goofy - Musketeer", 2)
        assert singer_value(card) is None

    def test_non_keyword_abilities_ignored(self):
        card = {"abilities": [{"type": "activated", "keyword": "", "fullText": "Do a thing."}]}
        assert singer_value(card) is None


class TestIsSong:
    def test_song_action(self):
        assert is_song(_song("Be Our Guest", 5)) is True

    def test_non_song_action(self):
        assert is_song({"type": "Action", "subtypes": []}) is False

    def test_character_is_not_song(self):
        assert is_song(_character("Goofy - Musketeer", 2)) is False


class TestFindSongSingers:
    _CARDS = [
        _character("Cheap Singer", 2, singer=5),
        _character("Big Singer", 6, singer=7),
        _character("Plain Expensive", 6),
        _character("Too Cheap", 1),
        _character("Steel Body", 5, color="Steel"),
        _song("Some Song", 5),  # not a Character — must be excluded
    ]

    def test_only_characters_returned(self):
        result = find_song_singers(5, self._CARDS)
        names = {c["fullName"] for c in result}
        assert "Some Song" not in names

    def test_singer_keyword_qualifies_below_actual_cost(self):
        result = find_song_singers(5, self._CARDS)
        names = {c["fullName"] for c in result}
        assert "Cheap Singer" in names  # cost 2, but Singer 5

    def test_actual_cost_qualifies_without_singer(self):
        result = find_song_singers(5, self._CARDS)
        names = {c["fullName"] for c in result}
        assert "Plain Expensive" in names  # cost 6, no Singer needed

    def test_too_cheap_and_no_singer_excluded(self):
        result = find_song_singers(5, self._CARDS)
        names = {c["fullName"] for c in result}
        assert "Too Cheap" not in names

    def test_singers_sorted_before_plain_qualifiers(self):
        result = find_song_singers(5, self._CARDS)
        names = [c["fullName"] for c in result]
        singer_names = {"Cheap Singer", "Big Singer"}
        plain_names = {"Plain Expensive", "Steel Body"}
        last_singer_idx = max(names.index(n) for n in singer_names if n in names)
        first_plain_idx = min(names.index(n) for n in plain_names if n in names)
        assert last_singer_idx < first_plain_idx

    def test_singers_sorted_by_value_desc_then_cost_asc(self):
        result = find_song_singers(5, self._CARDS)
        names = [c["fullName"] for c in result]
        assert names.index("Big Singer") < names.index("Cheap Singer")

    def test_color_filter(self):
        result = find_song_singers(5, self._CARDS, colors=["Steel"])
        names = {c["fullName"] for c in result}
        assert names == {"Steel Body"}

    def test_no_matches(self):
        result = find_song_singers(99, self._CARDS)
        assert result == []

    def test_duplicate_printings_deduplicated(self):
        cards = self._CARDS + [_character("Cheap Singer", 2, singer=5)]  # alt-art reprint
        result = find_song_singers(5, cards)
        matches = [c for c in result if c["fullName"] == "Cheap Singer"]
        assert len(matches) == 1


# ── dedupe_by_full_name ──────────────────────────────────────────────────────────

class TestDedupeByFullName:
    def test_keeps_first_occurrence(self):
        a = {"fullName": "Goofy - Musketeer", "setCode": "1"}
        b = {"fullName": "Goofy - Musketeer", "setCode": "1", "rarity": "Enchanted"}
        assert dedupe_by_full_name([a, b]) == [a]

    def test_distinct_names_preserved(self):
        a = {"fullName": "Goofy - Musketeer"}
        b = {"fullName": "Elsa - Snow Queen"}
        assert dedupe_by_full_name([a, b]) == [a, b]

    def test_empty_list(self):
        assert dedupe_by_full_name([]) == []


# ── fetch_lorcana_json / fetch_lorcana_sets (single-fetch refactor) ────────────────

class TestFetchLorcanaJsonSharedFetch:
    def test_cold_cache_calls_fetch_once_and_populates_both_keys(self):
        body = json.dumps({
            "cards": [{"fullName": "Goofy - Musketeer"}],
            "sets": {"1": {"name": "The First Chapter"}},
        }).encode()
        with patch("lorcana_mcp.api._cache.get", return_value=None), \
             patch("lorcana_mcp.api._fetch", return_value=body) as mock_fetch, \
             patch("lorcana_mcp.api._cache.set") as mock_set:
            cards = fetch_lorcana_json()
        assert cards == [{"fullName": "Goofy - Musketeer"}]
        mock_fetch.assert_called_once()
        assert mock_set.call_args_list == [
            call("lorcana_json", [{"fullName": "Goofy - Musketeer"}]),
            call("lorcana_json_sets", {"1": {"name": "The First Chapter"}}),
        ]

    def test_fetch_lorcana_sets_cold_cache_also_single_fetch(self):
        body = json.dumps({
            "cards": [{"fullName": "Goofy - Musketeer"}],
            "sets": {"1": {"name": "The First Chapter"}},
        }).encode()
        with patch("lorcana_mcp.api._cache.get", return_value=None), \
             patch("lorcana_mcp.api._fetch", return_value=body) as mock_fetch, \
             patch("lorcana_mcp.api._cache.set"):
            sets_meta = fetch_lorcana_sets()
        assert sets_meta == {"1": {"name": "The First Chapter"}}
        mock_fetch.assert_called_once()

    def test_warm_cache_skips_fetch(self):
        with patch("lorcana_mcp.api._cache.get", return_value={"1": {"name": "Cached"}}), \
             patch("lorcana_mcp.api._fetch") as mock_fetch:
            sets_meta = fetch_lorcana_sets()
        assert sets_meta == {"1": {"name": "Cached"}}
        mock_fetch.assert_not_called()


# ── lj_card_format_legal / filter_by_format ─────────────────────────────────────

def _fmt_card(name, set_code="9", number=1, rarity="Common"):
    return {"fullName": name, "setCode": set_code, "number": number, "rarity": rarity}


class TestLjCardFormatLegal:
    def test_core_legal_via_duels_lookup(self):
        card = _fmt_card("Legal Card", set_code="9", number=1)
        lookup = {("9", 1): {"legality": ["core", "infinity"]}}
        assert lj_card_format_legal(card, "core", lookup) is True

    def test_core_illegal_when_format_missing_from_legality(self):
        card = _fmt_card("Infinity Only", set_code="1", number=1)
        lookup = {("1", 1): {"legality": ["infinity"]}}
        assert lj_card_format_legal(card, "core", lookup) is False

    def test_illegal_when_not_in_duels_lookup(self):
        card = _fmt_card("Unknown Card", set_code="99", number=1)
        assert lj_card_format_legal(card, "core", {}) is False

    def test_poorcana_ignores_duels_lookup_uses_rarity(self):
        common = _fmt_card("Common Card", rarity="Common")
        legendary = _fmt_card("Legendary Card", rarity="Legendary")
        assert lj_card_format_legal(common, "poorcana", {}) is True
        assert lj_card_format_legal(legendary, "poorcana", {}) is False

    def test_missing_set_code_or_number_is_illegal(self):
        assert lj_card_format_legal({"fullName": "No Set"}, "core", {}) is False


class TestFilterByFormat:
    def test_filters_to_legal_cards_only(self):
        legal = _fmt_card("Legal", set_code="9", number=1)
        illegal = _fmt_card("Illegal", set_code="1", number=2)
        lookup = {("9", 1): {"legality": ["core"]}, ("1", 2): {"legality": ["infinity"]}}
        result = filter_by_format([legal, illegal], "core", lookup)
        assert result == [legal]

    def test_poorcana_needs_no_duels_lookup(self):
        common = _fmt_card("Common", rarity="Common")
        result = filter_by_format([common], "poorcana")
        assert result == [common]


# ── tcgcsv pricing ────────────────────────────────────────────────────────────────


class TestFetchTcgcsvGroups:
    def test_cache_hit_skips_fetch(self):
        with patch("lorcana_mcp.api._cache.get", return_value=[{"groupId": 1, "name": "Cached Set"}]), \
             patch("lorcana_mcp.api._fetch") as mock_fetch:
            groups = fetch_tcgcsv_groups()
        assert groups == [{"groupId": 1, "name": "Cached Set"}]
        mock_fetch.assert_not_called()

    def test_cache_miss_fetches_and_caches(self):
        body = json.dumps({"results": [{"groupId": 1, "name": "Set One"}]}).encode()
        with patch("lorcana_mcp.api._cache.get", return_value=None), \
             patch("lorcana_mcp.api._fetch", return_value=body), \
             patch("lorcana_mcp.api._cache.set") as mock_set:
            groups = fetch_tcgcsv_groups()
        assert groups == [{"groupId": 1, "name": "Set One"}]
        mock_set.assert_called_once_with("tcgcsv_groups", groups)


class TestFetchTcgcsvPrices:
    def test_cache_hit_returns_int_keyed_dict(self):
        # simulates a JSON round-trip, where dict keys always come back as strings
        with patch("lorcana_mcp.api._cache.get", return_value={"123": 4.5, "456": 1.0}):
            prices = fetch_tcgcsv_prices()
        assert prices == {123: 4.5, 456: 1.0}

    def test_cache_miss_merges_all_groups(self):
        groups = [{"groupId": 1}, {"groupId": 2}]
        group_bodies = {
            1: json.dumps({"results": [{"productId": 100, "marketPrice": 5.0}]}).encode(),
            2: json.dumps({"results": [{"productId": 200, "marketPrice": 3.0}]}).encode(),
        }

        def fake_fetch(url):
            group_id = 1 if "/1/prices" in url else 2
            return group_bodies[group_id]

        with patch("lorcana_mcp.api._cache.get", return_value=None), \
             patch("lorcana_mcp.api.fetch_tcgcsv_groups", return_value=groups), \
             patch("lorcana_mcp.api._fetch", side_effect=fake_fetch), \
             patch("lorcana_mcp.api._cache.set") as mock_set:
            prices = fetch_tcgcsv_prices()
        assert prices == {100: 5.0, 200: 3.0}
        mock_set.assert_called_once_with("tcgcsv_prices", prices)

    def test_duplicate_product_id_keeps_lowest_price(self):
        groups = [{"groupId": 1}, {"groupId": 2}]
        group_bodies = {
            1: json.dumps({"results": [{"productId": 100, "marketPrice": 5.0}]}).encode(),
            2: json.dumps({"results": [{"productId": 100, "marketPrice": 2.0}]}).encode(),
        }

        def fake_fetch(url):
            group_id = 1 if "/1/prices" in url else 2
            return group_bodies[group_id]

        with patch("lorcana_mcp.api._cache.get", return_value=None), \
             patch("lorcana_mcp.api.fetch_tcgcsv_groups", return_value=groups), \
             patch("lorcana_mcp.api._fetch", side_effect=fake_fetch), \
             patch("lorcana_mcp.api._cache.set"):
            prices = fetch_tcgcsv_prices()
        assert prices == {100: 2.0}

    def test_group_fetch_failure_is_skipped_not_fatal(self):
        groups = [{"groupId": 1}, {"groupId": 2}]
        ok_body = json.dumps({"results": [{"productId": 200, "marketPrice": 3.0}]}).encode()

        def fake_fetch(url):
            if "/1/prices" in url:
                raise RuntimeError("network down")
            return ok_body

        with patch("lorcana_mcp.api._cache.get", return_value=None), \
             patch("lorcana_mcp.api.fetch_tcgcsv_groups", return_value=groups), \
             patch("lorcana_mcp.api._fetch", side_effect=fake_fetch), \
             patch("lorcana_mcp.api._cache.set"):
            prices = fetch_tcgcsv_prices()
        assert prices == {200: 3.0}

    def test_rows_missing_price_or_id_skipped(self):
        groups = [{"groupId": 1}]
        body = json.dumps({"results": [
            {"productId": 100, "marketPrice": None},
            {"productId": None, "marketPrice": 5.0},
            {"productId": 200, "marketPrice": 3.0},
        ]}).encode()

        with patch("lorcana_mcp.api._cache.get", return_value=None), \
             patch("lorcana_mcp.api.fetch_tcgcsv_groups", return_value=groups), \
             patch("lorcana_mcp.api._fetch", return_value=body), \
             patch("lorcana_mcp.api._cache.set"):
            prices = fetch_tcgcsv_prices()
        assert prices == {200: 3.0}


class TestCheapestPriceForCard:
    def test_returns_lowest_price_across_printings(self):
        lj_cards = [
            {"fullName": "Goofy - Musketeer", "externalLinks": {"tcgPlayerId": 1}},
            {"fullName": "Goofy - Musketeer", "externalLinks": {"tcgPlayerId": 2}},
        ]
        price_by_pid = {1: 5.0, 2: 1.5}
        assert cheapest_price_for_card("Goofy - Musketeer", lj_cards, price_by_pid) == 1.5

    def test_no_matching_card_returns_none(self):
        lj_cards = [{"fullName": "Elsa - Snow Queen", "externalLinks": {"tcgPlayerId": 1}}]
        assert cheapest_price_for_card("Goofy - Musketeer", lj_cards, {1: 5.0}) is None

    def test_no_price_data_returns_none(self):
        lj_cards = [{"fullName": "Goofy - Musketeer", "externalLinks": {"tcgPlayerId": 1}}]
        assert cheapest_price_for_card("Goofy - Musketeer", lj_cards, {}) is None

    def test_missing_external_links_ignored(self):
        lj_cards = [{"fullName": "Goofy - Musketeer"}]
        assert cheapest_price_for_card("Goofy - Musketeer", lj_cards, {1: 5.0}) is None
