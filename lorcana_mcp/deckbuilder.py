"""Heuristic deck-list synthesis: assemble a legal, curve-balanced decklist
from the full LorcanaJSON card pool for a given ink pair, format, and
(optionally) collection/rotation constraints.

This is a curve/keyword-value heuristic, not a general synergy engine — it
does not detect multi-card combos like the Merlin/Mim Bounce Loop or the
Steelsong package (see the project CLAUDE.md's "Key combos and synergies"
section). It does have one scoped piece of synergy awareness: Shift-family
keywords (Shift, Duo Shift, Combo Shift, Potato Shift, ...) whose target is
a specific named character/item get a bonus applied to matching enablers
already in the candidate pool, so a Shift payoff and its base(s) are more
likely to be built together instead of the payoff losing out to unrelated
filler on raw score alone (see `compute_shift_synergy`). Floodborn/Madrigal/
Puppy/Red Panda Shift (subtype-targeted, not name-targeted) and Universal
Shift (no target) are out of scope for this — see `_shift_target_names`.

The other piece of scoped synergy awareness is Format Coconut (see
`compute_coconut_synergy`): a hand-curated per-Coconut tag table, since with
only 18 beta cards there's no general pattern to derive this from the way
Shift-family keywords share one.

See `build_deck` in server.py for the tool that wires this up and surfaces
these caveats to the user.
"""
from __future__ import annotations

import re
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


def _keyword_score(keyword: str) -> float:
    """Score a single keyword, falling back to a substring match on "shift"
    for named Shift variants that don't have their own dict entry. Set 13
    alone introduced Combo Shift, Duo Shift, Potato Shift, Madrigal Shift,
    Floodborn Shift, Temporary Shift, and Temporary Red Panda Shift, on top
    of the 311 plain "Shift" cards already in the pool across all sets —
    every variant is mechanically the same discounted-alternate-cost shape
    as plain Shift, so they should score the same rather than the 0.0 an
    exact-match lookup gives anything not spelled exactly "shift". This
    also future-proofs against whatever new variant name a later set
    introduces, without needing a new dict entry each time."""
    key = keyword.lower()
    if key in _KEYWORD_SCORE:
        return _KEYWORD_SCORE[key]
    if "shift" in key:
        return _KEYWORD_SCORE["shift"]
    return 0.0


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
    keyword_bonus = sum(_keyword_score(k) for k in _keywords_of(card))
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
    keyword_bonus = sum(_keyword_score(k) for k in _keywords_of(card)) * 0.5
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


# ── Shift-family synergy ────────────────────────────────────────────────────

# Subtype-targeted Shift variants (no specific name to match against — the
# target is "one of your <Subtype> characters") and Universal Shift (no
# target restriction at all) are out of scope for name-based matching.
_SUBTYPE_OR_UNTARGETED_SHIFT_KEYWORDS = {
    "floodborn shift", "madrigal shift", "puppy shift",
    "temporary red panda shift", "universal shift",
}

# Same tier as Ward/Evasive (see _KEYWORD_SCORE) — meaningful but not so
# large it forces in an otherwise-weak enabler on its own.
_SHIFT_SYNERGY_BONUS = 2.0

_ITEM_NAMED_RE = re.compile(r"\bitems?\s+named\s+([A-Z][\w'.\- ]*?)(?:[.,]|$)")


