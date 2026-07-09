"""Heuristic deck-list synthesis: assemble a legal, curve-balanced decklist
from the full LorcanaJSON card pool for a given ink pair, format, and
(optionally) collection/rotation constraints.

This is a curve/keyword-value heuristic, not a synergy engine — it does not
detect multi-card combos (see the project CLAUDE.md's "Key combos and
synergies" section). See `build_deck` in server.py for the tool that wires
this up and surfaces that caveat to the user.
"""
from __future__ import annotations

from typing import Callable

from .api import _card_colors, dedupe_by_full_name, filter_by_format, is_song, singer_value

# ── Candidate pool ───────────────────────────────────────────────────────────


def rotation_safe_set_codes(sets_meta: dict) -> set[str]:
    """Set codes (LorcanaJSON setCode strings) in the newest currently-
    Core-legal rotation group.

    At any given time ~2 rotation groups are Core-legal (the current one and
    the incoming one); rotation always drops the *older* of the two, so the
    numerically highest rotationGroup among allowed=True Core sets is always
    the one that survives the next rotation event. This generalizes the
    project CLAUDE.md's "restrict to rotationGroup >= 3" guidance correctly
    for any future rotation state — it only reads as ">=3" today because
    there's currently no group above 3. This assumes the "exactly ~2 legal
    groups, older always drops next" mechanic CLAUDE.md describes continues
    to hold; it isn't a guarantee enforced by the JSON schema itself.
    """
    groups: dict[int, set[str]] = {}
    for code, s in sets_meta.items():
        core = (s.get("allowedInFormats") or {}).get("Core") or {}
        if not core.get("allowed"):
            continue
        rg = core.get("rotationGroup")
        if rg is None:
            continue
        groups.setdefault(rg, set()).add(str(code))
    if not groups:
        return set()
    return groups[max(groups)]


def _color_subset_ok(card: dict, allowed: set[str]) -> bool:
    """A card is eligible for a deck of `allowed` colors only if every color
    on the card is within that set — a Ruby/Emerald dual-ink card must NOT
    be admitted into a Ruby/Amber pool. Deliberately not filter_cards()'s
    ANY-match semantics, which are correct for search but wrong here."""
    card_colors = {c.lower() for c in _card_colors(card)}
    return bool(card_colors) and card_colors <= allowed


def build_candidate_pool(
    lj_cards: list[dict],
    ink_colors: list[str],
    fmt: str,
    duels_lookup: dict | None = None,
    rotation_safe_codes: set[str] | None = None,
    owned_counts: dict[str, int] | None = None,
) -> list[dict]:
    """Assemble the legal candidate pool for deck building: dedupe alt-art
    duplicates, restrict to cards whose full color set fits within
    `ink_colors`, restrict to format-legal cards, optionally restrict to a
    rotation-safe set-code allowlist, and optionally (collection mode) drop
    any card owned zero copies. Per-card copy caps are applied later, during
    allocation — this only decides inclusion."""
    allowed = {c.strip().lower() for c in ink_colors}
    pool = dedupe_by_full_name(lj_cards)
    pool = [c for c in pool if _color_subset_ok(c, allowed)]
    pool = filter_by_format(pool, fmt, duels_lookup)
    if rotation_safe_codes is not None:
        pool = [c for c in pool if str(c.get("setCode")) in rotation_safe_codes]
    if owned_counts is not None:
        pool = [c for c in pool if owned_counts.get((c.get("fullName") or "").lower(), 0) > 0]
    return pool


# ── Scoring ──────────────────────────────────────────────────────────────────

# Ward and Evasive are the two strongest keywords per the project CLAUDE.md's
# own keyword glossary ("Considered the strongest defensive keyword" /
# "Core lore engine ... nearly untouchable"); everything else with real but
# smaller value gets a flat mid-tier bonus. Reckless is a real drawback
# (forced to challenge, can't quest) so it scores negative.
_KEYWORD_SCORE: dict[str, float] = {
    "ward": 3.0, "evasive": 3.0,
    "rush": 1.5, "bodyguard": 1.5, "resist": 1.5,
    "challenger": 1.5, "support": 1.5, "singer": 1.5, "shift": 1.5,
    "vanish": 1.0, "alert": 1.0,
    "reckless": -0.5,
}

