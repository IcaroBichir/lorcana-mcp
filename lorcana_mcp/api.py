"""Card data fetching from lorcana-api.com and LorcanaJSON, plus enrichment helpers."""
from __future__ import annotations

import difflib
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
    # Some hosts (tcgcsv.com) reject the default "Python-urllib/x.y" UA with a 401.
    req = urllib.request.Request(url, headers={"User-Agent": "lorcana-mcp/1.0"})
    return urllib.request.urlopen(req, timeout=60).read()


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
    """Find the single best-matching card by name across LorcanaJSON.

    Uses fuzzy token scoring (see score_candidates) and returns the top match,
    or None if nothing scores above zero. For ambiguous queries where several
    cards are close contenders, use score_candidates directly to see all of them.
    """
    candidates = score_candidates(name, set_name)
    return candidates[0][1] if candidates else None

# ── Fuzzy card resolution ────────────────────────────────────────────────────────

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _token_match(query_token: str, card_token: str) -> bool:
    """True if a query token plausibly refers to a card token.

    Exact match always counts. Substring containment only kicks in once both
    tokens are 3+ letters — otherwise short tokens like "o" or "of" become
    accidental substrings of unrelated long words (e.g. "te" is a substring of
    "musketeer") and pollute the results. Fuzzy-ratio matching (for typos like
    "musketer" vs "musketeer") requires 5+ letters on both sides — below that,
    unrelated short words collide too easily ("elsa" vs "elisa" scores 0.89).
    """
    if query_token == card_token:
        return True
    if len(query_token) < 3 or len(card_token) < 3:
        return False
    if query_token in card_token or card_token in query_token:
        return True
    if len(query_token) >= 5 and len(card_token) >= 5:
        return difflib.SequenceMatcher(None, query_token, card_token).ratio() >= 0.85
    return False


def _card_score(query_tokens: list[str], card: dict) -> float:
    """Score a card against tokenized query terms.

    Character name matches are weighted 2x subtitle/version matches, since the
    name is the more load-bearing part of a query. For multi-token queries
    (i.e. the query includes subtitle words), an extra precision term favors
    cards whose fields aren't padded out with unmatched words — this is what
    lets "goofy musketeer" prefer "Goofy - Musketeer" over "Goofy - Musketeer
    Swordsman". Single-token queries (bare character names like "Elsa") skip
    that term so same-named cards tie and fall through to recency sorting.
    """
    name_tokens = _tokenize(card.get("name", "") or "")
    version_tokens = _tokenize(card.get("version", "") or "")
    card_tokens = name_tokens + version_tokens
    if not card_tokens or not query_tokens:
        return 0.0

    weighted = 0.0
    matched_query = 0
    for qt in query_tokens:
        if any(_token_match(qt, nt) for nt in name_tokens):
            weighted += 2
            matched_query += 1
        elif any(_token_match(qt, vt) for vt in version_tokens):
            weighted += 1
            matched_query += 1

    if matched_query == 0:
        return 0.0

    recall = weighted / (len(query_tokens) * 2)
    if len(query_tokens) == 1:
        return recall

    covered = sum(1 for ct in card_tokens if any(_token_match(qt, ct) for qt in query_tokens))
    precision = covered / len(card_tokens)
    return recall * 0.85 + precision * 0.15


def _set_recency(card: dict) -> int:
    """Higher = more recent. Non-numeric set codes (promo sets) sort last."""
    try:
        return int(card.get("setCode"))
    except (TypeError, ValueError):
        return -1


