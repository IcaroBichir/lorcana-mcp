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
    compute_shift_synergy,
    _shift_target_names,
    compute_coconut_synergy,
    ensure_coconut_associated_card,
)


def _card(name, cost, ctype, colors, lore=0, strength=0, willpower=0, subtypes=None,
          keywords=None, full_text="", set_code="12", number=1, rarity="Common", inkwell=True,
          card_name=None):
    abilities = [{"type": "keyword", "keyword": kw} for kw in (keywords or [])]
    return {
        "fullName": name,
        "name": card_name if card_name is not None else name.split(" - ")[0],
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


def _shift_card(name, card_name, cost, keyword, reminder_text="", **kw):
    """A character with a single Shift-family keyword ability, for
    synergy-detection tests. `card_name` is LorcanaJSON's `name` field
    (base name before " - subtitle") — the thing `_shift_target_names`
    actually reads, distinct from the test-helper default in `_card`."""
    card = _card(name, cost, "Character", ["Emerald"], card_name=card_name, **kw)
    card["abilities"] = [{
        "type": "keyword", "keyword": keyword, "reminderText": reminder_text,
    }]
    return card


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

    def test_named_shift_variants_score_same_as_plain_shift(self):
        # Set 13 introduced Duo Shift, Combo Shift, Potato Shift, Madrigal
        # Shift, Floodborn Shift, Temporary Shift, and Temporary Red Panda
        # Shift — none spelled exactly "Shift", so an exact-match keyword
        # lookup would silently score them as 0.0 instead of crediting the
        # same discounted-alternate-cost value plain Shift gets.
        base = _card("Base", 4, "Character", ["Emerald"], lore=1, strength=2, willpower=3)
        plain_shift = _card("Plain Shift", 4, "Character", ["Emerald"], lore=1, strength=2,
                             willpower=3, keywords=["Shift"])
        duo_shift = _card("Duo Shift", 4, "Character", ["Emerald"], lore=1, strength=2,
                           willpower=3, keywords=["Duo Shift"])
        combo_shift = _card("Combo Shift", 4, "Character", ["Emerald"], lore=1, strength=2,
                             willpower=3, keywords=["Combo Shift"])
        potato_shift = _card("Potato Shift", 4, "Character", ["Emerald"], lore=1, strength=2,
                              willpower=3, keywords=["Potato Shift"])
        assert score_card(duo_shift) == score_card(plain_shift) > score_card(base)
        assert score_card(combo_shift) == score_card(plain_shift)
        assert score_card(potato_shift) == score_card(plain_shift)

    def test_unrelated_keyword_still_scores_zero_bonus(self):
        # Guards against the substring fallback being too broad — a keyword
        # that merely happens to not be in the dict (and doesn't contain
        # "shift") must still score 0.0, not fall through to the Shift value.
        base = _card("Base", 3, "Character", ["Amber"], lore=1, strength=2, willpower=2)
        unknown_kw = _card("Unknown Keyword", 3, "Character", ["Amber"], lore=1, strength=2,
                            willpower=2, keywords=["Totally Made Up Keyword"])
        assert score_card(unknown_kw) == score_card(base)


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


# ── _shift_target_names ─────────────────────────────────────────────────────

class TestShiftTargetNames:
    def test_plain_solo_name_shift(self):
        card = _shift_card("Robin Hood - Champion of Sherwood", "Robin Hood", 5, "Shift")
        assert _shift_target_names(card) == ("Character", "any", ["Robin Hood"])

    def test_compound_ampersand_name_is_any_relation_for_plain_shift(self):
        card = _shift_card("Aladdin & Genie - Mischievous Pals", "Aladdin & Genie", 3, "Shift")
        assert _shift_target_names(card) == ("Character", "any", ["Aladdin", "Genie"])

    def test_apostrophe_n_separator(self):
        card = _shift_card("Chip 'n' Dale - Recovery Rangers", "Chip 'n' Dale", 5, "Shift")
        assert _shift_target_names(card) == ("Character", "any", ["Chip", "Dale"])

    def test_duo_shift_is_all_relation(self):
        card = _shift_card(
            "Mickey Mouse & Minnie Mouse - Adventuring Duo",
            "Mickey Mouse & Minnie Mouse", 7, "Duo Shift",
        )
        assert _shift_target_names(card) == (
            "Character", "all", ["Mickey Mouse", "Minnie Mouse"],
        )

    def test_combo_shift_is_any_relation(self):
        card = _shift_card(
            "Dash Parr & Violet Parr - Super Siblings",
            "Dash Parr & Violet Parr", 8, "Combo Shift",
        )
        assert _shift_target_names(card) == (
            "Character", "any", ["Dash Parr", "Violet Parr"],
        )

    def test_potato_shift_targets_an_item_parsed_from_reminder_text(self):
        card = _shift_card(
            "Posey - Vampire Potato", "Posey", 7, "Potato Shift",
            reminder_text="You may pay 5 ⬡ to play this on top of one of your items named Potato.",
        )
        assert _shift_target_names(card) == ("Item", "any", ["Potato"])

    def test_subtype_targeted_shift_variants_return_none(self):
        for keyword, subtype_text in [
            ("Floodborn Shift", "one of your Floodborn characters"),
            ("Madrigal Shift", "one of your Madrigal characters"),
            ("Puppy Shift", "one of your Puppy characters"),
            ("Temporary Red Panda Shift", "one of your Red Panda characters"),
            ("Universal Shift", "any one of your characters"),
        ]:
            card = _shift_card("Whatever - Subtitle", "Whatever", 4, keyword,
                                reminder_text=f"You may pay 4 ⬡ to play this on top of {subtype_text}.")
            assert _shift_target_names(card) is None, keyword

    def test_non_shift_card_returns_none(self):
        card = _card("Vanilla - Body", 3, "Character", ["Amber"], keywords=["Evasive"])
        assert _shift_target_names(card) is None


# ── compute_shift_synergy ────────────────────────────────────────────────────

class TestComputeShiftSynergy:
    def test_bonus_and_info_when_payoff_and_enabler_both_in_pool(self):
        payoff = _shift_card(
            "Mickey Mouse & Minnie Mouse - Adventuring Duo",
            "Mickey Mouse & Minnie Mouse", 7, "Duo Shift",
        )
        mickey = _card("Mickey Mouse - Inquisitive Explorer", 4, "Character", ["Sapphire"],
                        card_name="Mickey Mouse")
        minnie = _card("Minnie Mouse - Curious Adventurer", 1, "Character", ["Emerald"],
                        card_name="Minnie Mouse")
        bonus, info = compute_shift_synergy([payoff, mickey, minnie])

        assert bonus[payoff["fullName"]] > 0
        assert bonus[mickey["fullName"]] > 0
        assert bonus[minnie["fullName"]] > 0
        assert len(info) == 1
        assert info[0]["payoff"] == payoff["fullName"]
        assert info[0]["relation"] == "all"
        assert set(info[0]["enablers_found"]) == {mickey["fullName"], minnie["fullName"]}

    def test_no_bonus_for_all_relation_missing_one_side(self):
        # Duo Shift needs BOTH names — only Mickey present means the combo
        # genuinely can't be assembled, so nothing should be rewarded for it.
        payoff = _shift_card(
            "Mickey Mouse & Minnie Mouse - Adventuring Duo",
            "Mickey Mouse & Minnie Mouse", 7, "Duo Shift",
        )
        mickey = _card("Mickey Mouse - Inquisitive Explorer", 4, "Character", ["Sapphire"],
                        card_name="Mickey Mouse")
        bonus, info = compute_shift_synergy([payoff, mickey])

        assert bonus == {}
        assert info == []

    def test_bonus_for_any_relation_with_only_one_side_present(self):
        # Combo Shift's "one named X, one named Y, or one of each" means
        # either alone is already sufficient.
        payoff = _shift_card(
            "Dash Parr & Violet Parr - Super Siblings",
            "Dash Parr & Violet Parr", 8, "Combo Shift",
        )
        dash = _card("Dash Parr - Dodgeball Dynamo", 1, "Character", ["Ruby"],
                      card_name="Dash Parr")
        bonus, info = compute_shift_synergy([payoff, dash])

        assert bonus[payoff["fullName"]] > 0
        assert bonus[dash["fullName"]] > 0
        assert info[0]["relation"] == "any"
        assert info[0]["enablers_found"] == [dash["fullName"]]

    def test_no_synergy_entries_when_pool_has_no_shift_cards(self):
        vanilla = _card("Vanilla - Body", 3, "Character", ["Amber"])
        bonus, info = compute_shift_synergy([vanilla])
        assert bonus == {}
        assert info == []


# ── allocate_deck: "all"-relation synergy guarantee ─────────────────────────

class TestAllocateDeckSynergyGuarantee:
    def test_bonus_alone_can_leave_a_weak_enabler_out(self):
        # Baseline: without synergy_info, only the scoring bonus applies —
        # a sufficiently weak enabler can still lose out to unrelated cards
        # on raw score, same as the real Mickey/Minnie case this was built
        # to fix.
        payoff = _shift_card(
            "Mickey Mouse & Minnie Mouse - Adventuring Duo",
            "Mickey Mouse & Minnie Mouse", 7, "Duo Shift",
            lore=5, strength=5, willpower=5,
        )
        strong1 = _card("Strong Filler 1", 1, "Character", ["Emerald"], strength=4, willpower=4, lore=2)
        strong2 = _card("Strong Filler 2", 1, "Character", ["Emerald"], strength=3, willpower=4, lore=2)
        mickey = _card("Mickey Mouse - Inquisitive Explorer", 1, "Character", ["Emerald"],
                        card_name="Mickey Mouse", strength=2, willpower=3, lore=1)
        neutral = _card("Neutral Weak Filler", 1, "Character", ["Emerald"], strength=1, willpower=2, lore=1)
        minnie = _card("Minnie Mouse - Curious Adventurer", 1, "Character", ["Emerald"],
                        card_name="Minnie Mouse", strength=1, willpower=1, lore=0)
        pool = [payoff, strong1, strong2, mickey, neutral, minnie]
        targets = {"1-2": 4, "3-4": 0, "5-6": 0, "7+": 1}

        bonus, info = compute_shift_synergy(pool)
        picks = allocate_deck(pool, targets=targets, max_copies_fn=lambda c: 1,
                               synergy_bonus=bonus)  # no synergy_info -> no guarantee pass
        picked_names = {c["fullName"] for c, _ in picks}

        assert payoff["fullName"] in picked_names
        assert mickey["fullName"] in picked_names
        assert minnie["fullName"] not in picked_names  # the gap this feature closes
        assert sum(q for _, q in picks) == 5

    def test_synergy_info_guarantees_the_missing_side_is_added(self):
        payoff = _shift_card(
            "Mickey Mouse & Minnie Mouse - Adventuring Duo",
            "Mickey Mouse & Minnie Mouse", 7, "Duo Shift",
            lore=5, strength=5, willpower=5,
        )
        strong1 = _card("Strong Filler 1", 1, "Character", ["Emerald"], strength=4, willpower=4, lore=2)
        strong2 = _card("Strong Filler 2", 1, "Character", ["Emerald"], strength=3, willpower=4, lore=2)
        mickey = _card("Mickey Mouse - Inquisitive Explorer", 1, "Character", ["Emerald"],
                        card_name="Mickey Mouse", strength=2, willpower=3, lore=1)
        neutral = _card("Neutral Weak Filler", 1, "Character", ["Emerald"], strength=1, willpower=2, lore=1)
        minnie = _card("Minnie Mouse - Curious Adventurer", 1, "Character", ["Emerald"],
                        card_name="Minnie Mouse", strength=1, willpower=1, lore=0)
        pool = [payoff, strong1, strong2, mickey, neutral, minnie]
        targets = {"1-2": 4, "3-4": 0, "5-6": 0, "7+": 1}

        bonus, info = compute_shift_synergy(pool)
        picks = allocate_deck(pool, targets=targets, max_copies_fn=lambda c: 1,
                               synergy_bonus=bonus, synergy_info=info)
        picked_names = {c["fullName"] for c, _ in picks}

        assert payoff["fullName"] in picked_names
        assert mickey["fullName"] in picked_names
        assert minnie["fullName"] in picked_names  # forced in by the guarantee pass
        assert sum(q for _, q in picks) == 5  # total held constant
        # The weakest kept filler (Neutral Weak Filler) is what got trimmed
        # to make room, not the Mickey enabler or either strong filler.
        assert "Neutral Weak Filler" not in picked_names
        assert strong1["fullName"] in picked_names
        assert strong2["fullName"] in picked_names

    def test_guarantee_pass_is_a_noop_without_a_landed_payoff(self):
        # If the payoff itself never made it into the deck, there's nothing
        # to guarantee enablers for.
        mickey = _card("Mickey Mouse - Inquisitive Explorer", 1, "Character", ["Emerald"],
                        card_name="Mickey Mouse", strength=1, willpower=1, lore=1)
        minnie = _card("Minnie Mouse - Curious Adventurer", 1, "Character", ["Emerald"],
                        card_name="Minnie Mouse", strength=1, willpower=1, lore=0)
        payoff = _shift_card(
            "Mickey Mouse & Minnie Mouse - Adventuring Duo",
            "Mickey Mouse & Minnie Mouse", 7, "Duo Shift",
        )
        pool = [mickey, minnie]  # payoff deliberately excluded from the pool
        info = compute_shift_synergy(pool)[1]
        assert info == []  # nothing to detect without the payoff present

        picks = allocate_deck(pool, targets={"1-2": 2, "3-4": 0, "5-6": 0, "7+": 0},
                               max_copies_fn=lambda c: 1, synergy_info=info)
        assert sum(q for _, q in picks) == 2


# ── Format Coconut synergy (beta) ────────────────────────────────────────────

def _coconut(name, associated_full_name, color="Amber"):
    return {
        "name": name,
        "color": color,
        "associatedCardName": associated_full_name,
        "abilities": [{"effect": f"You can have up to 4 copies of {associated_full_name} in your deck."}],
    }


class TestComputeCoconutSynergy:
    def test_associated_card_gets_the_higher_bonus(self):
        associated = _card("Scar - Finally King", 3, "Character", ["Steel"])
        pool = [associated]
        bonus = compute_coconut_synergy(pool, _coconut("Scar", "Scar - Finally King", "Steel"))
        assert bonus["Scar - Finally King"] == 4.0

    def test_tag_matched_cards_get_the_lower_bonus(self):
        ally = _card("Some Ally", 2, "Character", ["Steel"], subtypes=["Ally"])
        non_ally = _card("Some Hero", 2, "Character", ["Steel"], subtypes=["Hero"])
        pool = [ally, non_ally]
        bonus = compute_coconut_synergy(pool, _coconut("Scar", "Scar - Finally King", "Steel"))
        assert bonus.get("Some Ally") == 2.0
        assert "Some Hero" not in bonus

    def test_associated_card_bonus_wins_over_tag_bonus_for_same_card(self):
        # Scar's own associated card happens to also be an Ally — associated
        # (4.0) must win, not get overwritten by the lower tag bonus (2.0).
        associated = _card("Scar - Finally King", 3, "Character", ["Steel"], subtypes=["Ally"])
        bonus = compute_coconut_synergy([associated], _coconut("Scar", "Scar - Finally King", "Steel"))
        assert bonus["Scar - Finally King"] == 4.0

    def test_unknown_coconut_name_still_bonuses_associated_card_only(self):
        associated = _card("Made Up - Character", 2, "Character", ["Amber"])
        other = _card("Unrelated Card", 2, "Character", ["Amber"])
        bonus = compute_coconut_synergy(
            [associated, other], _coconut("Not A Real Coconut", "Made Up - Character"),
        )
        assert bonus == {"Made Up - Character": 4.0}

    def test_no_matches_returns_empty(self):
        card = _card("Nothing Special", 2, "Character", ["Amber"])
        bonus = compute_coconut_synergy([card], _coconut("Scar", "Scar - Finally King", "Steel"))
        assert bonus == {}


class TestEnsureCoconutAssociatedCard:
    def test_noop_when_already_present(self):
        associated = _card("Scar - Finally King", 3, "Character", ["Steel"])
        picks = [(associated, 2)]
        result = ensure_coconut_associated_card(
            picks, [associated], "Scar - Finally King", max_copies_fn=lambda c: 4,
        )
        assert result == picks

    def test_forces_in_missing_card_trimming_weakest_picks(self):
        associated = _card("Scar - Finally King", 6, "Character", ["Steel"], strength=1, willpower=1, lore=1)
        weak_fillers = [
            _card(f"Weak Filler {i}", 1, "Character", ["Steel"], strength=0, willpower=1, lore=0)
            for i in range(4)
        ]
        strong = _card("Strong Filler", 1, "Character", ["Steel"], strength=3, willpower=3, lore=2)
        pool = [associated, strong, *weak_fillers]
        # associated missing; 4 weak singles + 1 strong single = total 5
        picks = [(strong, 1)] + [(w, 1) for w in weak_fillers]

        result = ensure_coconut_associated_card(
            picks, pool, "Scar - Finally King", max_copies_fn=lambda c: 4,
        )
        result_map = {c["fullName"]: q for c, q in result}

        assert result_map["Scar - Finally King"] == 4
        assert not any(f"Weak Filler {i}" in result_map for i in range(4))  # trimmed to make room
        assert result_map["Strong Filler"] == 1  # kept — it scored higher
        assert sum(result_map.values()) == 5  # total held constant

    def test_trim_is_capped_by_available_picks(self):
        # Only 2 total copies exist across current picks, so at most 2 can be
        # freed up even though max_copies_fn allows 4 — the function never
        # invents extra deck slots, it only reshuffles existing ones.
        associated = _card("Scar - Finally King", 6, "Character", ["Steel"], strength=1, willpower=1, lore=1)
        weak = _card("Weak Filler", 1, "Character", ["Steel"], strength=0, willpower=1, lore=0)
        strong = _card("Strong Filler", 1, "Character", ["Steel"], strength=3, willpower=3, lore=2)
        pool = [associated, weak, strong]
        picks = [(weak, 1), (strong, 1)]

        result = ensure_coconut_associated_card(
            picks, pool, "Scar - Finally King", max_copies_fn=lambda c: 4,
        )
        result_map = {c["fullName"]: q for c, q in result}

        assert result_map["Scar - Finally King"] == 2
        assert sum(result_map.values()) == 2  # total held constant

    def test_noop_when_not_in_legal_pool(self):
        weak = _card("Weak Filler", 1, "Character", ["Steel"])
        picks = [(weak, 1)]
        result = ensure_coconut_associated_card(
            picks, [weak], "Scar - Finally King", max_copies_fn=lambda c: 4,
        )
        assert result == picks

    def test_noop_when_max_copies_is_zero(self):
        # e.g. mode="collection" and zero copies of the associated card owned.
        associated = _card("Scar - Finally King", 3, "Character", ["Steel"])
        weak = _card("Weak Filler", 1, "Character", ["Steel"])
        pool = [associated, weak]
        picks = [(weak, 1)]
        result = ensure_coconut_associated_card(
            picks, pool, "Scar - Finally King", max_copies_fn=lambda c: 0,
        )
        assert result == picks

    def test_noop_with_empty_associated_name(self):
        weak = _card("Weak Filler", 1, "Character", ["Steel"])
        picks = [(weak, 1)]
        result = ensure_coconut_associated_card(picks, [weak], "", max_copies_fn=lambda c: 4)
        assert result == picks