def _shift_target_names(card: dict) -> tuple[str, str, list[str]] | None:
    """For a Shift-family character with a *named* target, return
    (target_type, relation, [required base names]):

    - target_type is "Item" for Potato Shift, else "Character".
    - relation is "all" (every name must have a match — Duo Shift, the only
      true AND case) or "any" (at least one match suffices — plain Shift's
      compound "X or Y" cards, Combo Shift's "one named X, one named Y, or
      one of each" — the "or one of each" phrasing means either alone is
      already sufficient).

    Plain, Duo, and Combo Shift never need their reminder text parsed: a
    solo-named card ("Robin Hood - Champion of Sherwood") always shifts onto
    that same name, and a compound name joined by " & " or " 'n' " (e.g.
    "Mickey Mouse & Minnie Mouse - Adventuring Duo",
    "Chip 'n' Dale - Recovery Rangers") always shifts onto its components
    individually — LorcanaJSON's own `name` field already gives this with
    no ambiguity, which sidesteps punctuation edge cases a text regex would
    trip on (e.g. "Dr. Facilier", "Fix-It Felix, Jr."). Verified against
    every Shift/Duo Shift/Combo Shift card in the live card pool (2026-08)
    with zero exceptions. Potato Shift is the one case that does need its
    target parsed from reminder text, since the item name isn't reflected
    in the shifting character's own name at all.

    Returns None if the card has no name-targeted Shift-family keyword.
    """
    ability = None
    keyword = ""
    for ab in card.get("abilities", []):
        kw = (ab.get("keyword") or "")
        kw_lower = kw.lower()
        if ab.get("type") == "keyword" and "shift" in kw_lower:
            if kw_lower in _SUBTYPE_OR_UNTARGETED_SHIFT_KEYWORDS:
                return None
            ability = ab
            keyword = kw_lower
            break
    if ability is None:
        return None

    if keyword == "potato shift":
        text = ability.get("reminderText") or ability.get("fullText") or ""
        m = _ITEM_NAMED_RE.search(text)
        return ("Item", "any", [m.group(1).strip()]) if m else None

    name = (card.get("name") or "").strip()
    if not name:
        return None
    for sep in (" & ", " 'n' "):
        if sep in name:
            parts = [p.strip() for p in name.split(sep) if p.strip()]
            relation = "all" if keyword == "duo shift" else "any"
            return ("Character", relation, parts) if parts else None
    return ("Character", "any", [name])


def compute_shift_synergy(pool: list[dict]) -> tuple[dict[str, float], list[dict]]:
    """Find every name-targeted Shift-family card in `pool` whose target(s)
    are actually satisfiable from cards also in `pool`, and award a bonus to
    both the payoff and its matching enabler(s) — mirrors the project
    CLAUDE.md's own Shift-strategy guidance ("Include 3-4 copies of the
    cheap base version AND 3-4 copies of the shifted version") instead of
    letting the payoff compete purely on its own raw stats against unrelated
    filler. No bonus is awarded for an unreachable combo (a required name
    with zero pool matches) — that would just reward a dead card.

    Returns (bonus_by_full_name, synergy_info) — synergy_info is a list of
    dicts describing each detected, satisfiable synergy, for surfacing to
    the user in the tool's output.
    """
    by_char_name: dict[str, list[dict]] = {}
    by_item_full_name: dict[str, list[dict]] = {}
    for c in pool:
        n = (c.get("name") or "").strip().lower()
        if n:
            by_char_name.setdefault(n, []).append(c)
        if c.get("type") == "Item":
            fn = (c.get("fullName") or "").strip().lower()
            if fn:
                by_item_full_name.setdefault(fn, []).append(c)

    bonus: dict[str, float] = {}
    synergy_info: list[dict] = []

    for card in pool:
        target = _shift_target_names(card)
        if target is None:
            continue
        target_type, relation, names = target
        index = by_item_full_name if target_type == "Item" else by_char_name
        payoff_full_name = card.get("fullName") or ""

        matches: dict[str, list[dict]] = {}
        for req in names:
            found = [
                e for e in index.get(req.lower(), [])
                if e.get("fullName") != payoff_full_name
            ]
            if found:
                matches[req] = found

        satisfiable = len(matches) == len(names) if relation == "all" else bool(matches)
        if not satisfiable:
            continue

        if payoff_full_name:
            bonus[payoff_full_name] = max(bonus.get(payoff_full_name, 0.0), _SHIFT_SYNERGY_BONUS)

        enabler_names: set[str] = set()
        for found in matches.values():
            for enabler in found:
                key = enabler.get("fullName") or ""
                if key:
                    bonus[key] = max(bonus.get(key, 0.0), _SHIFT_SYNERGY_BONUS)
                    enabler_names.add(key)

        synergy_info.append({
            "payoff": payoff_full_name,
            "target_type": target_type,
            "relation": relation,
            "required_names": names,
            "enablers_found": sorted(enabler_names),
        })

    return bonus, synergy_info