def score_candidates(query: str, set_name: str = "") -> list[tuple[float, dict]]:
    """Score every LorcanaJSON card against a fuzzy query.

    Tolerates missing dashes/subtitles, word order, and minor typos. An exact
    fullName match always scores 1.0. Ties (e.g. a bare character name like
    "Elsa" matching every version of that character) are broken by set
    recency. Cards are deduplicated by fullName, keeping the best-scoring /
    most recent instance. Returns (score, card) pairs sorted best-first;
    empty if nothing scores above zero.
    """
    lj_cards = fetch_lorcana_json()
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    if set_name:
        set_name_lower = set_name.lower()
        lj_cards = [
            c for c in lj_cards
            if set_name_lower in LJCODE_TO_SETNAME.get(str(c.get("setCode")), "").lower()
        ]

    query_token_set = set(query_tokens)
    best_by_name: dict[str, tuple[float, dict]] = {}
    for c in lj_cards:
        score = _card_score(query_tokens, c)
        if score <= 0:
            continue
        full_name = c.get("fullName", "")
        # Token-set equality catches "jafar newly crowned" == "Jafar - Newly
        # Crowned" even though punctuation/word order differ.
        if query_token_set == set(_tokenize(full_name)):
            score = 1.0
        existing = best_by_name.get(full_name)
        if existing is None or (score, _set_recency(c)) > (existing[0], _set_recency(existing[1])):
            best_by_name[full_name] = (score, c)

    return sorted(best_by_name.values(), key=lambda sc: (sc[0], _set_recency(sc[1])), reverse=True)


# Below this, nothing scores highly enough to be worth surfacing at all.
_NOT_FOUND_FLOOR = 0.35
# Above this, and clear enough of the runner-up, a query is confident enough
# to auto-resolve instead of asking the user to disambiguate.
_RESOLVED_MIN_SCORE = 0.85
_RESOLVED_MIN_GAP = 0.15


def resolve_card(query: str, set_name: str = "") -> dict:
    """Classify a fuzzy card query as resolved / ambiguous / not_found.

    Returns {"match_type": "resolved" | "ambiguous" | "not_found",
             "candidates": [(score, card), ...]}.

    "resolved" means one candidate is confident and clearly ahead of the
    runner-up (candidates has exactly 1 entry). "ambiguous" means several
    candidates are plausible — e.g. a bare name like "Elsa" matching every
    version of that character, or a vague query like "big pete" that only
    partially identifies a card — and returns the top 3. "not_found" means
    nothing cleared the noise floor.
    """
    candidates = score_candidates(query, set_name)
    if not candidates or candidates[0][0] < _NOT_FOUND_FLOOR:
        return {"match_type": "not_found", "candidates": []}

    top_score = candidates[0][0]
    runner_up = candidates[1][0] if len(candidates) > 1 else 0.0
    if top_score >= _RESOLVED_MIN_SCORE and top_score - runner_up >= _RESOLVED_MIN_GAP:
        return {"match_type": "resolved", "candidates": candidates[:1]}

    return {"match_type": "ambiguous", "candidates": candidates[:3]}

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


def dedupe_by_full_name(cards: list[dict]) -> list[dict]:
    """Collapse alt-art/enchanted/reprint duplicates that share a fullName.

    allCards.json lists each printing as a separate entry, so the same card
    (e.g. a base + Enchanted pair) can appear twice with identical gameplay
    stats — see CLAUDE.md's note that Enchanted/Epic cards are gameplay-
    identical to their base version. Keeps the first occurrence of each name.
    """
    seen: set[str] = set()
    result = []
    for c in cards:
        full_name = c.get("fullName", "")
        if full_name in seen:
            continue
        seen.add(full_name)
        result.append(c)
    return result


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

    result = dedupe_by_full_name(result)
    result.sort(key=lambda c: (c.get("cost") if isinstance(c.get("cost"), int) else 99, c.get("fullName", "")))
    return result

# ── Song synergies ────────────────────────────────────────────────────────────

def singer_value(card: dict) -> int | None:
    """A character's Singer X value, or None if it has no Singer keyword."""
    for ab in card.get("abilities", []):
        if ab.get("type") == "keyword" and ab.get("keyword") == "Singer":
            v = ab.get("keywordValueNumber")
            if isinstance(v, int):
                return v
    return None


def is_song(card: dict) -> bool:
    return card.get("type") == "Action" and "Song" in (card.get("subtypes") or [])


