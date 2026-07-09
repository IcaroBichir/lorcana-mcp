"""Tests for deckbuilder.py — deck-list synthesis (pure logic, no network)."""
from __future__ import annotations

from lorcana_mcp.deckbuilder import (
    rotation_safe_set_codes,
    build_candidate_pool,
    score_card,
    character_score,
    item_location_score,
    curve_targets,
    allocate_deck,
)


def _card(name, cost, ctype, colors, lore=0, strength=0, willpower=0, subtypes=None,
          keywords=None, full_text="", set_code="12", number=1, rarity="Common", inkwell=True):
    abilities = [{"type": "keyword", "keyword": kw} for kw in (keywords or [])]
    return {
        "fullName": name,
        "cost": cost,
        "type": ctype,
        "colors": colors if len(colors) > 1 else None,
        "color": "-".join(colors),
        "lore": lore,
        "strength": strength,
        "willpower": willpower,
        "subtypes": subtypes or [],
        "abilities": abilities,
        "fullText": full_text,
        "setCode": set_code,
        "number": number,
        "rarity": rarity,
        "inkwell": inkwell,
    }


def _duels_entry(legality=("core", "infinity")):
    return {"legality": list(legality)}


# ── rotation_safe_set_codes ─────────────────────────────────────────────────────

class TestRotationSafeSetCodes:
    def test_picks_highest_currently_legal_group(self):
        sets_meta = {
            "9": {"allowedInFormats": {"Core": {"allowed": True, "rotationGroup": 3}}},
            "5": {"allowedInFormats": {"Core": {"allowed": True, "rotationGroup": 2}}},
            "1": {"allowedInFormats": {"Core": {"allowed": False, "rotationGroup": 1}}},
        }
        assert rotation_safe_set_codes(sets_meta) == {"9"}

    def test_group_shifts_dynamically_when_a_new_group_activates(self):
        sets_meta = {
            "9": {"allowedInFormats": {"Core": {"allowed": True, "rotationGroup": 3}}},
            "13": {"allowedInFormats": {"Core": {"allowed": True, "rotationGroup": 4}}},
        }
        assert rotation_safe_set_codes(sets_meta) == {"13"}

    def test_multiple_sets_in_the_same_safe_group(self):
        sets_meta = {
            "9": {"allowedInFormats": {"Core": {"allowed": True, "rotationGroup": 3}}},
            "10": {"allowedInFormats": {"Core": {"allowed": True, "rotationGroup": 3}}},
            "5": {"allowedInFormats": {"Core": {"allowed": True, "rotationGroup": 2}}},
        }
        assert rotation_safe_set_codes(sets_meta) == {"9", "10"}

    def test_empty_or_missing_data(self):
        assert rotation_safe_set_codes({}) == set()
        assert rotation_safe_set_codes({"1": {}}) == set()
        assert rotation_safe_set_codes({"1": {"allowedInFormats": {"Core": {"allowed": True}}}}) == set()


# ── build_candidate_pool ─────────────────────────────────────────────────────────

