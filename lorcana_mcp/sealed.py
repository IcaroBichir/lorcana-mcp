"""Sealed (prerelease) deck building: resolve an opened card pool and build
the best 40-card deck from it.

Sealed rules (Disney Lorcana prerelease): decks are built on-site from the
cards opened (6 booster packs, ~72 cards), minimum 40 cards, **no ink-color
limit** and **no copy limit** — you can play every copy you open. Unused
cards are the sideboard and can be swapped between games.

Because ink is colorless in Lorcana (any inkable card pays for any card),
playing more than two inks costs no mana consistency — only synergy. That
shapes the strategy here: build around the deepest two-ink pair in the pool,
and only splash a third (or fourth) ink when that pair can't reach 40 cards
on its own, which is common from just 6 packs (~24 cards per pair on
average). Everything is pure logic over an already-fetched card list — no
network — so it's directly testable; `build_sealed_deck` in server.py does
the fetching and formatting.
"""
from __future__ import annotations

import re
from itertools import combinations

from .api import _card_colors, _card_score, _tokenize, dedupe_by_full_name
from .deck import parse_deck_list
from .deckbuilder import (
    _color_subset_ok as _lower_subset_ok, allocate_deck, compute_shift_synergy, curve_targets, score_card,
)

SEALED_DECK_SIZE = 40
INK_COLORS = ["Amber", "Amethyst", "Emerald", "Ruby", "Sapphire", "Steel"]



def _color_subset_ok(card: dict, colors: set[str]) -> bool:
    """deckbuilder's subset check, but taking display-case ink names."""
    return _lower_subset_ok(card, {c.lower() for c in colors})


# "123", "#123", "123/204", "123/204 EN 14" — the collector line printed at
# the bottom of every card, which is the most reliable thing to read off a
# photo of a card pool (names can be partially covered or glare-washed).
_NUMBER_RE = re.compile(
    r"#?\s*(\d{1,3})(?:\s*/\s*\d{1,3})?(?:\s*[·•|-]?\s*[A-Z]{2})?(?:\s*[·•|-]?\s*\d{1,2})?",
    re.IGNORECASE,
)

_HASH_NUMBER_RE = re.compile(r"^(\s*(?:\d+\s*[xX]?\s+)?)#\s*(?=\d)", re.MULTILINE)

# A name query resolves when the best card clears this score and is clearly
# ahead of the runner-up. Mirrors api.resolve_card's thresholds, slightly
# looser on the score because the search is scoped to one set's ~250 cards
# (far fewer near-collisions than the full ~3,000-card pool).
_MIN_SCORE = 0.6
_MIN_GAP = 0.1


def _resolve_line(
    query: str, set_cards: list[dict], scoped: list[dict], everything: list[dict],
) -> tuple[dict | None, list[dict]]:
    """Resolve one pool line to a card. Returns (card, []) when confident, or
    (None, candidates) when ambiguous / not found (candidates may be empty).

    Collector numbers are matched against every printing in the scoped set
    (`set_cards`, not deduped — Enchanted/Epic alt-arts have their own
    numbers past 204 but share the base card's fullName). Names are
    tried against the scoped set first, then the whole card pool — so a
    stray older-set card or promo still resolves.
    """
    m = _NUMBER_RE.fullmatch(query.strip())
    if m:
        number = int(m.group(1))
        for c in set_cards:
            if c.get("number") == number:
                return c, []
        return None, []

    tokens = _tokenize(query)
    if not tokens:
        return None, []
    token_set = set(tokens)
    for cards in (scoped, everything):
        for c in cards:
            if token_set == set(_tokenize(c.get("fullName", ""))):
                return c, []
        scored: list[tuple[float, dict]] = []
        for c in cards:
            score = _card_score(tokens, c)
            if score > 0:
                scored.append((score, c))
        if not scored:
            continue
        scored.sort(key=lambda sc: -sc[0])
        top_score, top = scored[0]
        runner_up = scored[1][0] if len(scored) > 1 else 0.0
        # A bare character name ("merlin") ties every version at 1.0 — that's
        # ambiguous, not confident, so the gap check applies even at the top.
        if top_score >= _MIN_SCORE and top_score - runner_up >= _MIN_GAP:
            return top, []
        if top_score >= _MIN_SCORE:
            return None, [c for _, c in scored[:3]]
    return None, []