def find_song_singers(
    song_cost: int, cards: list[dict], colors: list[str] | None = None,
) -> list[dict]:
    """Every Character that can sing a song of the given cost.

    A character qualifies if its printed cost meets the song cost outright, OR
    it has a Singer X keyword with X meeting the song cost (Singer lets a
    cheaper character punch above its actual cost for singing purposes only).

    Sorted with Singer-keyword characters first (best "discount" surfaced
    first: highest Singer value, then cheapest actual cost), followed by
    plain cost-qualifiers sorted by actual cost ascending — the cheapest way
    onto the board that can still belt out the song.
    """
    colors_lower = {c.lower() for c in colors} if colors else None
    result = []
    for c in cards:
        if c.get("type") != "Character":
            continue
        if colors_lower is not None:
            card_colors = {cc.lower() for cc in _card_colors(c)}
            if not (card_colors & colors_lower):
                continue

        cost = c.get("cost")
        sv = singer_value(c)
        qualifies_by_cost = isinstance(cost, int) and cost >= song_cost
        qualifies_by_singer = sv is not None and sv >= song_cost
        if not (qualifies_by_cost or qualifies_by_singer):
            continue

        result.append(c)

    result = dedupe_by_full_name(result)
    result.sort(key=lambda c: (
        0 if singer_value(c) is not None else 1,
        -(singer_value(c) or 0),
        c.get("cost") if isinstance(c.get("cost"), int) else 99,
        c.get("fullName", ""),
    ))
    return result

# ── TCGPlayer pricing (tcgcsv.com) ──────────────────────────────────────────────

LORCANA_TCGCSV_CATEGORY_ID = 71


def fetch_tcgcsv_groups() -> list[dict]:
    """Fetch all Lorcana set groups from tcgcsv.com (cached 24h)."""
    cached = _cache.get("tcgcsv_groups")
    if cached is not None:
        return cached
    data = json.loads(_fetch(f"https://tcgcsv.com/tcgplayer/{LORCANA_TCGCSV_CATEGORY_ID}/groups"))
    groups = data.get("results", [])
    _cache.set("tcgcsv_groups", groups)
    return groups


def fetch_tcgcsv_prices() -> dict[int, float]:
    """Fetch and merge TCGPlayer market prices for every Lorcana set (cached 24h).

    Maps productId -> marketPrice. A productId is a specific printing
    (Normal/Holofoil/etc.) of a specific card; if the same productId somehow
    shows up in more than one group's feed, the lowest price seen wins.
    """
    cached = _cache.get("tcgcsv_prices")
    if cached is not None:
        return {int(pid): price for pid, price in cached.items()}

    prices: dict[int, float] = {}
    for group in fetch_tcgcsv_groups():
        group_id = group.get("groupId")
        if group_id is None:
            continue
        try:
            data = json.loads(_fetch(
                f"https://tcgcsv.com/tcgplayer/{LORCANA_TCGCSV_CATEGORY_ID}/{group_id}/prices"
            ))
        except Exception:
            continue
        for row in data.get("results", []):
            pid, mp = row.get("productId"), row.get("marketPrice")
            if pid is None or mp is None:
                continue
            if pid not in prices or mp < prices[pid]:
                prices[pid] = mp

    _cache.set("tcgcsv_prices", prices)
    return prices


def cheapest_price_for_card(full_name: str, lj_cards: list[dict], price_by_pid: dict[int, float]) -> float | None:
    """Cheapest known TCGPlayer market price across every printing of a card.

    Different printings (base, Enchanted, promo, etc.) are gameplay-identical
    but priced differently — the cheapest is the actual cheapest legal way to
    acquire the card, regardless of rarity or art (see CLAUDE.md's "Checking
    TCGPlayer card prices" section). Returns None if no printing has a
    tcgPlayerId with a known price.
    """
    best = None
    for c in lj_cards:
        if c.get("fullName") != full_name:
            continue
        pid = (c.get("externalLinks") or {}).get("tcgPlayerId")
        if pid is None:
            continue
        price = price_by_pid.get(pid)
        if price is None:
            continue
        if best is None or price < best:
            best = price
    return best