# ── Format Coconut synergy (beta, see api.fetch_format_coconut_cards) ──────────

# One hand-curated synergy hint per Coconut card, keyed by the Coconut's own
# `name` field (lowercased) — mirrors this project's CLAUDE.md "Format
# Coconut" section, which documents the same 18 cards with the same intent.
# Only 18 cards exist, each with a genuinely different payoff shape (subtype
# tribal, keyword-matters, cost-band, named-character chain, ...), so unlike
# Shift-family synergy above this isn't derivable from the card data itself
# — it has to be told what each Coconut's ability actually rewards. A tag is
# (kind, value); a card matching ANY of a Coconut's tags gets the bonus.
_COCONUT_SYNERGY_TAGS: dict[str, list[tuple[str, str]]] = {
    "scar":            [("subtype", "Ally")],
    "ariel":           [("subtype", "Princess"), ("type", "Song")],
    "winnie the pooh": [("no_ability", "")],
    "stitch":          [("cost_le", "2")],
    "ursula":          [("type", "Song")],
    "mickey mouse":    [("name_contains", "mickey mouse")],
    "mufasa":          [("cost_ge", "6")],
    "nick wilde":      [("type", "Item")],
    "snow white":      [("subtype", "Seven Dwarfs"), ("name_contains", "snow white")],
    "donald duck":     [("keyword", "Boost")],
    "mr. incredible":  [("subtype", "Super")],
    "moana":           [("name_contains", "moana"), ("name_contains", "heihei"), ("name_contains", "pua")],
    "john silver":     [("type", "Location")],
    "robin hood":      [("name_contains", "robin hood"), ("text_contains", "deal")],
    "tinker bell":     [("text_contains", "deal")],
    "sisu":            [("keyword", "Ward"), ("keyword", "Resist")],
    "pocahontas":      [("text_contains", "lore")],
    "dumbo":           [("text_contains", "⟳"), ("text_contains", "exert")],
}

# Same tier as the Shift synergy bonus above — meaningful nudge, not a
# guaranteed inclusion on its own.
_COCONUT_SYNERGY_BONUS = 2.0

# Higher than the archetype-tag bonus: the Coconut's own associated
# character (the one card allowed up to 4 copies instead of 1) should
# clearly outrank ordinary same-tag filler, the same way a Shift payoff
# outranks unrelated cards once its enabler is confirmed satisfiable.
_COCONUT_ASSOCIATED_BONUS = 4.0


def _matches_coconut_tag(card: dict, kind: str, value: str) -> bool:
    if kind == "subtype":
        return value.lower() in [s.lower() for s in (card.get("subtypes") or [])]
    if kind == "keyword":
        return value.lower() in [k.lower() for k in _keywords_of(card)]
    if kind == "type":
        return is_song(card) if value == "Song" else card.get("type") == value
    if kind == "name_contains":
        return value.lower() in (card.get("name") or "").lower()
    if kind == "text_contains":
        return value.lower() in (card.get("fullText") or "").lower()
    if kind == "no_ability":
        return not card.get("abilities")
    if kind == "cost_le":
        cost = card.get("cost")
        return isinstance(cost, int) and cost <= int(value)
    if kind == "cost_ge":
        cost = card.get("cost")
        return isinstance(cost, int) and cost >= int(value)
    return False