# Rough ability-text value signals for non-character cards, since there's no
# structured "this is removal/draw" field to key off of.
_ACTION_VALUE_PATTERNS: list[tuple[str, float]] = [
    ("banish", 3.0), ("draw a card", 2.0), ("deal", 1.5),
    ("return", 1.0), ("draw", 1.0), ("look at", 0.5),
]


def _keywords_of(card: dict) -> list[str]:
    return [ab.get("keyword", "") for ab in card.get("abilities", []) if ab.get("type") == "keyword"]


def _text_value(card: dict) -> float:
    text = (card.get("fullText") or "").lower()
    return sum(weight for pattern, weight in _ACTION_VALUE_PATTERNS if pattern in text)


def character_score(card: dict) -> float:
    cost = card.get("cost") or 0
    strength = card.get("strength") or 0
    willpower = card.get("willpower") or 0
    lore = card.get("lore") or 0
    # Lore is weighted higher — it's the actual win condition.
    stat_total = strength + willpower + lore * 2
    efficiency = stat_total / max(cost, 1)
    keyword_bonus = sum(_KEYWORD_SCORE.get(k.lower(), 0.0) for k in _keywords_of(card))
    sv = singer_value(card)
    singer_bonus = 0.3 * sv if sv else 0.0
    return efficiency + keyword_bonus + singer_bonus


def action_score(card: dict) -> float:
    cost = card.get("cost") or 0
    value = _text_value(card)
    song_bonus = 0.5 if is_song(card) else 0.0
    return value / max(cost, 1) + song_bonus


def item_location_score(card: dict) -> float:
    cost = card.get("cost") or 0
    value = _text_value(card) * 0.5
    keyword_bonus = sum(_KEYWORD_SCORE.get(k.lower(), 0.0) for k in _keywords_of(card)) * 0.5
    lore = card.get("lore") or 0  # Locations carry a lore value
    return (value + keyword_bonus + lore * 1.5) / max(cost, 1) + 0.25


def score_card(card: dict) -> float:
    ctype = card.get("type")
    if ctype == "Character":
        return character_score(card)
    if ctype == "Action":
        return action_score(card)
    if ctype in ("Item", "Location"):
        return item_location_score(card)
    return 0.0


# ── Curve targets + allocation ───────────────────────────────────────────────

# Midpoints of the project CLAUDE.md's ink-curve guideline ranges
# (1-2: 8-12, 3-4: 12-16, 5-6: 8-12, 7+: 2-6) — scaled proportionally to
# whatever total is requested, via largest-remainder apportionment so the
# buckets always sum exactly to that total.
_CURVE_MIDPOINTS: dict[str, int] = {"1-2": 10, "3-4": 14, "5-6": 10, "7+": 4}

# Upper end of CLAUDE.md's composition guideline (Characters 20-24, Actions/
# Songs 10-16, Items 4-8, Locations 2-4) — soft caps during allocation.
_TYPE_CAPS: dict[str, int] = {"Character": 24, "Action": 16, "Item": 8, "Location": 4}


def curve_targets(total: int = 60) -> dict[str, int]:
    """Cost-bucket targets that sum exactly to `total`, preserving the
    bell-curve shape (peaked at 3-4 cost) from CLAUDE.md's guideline."""
    base_sum = sum(_CURVE_MIDPOINTS.values())
    raw = {bucket: value * total / base_sum for bucket, value in _CURVE_MIDPOINTS.items()}
    floored = {bucket: int(value) for bucket, value in raw.items()}
    remainder = total - sum(floored.values())
    order = sorted(raw, key=lambda bucket: raw[bucket] - floored[bucket], reverse=True)
    for bucket in order[:remainder]:
        floored[bucket] += 1
    return floored


def _cost_bracket(cost: int) -> str:
    """Mirrors deck.py's _cost_bracket boundaries (1-2 / 3-4 / 5-6 / 7+).
    Duplicated rather than imported to keep deckbuilder.py's only dependency
    on api.py, parallel to deck.py's own dependency shape."""
    if cost <= 2:
        return "1-2"
    if cost <= 4:
        return "3-4"
    if cost <= 6:
        return "5-6"
    return "7+"


