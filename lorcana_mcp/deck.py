"""Deck list parsing and analysis: curve, color split, legality, lore estimate."""
from __future__ import annotations

import re

from .api import search_card, _card_colors

_LINE_RE = re.compile(r"^(\d+)\s*[xX]?\s+(.+?)\s*$")
_COST_BRACKETS = [(1, 2, "1-2"), (3, 4, "3-4"), (5, 6, "5-6"), (7, None, "7+")]


def parse_deck_list(text: str) -> list[tuple[int, str]]:
    """Parse a raw deck list into (quantity, card_name) pairs.

    Accepts "4x Card Name", "4 Card Name", and "Card Name" (implicit qty 1).
    Blank lines and lines starting with "#" or "//" are skipped.
    """
    entries: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        m = _LINE_RE.match(line)
        if m:
            entries.append((int(m.group(1)), m.group(2).strip()))
        else:
            entries.append((1, line))
    return entries


def _cost_bracket(cost: int) -> str:
    for lo, hi, label in _COST_BRACKETS:
        if hi is None:
            if cost >= lo:
                return label
        elif lo <= cost <= hi:
            return label
    return "7+"


def _card_type_display(card: dict) -> str:
    ctype = card.get("type", "")
    if ctype == "Action" and "Song" in (card.get("subtypes") or []):
        return "Action - Song"
    return ctype


def combine_deck_lines(parsed: list[tuple[int, str]]) -> tuple[dict[str, int], dict[str, str]]:
    """Combine duplicate deck-list lines (case-insensitive) into total quantities.

    Returns (qty_by_key, display_name_by_key), keyed by lowercased card name.
    Dict insertion order is preserved, so callers can iterate in original
    deck-list order.
    """
    combined: dict[str, int] = {}
    name_by_key: dict[str, str] = {}
    for qty, name in parsed:
        key = name.strip().lower()
        if key not in combined:
            combined[key] = 0
            name_by_key[key] = name.strip()
        combined[key] += qty
    return combined, name_by_key


def analyze_deck(deck_text: str) -> dict:
    """
    Analyze a raw deck list and return curve, composition, and legality stats.

    Returns a dict with keys: total_cards, unique_cards, curve (dict bracket->qty),
    inkable_count, uninkable_count, color_counts (dict color->qty),
    type_counts (dict type->qty), lore_per_turn, legality (dict of checks),
    unresolved (list of {name, qty}), entries (list of resolved card rows).
    """
    combined, name_by_key = combine_deck_lines(parse_deck_list(deck_text))

    total_cards = sum(combined.values())
    unique_cards = len(combined)

    curve: dict[str, int] = {"1-2": 0, "3-4": 0, "5-6": 0, "7+": 0}
    inkable_count = 0
    uninkable_count = 0
    color_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    lore_per_turn = 0
    over_limit: list[tuple[str, int]] = []
    unresolved: list[dict] = []
    entries: list[dict] = []
    all_colors: set[str] = set()

    for key, qty in combined.items():
        raw_name = name_by_key[key]

        if qty > 4:
            over_limit.append((raw_name, qty))

        card = search_card(raw_name)
        if not card:
            unresolved.append({"name": raw_name, "qty": qty})
            continue

        cost = card.get("cost")
        inkwell = bool(card.get("inkwell"))
        ctype = _card_type_display(card)
        colors = _card_colors(card)
        lore = card.get("lore")

        if isinstance(cost, int):
            curve[_cost_bracket(cost)] += qty
        if inkwell:
            inkable_count += qty
        else:
            uninkable_count += qty

        color_key = "/".join(colors) if colors else "Unknown"
        color_counts[color_key] = color_counts.get(color_key, 0) + qty
        all_colors.update(colors)

        type_counts[ctype] = type_counts.get(ctype, 0) + qty

        if card.get("type") == "Character" and isinstance(lore, int):
            lore_per_turn += lore * qty

        entries.append({
            "name": card.get("fullName", raw_name),
            "qty": qty,
            "cost": cost,
            "type": ctype,
            "inkwell": inkwell,
            "colors": colors,
        })

    legality = {
        "min_60_cards": total_cards >= 60,
        "max_4_copies": not over_limit,
        "over_limit_cards": over_limit,
        "two_ink_colors_or_fewer": len(all_colors) <= 2,
        "ink_colors_used": sorted(all_colors),
    }

    return {
        "total_cards": total_cards,
        "unique_cards": unique_cards,
        "curve": curve,
        "inkable_count": inkable_count,
        "uninkable_count": uninkable_count,
        "color_counts": color_counts,
        "type_counts": type_counts,
        "lore_per_turn": lore_per_turn,
        "legality": legality,
        "unresolved": unresolved,
        "entries": entries,
    }


def what_am_i_missing(deck_text: str, owned_counts: dict[str, int]) -> dict:
    """
    Compare a deck list against owned card quantities.

    owned_counts maps a lowercased card fullName to total copies owned (see
    server._load_owned_counts, which strips promo-suffix parentheticals before
    lowercasing). Pricing isn't computed here — this stays network-free so
    it's easily testable; the caller cross-references missing entries against
    live prices.

    Returns a dict with keys: entries (list of {name, needed, owned, missing}),
    unresolved (list of {name, qty}).
    """
    combined, name_by_key = combine_deck_lines(parse_deck_list(deck_text))

    entries: list[dict] = []
    unresolved: list[dict] = []

    for key, needed in combined.items():
        raw_name = name_by_key[key]
        card = search_card(raw_name)
        if not card:
            unresolved.append({"name": raw_name, "qty": needed})
            continue

        full_name = card.get("fullName", raw_name)
        owned = owned_counts.get(full_name.lower(), 0)

        entries.append({
            "name": full_name,
            "needed": needed,
            "owned": owned,
            "missing": max(needed - owned, 0),
        })

    return {"entries": entries, "unresolved": unresolved}
