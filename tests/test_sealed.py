"""Tests for sealed.py — Sealed/prerelease pool resolution and deck building
(pure logic, no network) — plus the build_sealed_deck tool wiring."""
from __future__ import annotations

from unittest.mock import patch

from lorcana_mcp.sealed import build_sealed_deck, rank_ink_pairs, resolve_pool
from lorcana_mcp.deckbuilder import score_card


def _card(name, cost, color, number, set_code="14", ctype="Character", lore=1,
          strength=2, willpower=2, keywords=None, inkwell=True, card_name=None):
    colors = color.split("-")
    return {
        "fullName": name,
        "name": card_name if card_name is not None else name.split(" - ")[0],
        "version": name.split(" - ")[1] if " - " in name else "",
        "cost": cost, "type": ctype, "color": color,
        "colors": colors if len(colors) > 1 else None,
        "lore": lore, "strength": strength, "willpower": willpower,
        "subtypes": [], "abilities": [{"type": "keyword", "keyword": k} for k in (keywords or [])],
        "fullText": "", "setCode": set_code, "number": number, "rarity": "Common",
        "inkwell": inkwell,
    }


def _set_cards():
    """A tiny fake Set 14: three Merlins (for bare-name ambiguity), an
    Enchanted reprint of Mickey (#210, same fullName), and an older-set card."""
    return [
        _card("Mickey Mouse - Best in Town", 2, "Amber", 23),
        _card("Mickey Mouse - Best in Town", 2, "Amber", 210),
        _card("Merlin - Bauble Expert", 3, "Amethyst", 39),
        _card("Merlin - Ink Drop Tinkerer", 4, "Amethyst", 52),
        _card("Merlin - Profoundly Curious", 2, "Amethyst", 57),
        _card("Minnie Mouse - Urban Visionary", 8, "Sapphire", 155),
        _card("Goofy - Musketeer", 5, "Amber", 4, set_code="1"),
    ]


def _pool(color_counts):
    """{color: n} → a pool of n distinct, equal-strength single-copy cards per color."""
    pool, n = [], 1
    for color, count in color_counts.items():
        for i in range(count):
            pool.append((_card(f"{color} Card - {i}", (i % 6) + 1, color, n), 1))
            n += 1
    return pool


class TestResolvePool:
    def test_collector_number_formats(self):
        text = "23\n155/204\n2x 39/204 EN 14\n#57\n3x #52"
        r = resolve_pool(text, _set_cards(), "14")
        got = {c["fullName"]: q for c, q in r["pool"]}
        assert got == {
            "Mickey Mouse - Best in Town": 1,
            "Minnie Mouse - Urban Visionary": 1,
            "Merlin - Bauble Expert": 2,
            "Merlin - Profoundly Curious": 1,
            "Merlin - Ink Drop Tinkerer": 3,
        }

    def test_hash_comment_still_skipped(self):
        r = resolve_pool("# my pool\n23", _set_cards(), "14")
        assert sum(q for _, q in r["pool"]) == 1
        assert not r["unresolved"]

    def test_enchanted_number_merges_with_base(self):
        r = resolve_pool("23\n210", _set_cards(), "14")
        assert [(c["fullName"], q) for c, q in r["pool"]] == [("Mickey Mouse - Best in Town", 2)]

    def test_informal_name_resolves(self):
        r = resolve_pool("mickey best in town", _set_cards(), "14")
        assert r["pool"][0][0]["fullName"] == "Mickey Mouse - Best in Town"

    def test_bare_name_with_several_versions_is_ambiguous_not_guessed(self):
        r = resolve_pool("merlin", _set_cards(), "14")
        assert r["pool"] == []
        line, qty, cands = r["ambiguous"][0]
        assert line == "merlin" and len(cands) == 3

    def test_falls_back_to_other_sets_by_name(self):
        r = resolve_pool("Goofy - Musketeer", _set_cards(), "14")
        assert r["pool"][0][0]["fullName"] == "Goofy - Musketeer"

    def test_unknown_lines_reported(self):
        r = resolve_pool("Totally Fake Card\n999", _set_cards(), "14")
        assert r["pool"] == []
        assert [line for line, _ in r["unresolved"]] == ["Totally Fake Card", "999"]


