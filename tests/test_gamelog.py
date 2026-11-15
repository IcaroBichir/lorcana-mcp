"""Tests for gamelog.py: duels.ink game-log parsing and review tips.

Fixtures are two real duels.ink logs: a win copied with line breaks, and a
loss whose copy lost every line break (one long line). Card data comes from
a small JSON snapshot, so no network is needed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lorcana_mcp.gamelog import (
    OPP, YOU, analyze_game_log, format_game_review, read_deck_file,
    split_card_list, split_log_lines,
)

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def cards():
    return json.loads((FIX / "gamelog_cards.json").read_text())


@pytest.fixture(scope="module")
def win_log():
    return (FIX / "duels_log_win_multiline.txt").read_text()


@pytest.fixture(scope="module")
def loss_log():
    return (FIX / "duels_log_loss_oneline.txt").read_text()


class TestSplitting:
    def test_multiline_kept_as_is(self, win_log):
        lines = split_log_lines(win_log)
        assert lines[0].startswith("Your starting hand:")
        assert "--- Turn 1 ---" in lines

    def test_one_line_log_is_split_into_events(self, loss_log):
        assert loss_log.count("\n") <= 1
        lines = split_log_lines(loss_log)
        assert len(lines) > 400
        assert "Grandmother Willow - Ancient Advisor was banished" in lines
        assert "Opponent added Swooping Strike to ink" in lines
        assert "--- Turn 25 ---" in lines

    def test_one_line_split_matches_multiline_split(self, win_log):
        multi = split_log_lines(win_log)
        glued = split_log_lines("".join(multi))
        assert glued == multi

    def test_opening_quote_not_split(self):
        text = ('--- Turn 1 ---Opponent\'s turn beginsHades - Looking for a Deal\'s WHAT D\'YA SAY? '
                'chose "Let them draw"Opponent drew 2 cards' * 3) + "x" * 400
        lines = split_log_lines(text)
        assert any(l.endswith('chose "Let them draw"') for l in lines)

    def test_mcduck_not_split(self):
        lines = split_log_lines(("--- Turn 1 ---You played Scrooge McDuck - Ghostly Ebenezer (cost 4)" * 5) + "y" * 400)
        assert "You played Scrooge McDuck - Ghostly Ebenezer (cost 4)" in lines

    def test_card_list_with_commas(self, cards):
        known = dict(cards, **{"Malicious, Mean, and Scary": {}})
        assert split_card_list("Rex - Protective Dinosaur, Malicious, Mean, and Scary, RC - Remote-Controlled Car",
                               known) == ["Rex - Protective Dinosaur", "Malicious, Mean, and Scary",
                                          "RC - Remote-Controlled Car"]


@pytest.fixture(scope="module")
def win_r(win_log, cards):
    return analyze_game_log(win_log, card_index=cards)


@pytest.fixture(scope="module")
def loss_r(loss_log, cards):
    return analyze_game_log(loss_log, card_index=cards)


class TestWinGame:
    @pytest.fixture
    def r(self, win_r):
        return win_r

    def test_result_and_lore(self, r):
        s = r["state"]
        assert s.winner == YOU
        assert s.lore == {YOU: 21, OPP: 12}
        assert s.first_player == YOU
        assert s.unparsed == 0

    def test_undo_rolled_back(self, r):
        s = r["state"]
        assert s.undo_count == 2
        t9 = next(t for t in s.turns if t.number == 9)
        assert [c for c, _ in t9.played] == ["Woody - Helping a Friend", "Rex - Protective Dinosaur"]
        t13 = next(t for t in s.turns if t.number == 13)
        assert [c for c, _ in t13.played].count("Piercing Attack") == 1

    def test_mulligan_and_hand(self, r):
        s = r["state"]
        assert s.mulligan[YOU]["out"] == ["Merida - Gifted Archer", "Tod - Nimble Fox"]
        assert s.mulligan[OPP]["count"] == 4

    def test_ink_and_spend(self, r):
        t7 = next(t for t in r["state"].turns if t.number == 7)
        assert t7.ink_after == 4
        assert sum(p for _, p in t7.played) == 3

    def test_unanswered_quester_tip(self, r):
        assert any("Genie - Of the Lamp quested for 6 lore and was never removed" in t for t in r["tips"])

    def test_missed_ink_only_where_meaningful(self, r):
        missed = [t for t in r["tips"] if t.startswith("**Missed ink")]
        assert missed and "T9" in missed[0] and "T15" not in missed[0]

    def test_no_unspent_ink_tip_on_winning_turn(self, r):
        assert not any("T17:" in t for t in r["tips"] if t.startswith("**Unspent ink"))

    def test_opponent_inks(self, r):
        assert set(r["opp_colors"][:2]) == {"Amber", "Emerald"}


class TestLossGame:
    @pytest.fixture
    def r(self, loss_r):
        return loss_r

    def test_result(self, r):
        s = r["state"]
        assert s.winner == OPP
        assert s.lore == {YOU: 16, OPP: 20}
        assert s.first_player == OPP
        assert s.unparsed == 0

    def test_location_lore_counted_for_you(self, r):
        t10 = next(t for t in r["state"].turns if t.number == 10)
        assert t10.lore_after[YOU] == 4

    def test_damage_sweeper_tip(self, r):
        tip = next(t for t in r["tips"] if t.startswith("**Played into their damage removal"))
        assert "Three Arrows (4)" in tip and "Windstorm (2)" in tip

    def test_late_removal_tip(self, r):
        assert any("Demona - Scourge of the Wyvern Clan quested for 10 lore before you removed it (turn 22)" in t
                   for t in r["tips"])

    def test_quest_into_challenge(self, r):
        tip = next(t for t in r["tips"] if t.startswith("**Quested into a challenge"))
        assert "T12 Woody - Jungle Guide" in tip

    def test_no_wrong_ink_archetype_guess(self, r):
        # A guess is fine (DLC London added an Amethyst/Steel list); it must
        # just never come from a different ink pair.
        if r["opp_guess"] is not None:
            assert r["opp_guess"][0].startswith("Amethyst / Steel")
        assert set(r["opp_colors"][:2]) == {"Amethyst", "Steel"}

    def test_rendered_review(self, r):
        out = format_game_review(r)
        assert out.startswith("# Game review — **Loss 16–20**")
        assert "## Tips" in out and "No deck list given" in out


class TestDeck:
    DECK = "\n".join([
        "4x Woody - Waiting for a Friend", "4x Alien - True Believer", "4x Rex - Protective Dinosaur",
        "4x Merida - Defiant Daughter", "1x Gaston - Superior Archer", "4x Woody - Jungle Guide",
        "4x Hamm - Piggy Bank",
    ])

    def test_deck_notes(self, win_log, cards):
        r = analyze_game_log(win_log, deck_text=self.DECK, card_index=cards)
        notes = " ".join(r["deck_notes"])
        assert "Hamm - Piggy Bank" in notes          # 4-of never seen
        assert "Elinor - Renowned Diplomat" in notes  # in the log, not in the list
        assert any("Gaston - Superior Archer (only 1 in the deck)" in t for t in r["tips"])
        assert "No deck list given" not in format_game_review(r)

    def test_read_deck_file_skips_retired_blocks(self, tmp_path):
        f = tmp_path / "deck.md"
        f.write_text(
            "# Deck\n\n## Reference list\n\n```\n4x Old Card - A\n```\n\n"
            "## duels.ink Import List\n\n```\n4x Current Card - B\n```\n\n"
            "## v1 Import List (retired)\n\n```\n4x Retired Card - C\n```\n"
        )
        assert read_deck_file(str(f)).strip() == "4x Current Card - B"


def test_not_a_log(cards):
    r = analyze_game_log("hello there", card_index=cards)
    assert "error" in r