def compute_coconut_synergy(pool: list[dict], coconut: dict) -> dict[str, float]:
    """Score a flat bonus (by fullName) for every pool card relevant to the
    chosen Coconut: its own associated character (see
    `_COCONUT_ASSOCIATED_BONUS` — the one card the format lets a deck run up
    to 4 copies of) always wins the higher bonus so it isn't crowded out by
    same-tag filler the way it otherwise could be on raw stats alone, and
    every other pool card matching one of the Coconut's synergy tags (see
    `_COCONUT_SYNERGY_TAGS`) gets the lower one. A Coconut name missing from
    the hand-curated tag table still gets its associated-character bonus —
    only the tag-based half is skipped — so callers still get a sensibly
    headlined, if untargeted, build.
    """
    coconut_name = (coconut.get("name") or "").strip().lower()
    associated_full_name = coconut.get("associatedCardName", "")
    tags = _COCONUT_SYNERGY_TAGS.get(coconut_name, [])
    bonus: dict[str, float] = {}
    for card in pool:
        fn = card.get("fullName", "")
        if not fn:
            continue
        if fn == associated_full_name:
            bonus[fn] = _COCONUT_ASSOCIATED_BONUS
        elif tags and any(_matches_coconut_tag(card, kind, value) for kind, value in tags):
            bonus[fn] = _COCONUT_SYNERGY_BONUS
    return bonus


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
    synergy_bonus: dict[str, float] | None = None,
    synergy_info: list[dict] | None = None,
) -> list[tuple[dict, int]]:
    """Greedily fill each cost bucket toward its target with the highest-
    scoring cards, respecting `max_copies_fn` (default: always up to 4) and
    soft type caps. A backfill pass (ignoring bucket targets, still
    respecting copy/type caps) tries to reach `total` from whatever pool
    remains, so a shortfall reflects a genuine ceiling on the pool — never
    padding with irrelevant fillers to fake a full 60.

    `synergy_bonus` (from `compute_shift_synergy`, keyed by fullName) is
    added directly into the ranking score. This matters in two ways: it
    raises a boosted enabler's rank *within its own cost bucket*, so it's
    more likely to be claimed before the cross-bucket Character type cap
    runs out during the primary (bucket-order) pass; and since a
    Character-heavy pool often exhausts that same type cap before the
    (processed-last) 7+ bucket gets a turn, a boosted payoff's much higher
    effective score makes it far more likely to be picked up by the
    backfill pass instead, which ignores the type cap entirely.

    `synergy_info` (from `compute_shift_synergy`) is used for a final
    guarantee pass over "all"-relation synergies (Duo Shift) only — see
    `_enforce_all_relation_synergies` for why the bonus alone isn't
    sufficient there.
    """
    if targets is None:
        targets = curve_targets()
    targets = dict(targets)
    total = sum(targets.values())
    max_copies_fn = max_copies_fn or (lambda c: 4)
    synergy_bonus = synergy_bonus or {}

    def _ranked_score(c: dict) -> float:
        return score_card(c) + synergy_bonus.get(c.get("fullName", ""), 0.0)

    ranked = sorted(pool, key=lambda c: (-_ranked_score(c), c.get("fullName", "")))

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

    if synergy_info:
        picks = _enforce_all_relation_synergies(picks, ranked, max_copies_fn, synergy_info)

    return picks