class TestRankInkPairs:
    def test_deepest_pair_first(self):
        ranked = rank_ink_pairs(_pool({"Amber": 15, "Steel": 14, "Ruby": 5}))
        assert ranked[0]["colors"] == ["Amber", "Steel"]
        assert ranked[0]["playables"] == 29
        assert len(ranked) == 15

    def test_dual_ink_card_counts_only_for_its_pair(self):
        pool = [(_card("Dual - Card", 3, "Amber-Steel", 1), 1)]
        ranked = {tuple(r["colors"]): r["playables"] for r in rank_ink_pairs(pool)}
        assert ranked[("Amber", "Steel")] == 1
        assert ranked[("Amber", "Ruby")] == 0


class TestBuildSealedDeck:
    def test_deep_pair_needs_no_splash(self):
        result = build_sealed_deck(_pool({"Amber": 22, "Steel": 22, "Ruby": 10}))
        assert result["core"] == ["Amber", "Steel"]
        assert result["splashes"] == []
        assert result["total"] == 40
        assert all(c["color"] in ("Amber", "Steel") for c, _ in result["picks"])

    def test_shallow_pair_splashes_to_reach_40(self):
        result = build_sealed_deck(_pool({"Amber": 15, "Steel": 14, "Ruby": 12, "Emerald": 6}))
        assert result["core"] == ["Amber", "Steel"]
        assert result["splashes"] == ["Ruby"]
        assert result["total"] == 40

    def test_no_copy_limit(self):
        pool = _pool({"Amber": 20, "Steel": 14}) + [(_card("Big - Stack", 3, "Amber", 999, lore=3), 6)]
        picks = dict((c["fullName"], q) for c, q in build_sealed_deck(pool)["picks"])
        assert picks["Big - Stack"] == 6

    def test_never_exceeds_opened_quantity(self):
        result = build_sealed_deck(_pool({"Amber": 10, "Steel": 10}))
        assert result["total"] == 20  # whole pool, honest shortfall
        assert all(q == 1 for _, q in result["picks"])

    def test_forced_inks(self):
        result = build_sealed_deck(_pool({"Amber": 22, "Steel": 22, "Ruby": 25}), ["Ruby", "Steel"])
        assert result["core"] == ["Ruby", "Steel"]
        assert result["total"] == 40

    def test_sideboard_is_everything_unused(self):
        pool = _pool({"Amber": 22, "Steel": 22, "Ruby": 3})
        result = build_sealed_deck(pool)
        assert sum(q for _, q in result["sideboard"]) == sum(q for _, q in pool) - 40


class TestNewKeywordScoring:
    def test_alert_beats_vanilla_and_adventurous_is_a_drawback(self):
        vanilla = _card("A - Vanilla", 3, "Steel", 1)
        alert = _card("B - Alert", 3, "Steel", 2, keywords=["Alert"])
        adventurous = _card("C - Adventurous", 3, "Steel", 3, keywords=["Adventurous"])
        assert score_card(alert) > score_card(vanilla) > score_card(adventurous)


class TestBuildSealedDeckTool:
    def test_output_sections(self):
        from lorcana_mcp.server import build_sealed_deck as tool
        cards = [c for c, _ in _pool({"Amber": 22, "Steel": 22})]
        text = "\n".join(c["fullName"] for c in cards) + "\nmerlin\nNope Card"
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=cards + _set_cards()):
            out = tool(text)
        assert "## Sealed deck — Amber/Steel" in out
        assert "### Decklist (40 cards)" in out
        assert "### Ink pairs by pool depth" in out
        assert "### Ambiguous" in out and '"merlin"' in out
        assert "### Unrecognized" in out and '"Nope Card"' in out

    def test_bad_ink_and_set(self):
        from lorcana_mcp.server import build_sealed_deck as tool
        assert "Unknown ink color" in tool("x", ink_colors="Purple")
        assert "Unknown set" in tool("x", set_name="Nowhere Land")

    def test_empty_pool(self):
        from lorcana_mcp.server import build_sealed_deck as tool
        with patch("lorcana_mcp.server.fetch_lorcana_json", return_value=_set_cards()):
            assert "No cards recognized" in tool("Nope Card")