class TestBuildCandidatePool:
    def test_dual_ink_excluded_when_second_color_outside_pair(self):
        dual = _card("Ruby Emerald Dual", 3, "Character", ["Ruby", "Emerald"], set_code="7", number=1)
        mono = _card("Ruby Mono", 2, "Character", ["Ruby"], set_code="7", number=2)
        lookup = {("7", 1): _duels_entry(), ("7", 2): _duels_entry()}
        pool = build_candidate_pool([dual, mono], ["Amber", "Ruby"], "core", duels_lookup=lookup)
        names = {c["fullName"] for c in pool}
        assert "Ruby Emerald Dual" not in names
        assert "Ruby Mono" in names

    def test_dual_ink_included_when_both_colors_in_pair(self):
        dual = _card("Ruby Emerald Dual", 3, "Character", ["Ruby", "Emerald"], set_code="7", number=1)
        lookup = {("7", 1): _duels_entry()}
        pool = build_candidate_pool([dual], ["Ruby", "Emerald"], "core", duels_lookup=lookup)
        assert dual in pool

    def test_format_illegal_card_excluded(self):
        card = _card("Not Core Legal", 2, "Character", ["Amber"], set_code="1", number=1)
        lookup = {("1", 1): _duels_entry(legality=("infinity",))}
        pool = build_candidate_pool([card], ["Amber"], "core", duels_lookup=lookup)
        assert pool == []

    def test_owned_counts_filters_zero_copies(self):
        owned = _card("Owned Card", 2, "Character", ["Amber"], set_code="7", number=1)
        unowned = _card("Unowned Card", 2, "Character", ["Amber"], set_code="7", number=2)
        lookup = {("7", 1): _duels_entry(), ("7", 2): _duels_entry()}
        pool = build_candidate_pool(
            [owned, unowned], ["Amber"], "core", duels_lookup=lookup,
            owned_counts={"owned card": 2},
        )
        assert {c["fullName"] for c in pool} == {"Owned Card"}

    def test_rotation_safe_codes_restrict_pool(self):
        safe = _card("Safe Set Card", 2, "Character", ["Amber"], set_code="9", number=1)
        unsafe = _card("Unsafe Set Card", 2, "Character", ["Amber"], set_code="5", number=1)
        lookup = {("9", 1): _duels_entry(), ("5", 1): _duels_entry()}
        pool = build_candidate_pool(
            [safe, unsafe], ["Amber"], "core", duels_lookup=lookup,
            rotation_safe_codes={"9"},
        )
        assert {c["fullName"] for c in pool} == {"Safe Set Card"}

    def test_poorcana_uses_rarity_not_duels_lookup(self):
        common = _card("Common Card", 2, "Character", ["Amber"], rarity="Common")
        rare = _card("Rare Card", 2, "Character", ["Amber"], rarity="Rare")
        pool = build_candidate_pool([common, rare], ["Amber"], "poorcana")
        assert {c["fullName"] for c in pool} == {"Common Card"}

    def test_dedupes_alt_art_duplicates(self):
        base = _card("Base Card", 2, "Character", ["Amber"], set_code="9", number=1)
        enchanted = dict(base)  # same fullName, different printing
        lookup = {("9", 1): _duels_entry()}
        pool = build_candidate_pool([base, enchanted], ["Amber"], "core", duels_lookup=lookup)
        assert len(pool) == 1


# ── score_card ───────────────────────────────────────────────────────────────────

class TestScoreCard:
    def test_character_dispatches_to_character_score(self):
        card = _card("X", 3, "Character", ["Amber"], lore=2, strength=2, willpower=3)
        assert score_card(card) == character_score(card)

    def test_ward_and_evasive_outscore_vanilla_same_cost(self):
        vanilla = _card("Vanilla", 3, "Character", ["Amber"], lore=1, strength=2, willpower=2)
        warded = _card("Warded", 3, "Character", ["Amber"], lore=1, strength=2, willpower=2,
                        keywords=["Ward"])
        evasive = _card("Evasive", 3, "Character", ["Amber"], lore=1, strength=2, willpower=2,
                         keywords=["Evasive"])
        assert score_card(warded) > score_card(vanilla)
        assert score_card(evasive) > score_card(vanilla)

    def test_reckless_scores_lower_than_vanilla(self):
        vanilla = _card("Vanilla", 3, "Character", ["Amber"], lore=1, strength=2, willpower=2)
        reckless = _card("Reckless", 3, "Character", ["Amber"], lore=1, strength=2, willpower=2,
                          keywords=["Reckless"])
        assert score_card(reckless) < score_card(vanilla)

    def test_action_dispatches_and_removal_beats_vanilla(self):
        vanilla_action = _card("Do Nothing", 2, "Action", ["Amber"], full_text="Nothing special.")
        removal = _card("Banish It", 2, "Action", ["Amber"], full_text="Banish chosen character.")
        assert score_card(removal) > score_card(vanilla_action)

    def test_item_dispatches_to_item_location_score(self):
        item = _card("An Item", 1, "Item", ["Amber"])
        assert score_card(item) == item_location_score(item)

    def test_location_lore_increases_score(self):
        no_lore = _card("Quiet Place", 2, "Location", ["Amber"], lore=0)
        lore_place = _card("Lore Place", 2, "Location", ["Amber"], lore=2)
        assert score_card(lore_place) > score_card(no_lore)

    def test_unknown_type_scores_zero(self):
        weird = _card("Weird", 1, "Character", ["Amber"])
        weird["type"] = "Mystery"
        assert score_card(weird) == 0.0


# ── curve_targets ────────────────────────────────────────────────────────────────