def _enforce_all_relation_synergies(
    picks: list[tuple[dict, int]],
    ranked: list[dict],
    max_copies_fn: Callable[[dict], int],
    synergy_info: list[dict],
) -> list[tuple[dict, int]]:
    """A flat scoring bonus is enough for "any"-relation synergies (Combo
    Shift, compound-name Shift) — landing just one side already makes the
    combo work. It is NOT reliably enough for "all"-relation synergies
    (currently just Duo Shift): in a strong, deep pool, one required name's
    enablers can clear the bar on score alone while the other still loses
    out to unrelated cards, leaving a picked Duo Shift payoff that can
    never actually be played for its intended 0-cost Shift since one whole
    side of the requirement is simply missing from the 60. This closes that
    gap directly: for every landed "all"-relation payoff, guarantee at
    least 1 copy of an enabler for every required name, trimming a copy
    from the current globally-weakest pick to hold the total constant.

    A trimmed pick could, in rare cases, itself be the sole enabler of a
    different landed synergy — accepted as a known edge case rather than
    tracked explicitly, since only 1 copy is ever removed (not all of a
    4-of), so it would take an unlucky exact-single-copy overlap to matter.
    """
    picks_map: dict[str, list] = {}
    order: list[str] = []
    for card, qty in picks:
        fn = card.get("fullName", "")
        if fn not in picks_map:
            order.append(fn)
        picks_map[fn] = [card, qty]

    for s in synergy_info:
        if s["relation"] != "all" or s["payoff"] not in picks_map:
            continue
        have_names = {(picks_map[fn][0].get("name") or "").strip() for fn in order}
        for req in s["required_names"]:
            if req in have_names:
                continue
            candidate = next(
                (c for c in ranked
                 if (c.get("name") or "").strip() == req
                 and c.get("fullName") not in picks_map
                 and max_copies_fn(c) > 0),
                None,
            )
            if candidate is None:
                continue
            weakest_fn = min(
                (fn for fn in order if fn != s["payoff"] and picks_map[fn][1] > 0),
                key=lambda fn: score_card(picks_map[fn][0]),
                default=None,
            )
            if weakest_fn is None:
                continue
            picks_map[weakest_fn][1] -= 1
            if picks_map[weakest_fn][1] <= 0:
                order.remove(weakest_fn)
                del picks_map[weakest_fn]
            cand_fn = candidate.get("fullName", "")
            picks_map[cand_fn] = [candidate, 1]
            order.append(cand_fn)
            have_names.add(req)

    return [(picks_map[fn][0], picks_map[fn][1]) for fn in order if picks_map[fn][1] > 0]


def ensure_coconut_associated_card(
    picks: list[tuple[dict, int]],
    pool: list[dict],
    associated_full_name: str,
    max_copies_fn: Callable[[dict], int],
) -> list[tuple[dict, int]]:
    """Guarantee the Coconut's associated character lands in the final build
    with as many copies as `max_copies_fn` allows (normally 4).

    A scoring bonus alone (see `compute_coconut_synergy`'s
    `_COCONUT_ASSOCIATED_BONUS`) isn't reliably enough: an expensive
    associated character competes in `allocate_deck`'s backfill pass on raw
    global score, which structurally favors cheap, efficient cards — the
    same gap `_enforce_all_relation_synergies` closes for Duo Shift above.
    This mirrors that approach: if the associated card is missing, trim
    copies from the current globally-weakest pick(s) to make room rather
    than pushing the deck past its target size. No-ops if the card is
    already present, isn't in the legal pool at all (e.g. its ink isn't
    part of this build), or `max_copies_fn` caps it at 0 (e.g.
    mode="collection" and zero copies owned).
    """
    if not associated_full_name:
        return picks

    picks_map: dict[str, list] = {}
    order: list[str] = []
    for card, qty in picks:
        fn = card.get("fullName", "")
        if fn not in picks_map:
            order.append(fn)
        picks_map[fn] = [card, qty]

    if associated_full_name in picks_map:
        return picks

    candidate = next((c for c in pool if c.get("fullName") == associated_full_name), None)
    if candidate is None:
        return picks

    want = max(0, max_copies_fn(candidate))
    if want <= 0:
        return picks

    remaining = want
    while remaining > 0:
        weakest_fn = min(
            (fn for fn in order if picks_map[fn][1] > 0),
            key=lambda fn: score_card(picks_map[fn][0]),
            default=None,
        )
        if weakest_fn is None:
            break
        trim = min(remaining, picks_map[weakest_fn][1])
        picks_map[weakest_fn][1] -= trim
        if picks_map[weakest_fn][1] <= 0:
            order.remove(weakest_fn)
            del picks_map[weakest_fn]
        remaining -= trim

    added_qty = want - remaining
    if added_qty > 0:
        picks_map[associated_full_name] = [candidate, added_qty]
        order.append(associated_full_name)

    return [(picks_map[fn][0], picks_map[fn][1]) for fn in order if picks_map[fn][1] > 0]


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
