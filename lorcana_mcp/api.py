"""Card data fetching from lorcana-api.com and LorcanaJSON, plus enrichment helpers."""
from __future__ import annotations

import json
import re
import urllib.request

from . import cache as _cache

# ── Constants ──────────────────────────────────────────────────────────────────

ENRICH_FIELDS = [
    "Ink", "Ink Cost", "Card Type", "Subtypes", "Strength",
    "Willpower", "Lore Points", "Inkable", "Keywords", "Abilities",
]

OUT_COLS = [
    "Product ID", "TCGplayer Id", "Product Line", "Set Name", "Product Name",
    "Ink", "Ink Cost", "Card Type", "Subtypes", "Strength", "Willpower", "Lore Points",
    "Inkable", "Keywords", "Abilities",
    "Title", "Number", "Rarity", "Condition", "Printing",
    "TCG Market Price", "TCG Direct Low", "TCG Low Price With Shipping", "TCG Low Price",
    "Total Quantity", "Add to Quantity", "TCG Marketplace Price", "Photo URL",
]

SETNAME_TO_LJCODE: dict[str, str] = {
    "The First Chapter":        "1",
    "Rise of the Floodborn":    "2",
    "Into the Inklands":        "3",
    "Ursula's Return":          "4",
    "Shimmering Skies":         "5",
    "Azurite Sea":              "6",
    "Archazia's Island":        "7",
    "Reign of Jafar":           "8",
    "Fabled":                   "9",
    "Whispers in the Well":     "10",
    "Winterspell":              "11",
    "Wilds Unknown":            "12",
    "Attack of the Vine!":      "13",
    "Hyperia City":             "14",
}

LJCODE_TO_SETNAME: dict[str, str] = {v: k for k, v in SETNAME_TO_LJCODE.items()}

# Sets not yet available in lorcana-api.com — use LorcanaJSON only
LJ_ONLY_SETS = {"Wilds Unknown", "Attack of the Vine!", "Hyperia City"}

# Promo card name → LorcanaJSON setCode where the promo entry lives
PROMO_SETCODE: dict[str, str] = {
    "Lenny - Toy Binoculars":           "12",
    "Will o' the Wisp - Forest Spirit": "12",
    "Zipper - Tiny Helper":             "12",
    "Stitch - High Badness Level":      "11",
    "Tinker Bell - Giant Fairy":        "9",
    "Buzz Lightyear - Space Ranger":    "12",
    "Stitch - Carefree Snowboarder":    "1",
}

KEYWORD_PATTERNS = [
    (r"\bEvasive\b",             "Evasive"),
    (r"\bBodyguard\b",           "Bodyguard"),
    (r"\bRush\b",                "Rush"),
    (r"\bWard\b",                "Ward"),
    (r"\bSupport\b",             "Support"),
    (r"\bReckless\b",            "Reckless"),
    (r"\bVanish\b",              "Vanish"),
    (r"\bAlert\b",               "Alert"),
    (r"\bShift\s+(\d+)",         "Shift"),
    (r"\bChallenger\s+\+(\d+)", "Challenger"),
    (r"\bResist\s+\+(\d+)",      "Resist"),
    (r"\bSinger\s+(\d+)",        "Singer"),
]

# ── Keyword helpers ────────────────────────────────────────────────────────────

def extract_keywords_from_text(text: str) -> str:
    if not text:
        return ""
    found = []
    for pattern, name in KEYWORD_PATTERNS:
        m = re.search(pattern, text)
        if m:
            if m.lastindex:
                found.append(f"{name} +{m.group(1)}" if name in ("Challenger", "Resist") else f"{name} {m.group(1)}")
            else:
                found.append(name)
    return ", ".join(found)


def extract_keywords_from_lj_abilities(abilities: list) -> str:
    found = []
    for ab in abilities:
        if ab.get("type") == "keyword":
            kw = ab.get("keyword", "")
            ft = ab.get("fullText", "")
            m = re.search(r"\b" + re.escape(kw) + r"\s+(\+?\d+)", ft)
            if m:
                found.append(f"{kw} {m.group(1)}")
            else:
                found.append(kw)
    return ", ".join(found)


def abilities_from_text(text: str) -> str:
    return " | ".join(line for line in text.split("\n") if line.strip()) if text else ""


def abilities_from_lj(abilities: list) -> str:
    parts = []
    for ab in abilities:
        for line in ab.get("fullText", "").split("\n"):
            if line.strip():
                parts.append(line.strip())
    return " | ".join(parts)