class TestCurveTargets:
    def test_sums_to_60_with_expected_shape(self):
        targets = curve_targets(60)
        assert targets == {"1-2": 16, "3-4": 22, "5-6": 16, "7+": 6}
        assert sum(targets.values()) == 60

    def test_sums_to_arbitrary_totals(self):
        for total in (50, 40, 30, 1, 7):
            assert sum(curve_targets(total).values()) == total

    def test_peaks_at_3_4(self):
        targets = curve_targets(60)
        assert targets["3-4"] == max(targets.values())


# ── allocate_deck ────────────────────────────────────────────────────────────────

def _pool(n, cost, ctype="Character", colors=("Amber",)):
    return [
        _card(f"{ctype} {cost} #{i}", cost, ctype, list(colors), lore=1, strength=1, willpower=1,
              number=i)
        for i in range(n)
    ]


class TestAllocateDeck:
    def test_abundant_pool_fills_to_60(self):
        pool = []
        for cost in (1, 2, 3, 4, 5, 6, 7):
            pool += _pool(10, cost)
        picks = allocate_deck(pool)
        total = sum(qty for _, qty in picks)
        assert total == 60
        for _, qty in picks:
            assert 1 <= qty <= 4

    def test_thin_pool_reports_honest_shortfall_not_padded(self):
        pool = _pool(3, 3)  # only 3 unique cards -> ceiling is 3*4=12, well under 60
        picks = allocate_deck(pool)
        total = sum(qty for _, qty in picks)
        assert total == 12
        assert len(picks) == 3
        for _, qty in picks:
            assert qty == 4

    def test_max_copies_fn_caps_collection_mode(self):
        pool = _pool(5, 3)
        owned = {c["fullName"].lower(): 1 for c in pool}  # only own 1 copy of each

        def cap(card):
            return owned.get(card["fullName"].lower(), 0)

        picks = allocate_deck(pool, max_copies_fn=cap)
        for _, qty in picks:
            assert qty <= 1
        assert sum(qty for _, qty in picks) == 5  # honest shortfall vs 60

    def test_type_cap_is_soft_and_backfill_still_reaches_60(self):
        # All 30 candidates are Character; the soft type-composition cap
        # (24) shapes the primary pass, but a single-type pool must still
        # be able to reach a full 60-card deck via the backfill pass —
        # type caps sum to less than 60 by design (CLAUDE.md's composition
        # ranges cap out at 24+16+8+4=52), so they can never be a hard cap.
        pool = _pool(30, 3, ctype="Character")
        picks = allocate_deck(pool)
        assert sum(qty for _, qty in picks) == 60
        char_total = sum(qty for card, qty in picks if card["type"] == "Character")
        assert char_total == 60

    def test_type_diversity_when_pool_spans_costs_and_types(self):
        # With plenty of every type spread across the curve, the deck should
        # draw from more than just Characters even though the type caps
        # (24+16+8+4=52) can't alone reach 60 on their own — the backfill
        # pass tops up the remainder by score regardless of type, so this
        # only checks real diversity, not an exact per-type ceiling.
        pool = []
        for cost in (1, 2, 3, 4, 5, 6, 7):
            pool += _pool(6, cost, ctype="Character")
            pool += _pool(6, cost, ctype="Action")
            pool += _pool(6, cost, ctype="Item")
            pool += _pool(6, cost, ctype="Location")
        picks = allocate_deck(pool)
        assert sum(qty for _, qty in picks) == 60
        type_totals: dict[str, int] = {}
        for card, qty in picks:
            type_totals[card["type"]] = type_totals.get(card["type"], 0) + qty
        assert len(type_totals) > 1
        assert type_totals.get("Item", 0) > 0
        assert type_totals.get("Location", 0) > 0

    def test_never_exceeds_4_copies_of_a_single_card(self):
        pool = _pool(2, 3)
        picks = allocate_deck(pool)
        for _, qty in picks:
            assert qty <= 4

    def test_deterministic_across_runs(self):
        pool = _pool(10, 3)
        picks_a = allocate_deck(pool)
        picks_b = allocate_deck(pool)
        assert [(c["fullName"], q) for c, q in picks_a] == [(c["fullName"], q) for c, q in picks_b]

    def test_empty_pool_returns_no_picks(self):
        assert allocate_deck([]) == []