def resolve_pool(pool_text: str, lj_cards: list[dict], set_code: str | None) -> dict:
    """Parse and resolve a pasted/transcribed pool list.

    Returns {"pool": [(card, qty), ...] merged by fullName (Enchanted/Epic
    alt-arts collapse into their base card), "ambiguous": [(line, qty,
    [candidate cards])], "unresolved": [(line, qty)]}.
    """
    everything = dedupe_by_full_name(lj_cards)
    set_cards = [c for c in lj_cards if set_code and str(c.get("setCode")) == set_code]
    scoped = dedupe_by_full_name(set_cards) or everything

    merged: dict[str, list] = {}
    ambiguous: list[tuple[str, int, list[dict]]] = []
    unresolved: list[tuple[str, int]] = []
    # "#123" is a collector number here, not a comment — un-hash it before
    # the shared deck-list parser (which skips "#" lines) sees it.
    pool_text = _HASH_NUMBER_RE.sub(r"\1", pool_text)
    for qty, line in parse_deck_list(pool_text):
        card, candidates = _resolve_line(line, set_cards, scoped, everything)
        if card is None:
            if candidates:
                ambiguous.append((line, qty, candidates))
            else:
                unresolved.append((line, qty))
            continue
        name = card.get("fullName", "")
        if name in merged:
            merged[name][1] += qty
        else:
            merged[name] = [card, qty]
    return {
        "pool": [(c, q) for c, q in merged.values()],
        "ambiguous": ambiguous,
        "unresolved": unresolved,
    }


def _copy_scores(pool: list[tuple[dict, int]], colors: set[str]) -> list[float]:
    """Every individual copy's score among cards playable in `colors`, best first."""
    scores: list[float] = []
    for card, qty in pool:
        if _color_subset_ok(card, colors):
            scores.extend([score_card(card)] * qty)
    return sorted(scores, reverse=True)


def rank_ink_pairs(pool: list[tuple[dict, int]], deck_size: int = SEALED_DECK_SIZE) -> list[dict]:
    """Rank every two-ink pair by pool depth: the summed score of its best
    `deck_size` copies. A pair that can't reach `deck_size` alone just sums
    what it has, so a deep pair outranks a shallow one with a few bombs.
    Returns [{"colors": [a, b], "playables": n, "strength": float}] best-first."""
    ranked = []
    for a, b in combinations(INK_COLORS, 2):
        scores = _copy_scores(pool, {a, b})
        ranked.append({
            "colors": [a, b],
            "playables": len(scores),
            "strength": round(sum(scores[:deck_size]), 1),
        })
    ranked.sort(key=lambda r: (-r["strength"], -r["playables"], r["colors"]))
    return ranked


def _choose_splashes(pool: list[tuple[dict, int]], core: set[str], deck_size: int) -> list[str]:
    """Add the fewest extra inks needed to reach `deck_size` playable copies,
    each time picking the ink whose best cards add the most score for the
    slots still open."""
    colors = set(core)
    splashes: list[str] = []
    while len(_copy_scores(pool, colors)) < deck_size:
        need = deck_size - len(_copy_scores(pool, colors))
        best_color, best_gain = None, 0.0
        for c in INK_COLORS:
            if c in colors:
                continue
            gained = [
                score_card(card)
                for card, qty in pool
                if _color_subset_ok(card, colors | {c}) and not _color_subset_ok(card, colors)
                for _ in range(qty)
            ]
            gain = sum(sorted(gained, reverse=True)[:need])
            if gained and (best_color is None or gain > best_gain):
                best_color, best_gain = c, gain
        if best_color is None:
            break  # the whole pool is smaller than deck_size
        colors.add(best_color)
        splashes.append(best_color)
    return splashes


def build_sealed_deck(
    pool: list[tuple[dict, int]],
    ink_colors: list[str] | None = None,
    deck_size: int = SEALED_DECK_SIZE,
) -> dict:
    """Build a `deck_size`-card Sealed deck from a resolved pool.

    `ink_colors` forces the core inks (any number — Sealed has no ink
    limit); otherwise the top pair from `rank_ink_pairs` is used. Extra inks
    are splashed only if the core inks can't reach `deck_size` on their own.

    Returns {"core": [...], "splashes": [...], "picks": [(card, qty)],
    "sideboard": [(card, qty)], "pair_ranking": [...], "total": int}.
    """
    pair_ranking = rank_ink_pairs(pool, deck_size)
    core = list(ink_colors) if ink_colors else (pair_ranking[0]["colors"] if pool else [])
    splashes = _choose_splashes(pool, set(core), deck_size)
    allowed = set(core) | set(splashes)

    candidates = [card for card, _ in pool if _color_subset_ok(card, allowed)]
    qty_by_name = {card.get("fullName", ""): qty for card, qty in pool}
    synergy_bonus, synergy_info = compute_shift_synergy(candidates)
    picks = allocate_deck(
        candidates,
        targets=curve_targets(deck_size),
        max_copies_fn=lambda c: qty_by_name.get(c.get("fullName", ""), 0),
        synergy_bonus=synergy_bonus,
        synergy_info=synergy_info,
        per_card_max=deck_size,
    )

    used = {card.get("fullName", ""): qty for card, qty in picks}
    sideboard = [
        (card, qty - used.get(card.get("fullName", ""), 0))
        for card, qty in pool
        if qty - used.get(card.get("fullName", ""), 0) > 0
    ]
    sideboard.sort(key=lambda cq: -score_card(cq[0]))

    return {
        "core": core,
        "splashes": splashes,
        "picks": picks,
        "sideboard": sideboard,
        "pair_ranking": pair_ranking,
        "total": sum(q for _, q in picks),
    }


def card_colors_label(card: dict) -> str:
    return "/".join(_card_colors(card)) or "—"