# ── Card selection ─────────────────────────────────────────────────────────────

def pick_lj_card(candidates: list, product_name: str) -> dict | None:
    """Select the correct card when multiple LJ entries share a (setCode, number).

    allCards.json can list alternate-art variants at the same number as the base
    card. We pick by fullName match first, then by name prefix, then first entry.
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    name_lower = product_name.lower()
    for c in candidates:
        if c.get("fullName", "").lower() == name_lower:
            return c
    for c in candidates:
        if name_lower.startswith(c.get("name", "").lower()):
            return c
    return candidates[0]

# ── Enrichment converters ──────────────────────────────────────────────────────

def enrich_from_api(c: dict) -> tuple:
    body = c.get("Body_Text", "")
    return (
        c.get("Color", ""),
        str(c["Cost"]) if c.get("Cost", "") != "" else "",
        c.get("Type", ""),
        c.get("Classifications", ""),
        str(c["Strength"]) if c.get("Strength", "") != "" else "",
        str(c["Willpower"]) if c.get("Willpower", "") != "" else "",
        str(c["Lore"]) if c.get("Lore", "") != "" else "",
        "Yes" if c.get("Inkable") else "No",
        extract_keywords_from_text(body),
        abilities_from_text(body),
    )


def enrich_from_lj(c: dict) -> tuple:
    abs_list = c.get("abilities", [])
    return (
        c.get("color", ""),
        str(c["cost"]) if c.get("cost", "") != "" else "",
        c.get("type", ""),
        ", ".join(c.get("subtypes", [])),
        str(c["strength"]) if c.get("strength", "") != "" else "",
        str(c["willpower"]) if c.get("willpower", "") != "" else "",
        str(c["lore"]) if c.get("lore", "") != "" else "",
        "Yes" if c.get("inkwell") else "No",
        extract_keywords_from_lj_abilities(abs_list),
        abilities_from_lj(abs_list),
    )

# ── API fetch + lookup builders ────────────────────────────────────────────────

def _fetch(url: str) -> bytes:
    return urllib.request.urlopen(url, timeout=60).read()


def fetch_lorcana_api() -> list[dict]:
    """Fetch all cards from lorcana-api.com (cached 24h)."""
    cached = _cache.get("lorcana_api")
    if cached is not None:
        return cached
    cards = json.loads(_fetch("https://api.lorcana-api.com/cards/all"))
    _cache.set("lorcana_api", cards)
    return cards


def fetch_lorcana_json() -> list[dict]:
    """Fetch allCards from LorcanaJSON (cached 24h)."""
    cached = _cache.get("lorcana_json")
    if cached is not None:
        return cached
    data = json.loads(_fetch("https://lorcanajson.org/files/current/en/allCards.json"))
    cards = data["cards"]
    _cache.set("lorcana_json", cards)
    return cards


def build_api_lookup(cards: list[dict]) -> dict:
    """(Set_Name, card_num_int) → card dict."""
    lookup: dict = {}
    for c in cards:
        try:
            key = (c["Set_Name"], int(c["Card_Num"]))
            lookup.setdefault(key, c)
        except (KeyError, ValueError):
            continue
    return lookup


def build_lj_lookup(cards: list[dict]) -> dict:
    """(setCode_str, card_num_int) → [card, ...] list to handle duplicate numbers."""
    lookup: dict = {}
    for c in cards:
        try:
            key = (str(c["setCode"]), int(c["number"]))
            lookup.setdefault(key, []).append(c)
        except (KeyError, ValueError):
            continue
    return lookup


def fetch_duels_ink() -> list[dict]:
    """Fetch all cards from duels.ink (paginated 100/page, cached 24h).

    Covers all sets including Set 13+. Primary use: legality data, structured
    ability text, and card image URLs — fields the other APIs don't expose.
    """
    cached = _cache.get("duels_ink")
    if cached is not None:
        return cached
    cards: list[dict] = []
    offset = 0
    while True:
        data = json.loads(_fetch(f"https://duels.ink/api/cards?limit=100&offset={offset}"))
        cards.extend(data["cards"])
        if not data["meta"]["hasMore"]:
            break
        offset += 100
    _cache.set("duels_ink", cards)
    return cards


def build_duels_lookup(cards: list[dict]) -> dict:
    """(setCode_str, card_num_int) → card dict.

    duels.ink IDs are "{set}-{num}" for regular cards (e.g. "1-61") and
    "{set}-PD1-{n}" for promo variants. We only index the regular format
    since promo numbers don't align with TCGPlayer card numbers.
    """
    lookup: dict = {}
    for c in cards:
        parts = c.get("id", "").split("-")
        if len(parts) == 2:
            try:
                lookup[(parts[0], int(parts[1]))] = c
            except ValueError:
                continue
    return lookup


DUELS_FORMAT_LABELS: dict[str, str] = {
    "core":      "Core EN",
    "infinity":  "Infinity",
    "core_zh":   "Core ZH",
    "core_ja":   "Core JA",
}


def load_all_data() -> tuple[dict, dict, list[dict]]:
    """Fetch both primary APIs and return (api_lookup, lj_lookup, lj_cards_list)."""
    api_cards = fetch_lorcana_api()
    lj_cards = fetch_lorcana_json()
    return build_api_lookup(api_cards), build_lj_lookup(lj_cards), lj_cards


def search_card(name: str, set_name: str = "") -> dict | None:
    """Find a card by name (exact then partial) across LorcanaJSON."""
    lj_cards = fetch_lorcana_json()
    name_lower = name.lower()

    # Exact fullName match (optionally filtered by set)
    for c in lj_cards:
        if c.get("fullName", "").lower() == name_lower:
            if not set_name or set_name.lower() in LJCODE_TO_SETNAME.get(str(c.get("setCode")), "").lower():
                return c

    # Partial match — return the most recent set's version
    matches = [c for c in lj_cards if name_lower in c.get("fullName", "").lower()]
    if set_name:
        filtered = [c for c in matches if set_name.lower() in LJCODE_TO_SETNAME.get(str(c.get("setCode")), "").lower()]
        if filtered:
            return filtered[-1]
    return matches[-1] if matches else None

# ── Card search / filtering ─────────────────────────────────────────────────────

def _card_colors(card: dict) -> list[str]:
    colors = card.get("colors")
    if colors:
        return list(colors)
    color = card.get("color", "")
    return color.split("-") if color else []


def _card_type_matches(card: dict, card_type: str) -> bool:
    ctype = card.get("type", "")
    if card_type.lower() == "song":
        return ctype == "Action" and "Song" in (card.get("subtypes") or [])
    return ctype.lower() == card_type.lower()


def _card_has_keyword(card: dict, keyword: str) -> bool:
    keyword_lower = keyword.lower()
    for ab in card.get("abilities", []):
        if ab.get("type") == "keyword" and ab.get("keyword", "").lower() == keyword_lower:
            return True
    return False


def filter_cards(
    cards: list[dict],
    colors: list[str] | None = None,
    card_type: str = "",
    rarity: str = "",
    set_name: str = "",
    cost_min: int | None = None,
    cost_max: int | None = None,
    keyword: str = "",
    ability_text: str = "",
    subtype: str = "",
) -> list[dict]:
    """Filter LorcanaJSON cards by any combination of the given criteria.

    `colors` matches if the card has ANY of the given colors (dual-ink cards
    match on either half). All other filters are ANDed together.
    """
    colors_lower = {c.lower() for c in colors} if colors else None
    set_name_lower = set_name.lower() if set_name else ""
    ability_text_lower = ability_text.lower() if ability_text else ""
    subtype_lower = subtype.lower() if subtype else ""

    result = []
    for c in cards:
        if colors_lower is not None:
            card_colors = {cc.lower() for cc in _card_colors(c)}
            if not (card_colors & colors_lower):
                continue

        if card_type and not _card_type_matches(c, card_type):
            continue

        if rarity and c.get("rarity", "").lower() != rarity.lower():
            continue

        if set_name_lower:
            set_display = LJCODE_TO_SETNAME.get(str(c.get("setCode")), "")
            if set_name_lower not in set_display.lower():
                continue

        cost = c.get("cost")
        if cost_min is not None and (not isinstance(cost, int) or cost < cost_min):
            continue
        if cost_max is not None and (not isinstance(cost, int) or cost > cost_max):
            continue

        if keyword and not _card_has_keyword(c, keyword):
            continue

        if ability_text_lower and ability_text_lower not in c.get("fullText", "").lower():
            continue

        if subtype_lower and subtype_lower not in [s.lower() for s in (c.get("subtypes") or [])]:
            continue

        result.append(c)

    result.sort(key=lambda c: (c.get("cost") if isinstance(c.get("cost"), int) else 99, c.get("fullName", "")))
    return result