def allocate_deck(
    pool: list[dict],
    targets: dict[str, int] | None = None,
    max_copies_fn: Callable[[dict], int] | None = None,
) -> list[tuple[dict, int]]:
    """Greedily fill each cost bucket toward its target with the highest-
    scoring cards, respecting `max_copies_fn` (default: always up to 4) and
    soft type caps. A backfill pass (ignoring bucket targets, still
    respecting copy/type caps) tries to reach `total` from whatever pool
    remains, so a shortfall reflects a genuine ceiling on the pool — never
    padding with irrelevant fillers to fake a full 60.
    """
    if targets is None:
        targets = curve_targets()
    targets = dict(targets)
    total = sum(targets.values())
    max_copies_fn = max_copies_fn or (lambda c: 4)

    ranked = sorted(pool, key=lambda c: (-score_card(c), c.get("fullName", "")))

    by_bucket: dict[str, list[dict]] = {"1-2": [], "3-4": [], "5-6": [], "7+": []}
    for card in ranked:
        cost = card.get("cost")
        if isinstance(cost, int):
            by_bucket[_cost_bracket(cost)].append(card)

    picks: list[tuple[dict, int]] = []
    used_names: set[str] = set()
    type_counts: dict[str, int] = {}
    grand_total = 0

    def try_take(card: dict, want: int, enforce_type_cap: bool) -> int:
        nonlocal grand_total
        name = card.get("fullName", "")
        if not name or name in used_names or want <= 0:
            return 0
        cap = min(want, max(0, max_copies_fn(card)))
        if cap <= 0:
            return 0
        ctype = card.get("type")
        if enforce_type_cap:
            type_cap = _TYPE_CAPS.get(ctype)
            if type_cap is not None:
                cap = min(cap, max(0, type_cap - type_counts.get(ctype, 0)))
            if cap <= 0:
                return 0
        picks.append((card, cap))
        used_names.add(name)
        type_counts[ctype] = type_counts.get(ctype, 0) + cap
        grand_total += cap
        return cap

    # Primary pass: fill each cost bucket toward its target, respecting the
    # soft type-composition caps (Character/Action/Item/Location).
    for bucket, cards in by_bucket.items():
        need = targets.get(bucket, 0)
        for card in cards:
            if need <= 0:
                break
            need -= try_take(card, min(4, need), enforce_type_cap=True)

    # Backfill pass: whatever's left in the pool, ignoring bucket targets
    # AND the type caps (which sum to less than a full deck by design — see
    # CLAUDE.md's composition guideline ranges) — only copy caps still
    # apply. This is what makes a single-type-heavy pool (e.g. very few
    # legal Actions/Items for a color pair) still reach a full deck instead
    # of stalling at the type-cap sum; the caps above only *shape* the
    # build toward good composition when the pool is diverse enough to
    # allow it, they never block reaching the real target.
    if grand_total < total:
        for card in ranked:
            if grand_total >= total:
                break
            try_take(card, min(4, total - grand_total), enforce_type_cap=False)

    return picks


def summarize_picks(picks: list[tuple[dict, int]]) -> dict:
    """Curve/inkable/color/type/lore stats computed directly from already-
    resolved (card, qty) picks. Deliberately NOT deck.analyze_deck() on a
    formatted text decklist: analyze_deck re-resolves each line by fuzzy
    name matching against the full card pool (a real, unnecessary network +
    O(pool size) fuzzy-match cost per card) when we already hold the exact
    resolved card dicts here."""
    curve = {"1-2": 0, "3-4": 0, "5-6": 0, "7+": 0}
    inkable_count = 0
    uninkable_count = 0
    lore_per_turn = 0
    color_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}

    for card, qty in picks:
        cost = card.get("cost")
        if isinstance(cost, int):
            curve[_cost_bracket(cost)] += qty

        if card.get("inkwell"):
            inkable_count += qty
        else:
            uninkable_count += qty

        colors = _card_colors(card)
        color_key = "/".join(colors) if colors else "Unknown"
        color_counts[color_key] = color_counts.get(color_key, 0) + qty

        ctype = card.get("type", "—")
        if ctype == "Action" and "Song" in (card.get("subtypes") or []):
            ctype = "Action - Song"
        type_counts[ctype] = type_counts.get(ctype, 0) + qty

        lore = card.get("lore")
        if card.get("type") == "Character" and isinstance(lore, int):
            lore_per_turn += lore * qty

    return {
        "curve": curve,
        "inkable_count": inkable_count,
        "uninkable_count": uninkable_count,
        "color_counts": color_counts,
        "type_counts": type_counts,
        "lore_per_turn": lore_per_turn,
    }
