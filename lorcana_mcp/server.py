from __future__ import annotations

import csv
import re

from mcp.server.fastmcp import FastMCP

from .api import (
    search_card, abilities_from_lj, LJCODE_TO_SETNAME, SETNAME_TO_LJCODE,
    fetch_duels_ink, build_duels_lookup, DUELS_FORMAT_LABELS,
    fetch_lorcana_json, filter_cards, _card_colors, resolve_card as _resolve_card,
    singer_value, is_song, find_song_singers,
    fetch_tcgcsv_prices, cheapest_price_for_card,
)
from .enricher import enrich_csv as _enrich_csv, audit_csv as _audit_csv, _num_int
from .deck import analyze_deck as _analyze_deck, what_am_i_missing as _what_am_i_missing

mcp = FastMCP(
    "Lorcana",
    instructions=(
        "Use these tools to enrich Disney Lorcana TCG collection exports from TCGPlayer, "
        "look up individual card data, resolve an informal/misspelled card name, "
        "search the full card pool by filters, find characters that can sing a given song, "
        "filter a collection by play format, "
        "audit an enriched collection for stale or wrong card data, "
        "analyze a deck list for curve, composition, and format legality, "
        "or check a deck list against your collection for what's missing and its cost to complete."
    ),
)

_PROMO_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*$")


def _load_collection_csv(csv_path: str) -> tuple[dict[str, int], dict[str, float]]:
    """Product Name (promo suffix stripped, lowercased) -> (owned qty, cheapest known price).

    The price side lets callers reuse the enriched CSV's own TCG Market Price
    column instead of hitting an external pricing API for cards already owned
    — only cards owned at zero copies actually need a live lookup.
    """
    counts: dict[str, int] = {}
    prices: dict[str, float] = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = _PROMO_SUFFIX_RE.sub("", row.get("Product Name", "")).strip()
            if not name:
                continue
            key = name.lower()

            try:
                qty = int(float(row.get("Add to Quantity", "0") or "0"))
            except ValueError:
                qty = 0
            if qty > 0:
                counts[key] = counts.get(key, 0) + qty

            price_str = row.get("TCG Market Price", "")
            if price_str:
                try:
                    price = float(price_str)
                    if key not in prices or price < prices[key]:
                        prices[key] = price
                except ValueError:
                    pass

    return counts, prices


def _load_owned_counts(csv_path: str) -> dict[str, int]:
    """Product Name (promo suffix stripped) -> total owned quantity."""
    return _load_collection_csv(csv_path)[0]


@mcp.tool()
def enrich_csv(input_path: str, cache_path: str = "", refresh_prices: bool = False) -> str:
    """
    Enrich a raw TCGPlayer Lorcana CSV export with full card data.

    Fetches card data from LorcanaJSON and lorcana-api.com and adds Ink color,
    Ink Cost, Card Type, Subtypes, Strength, Willpower, Lore Points, Inkable,
    Keywords, and Abilities to each row.

    Writes two output files next to the input:
      enriched_{filename}  — enriched collection CSV
      dreamborn_{filename} — import-ready CSV for dreamborn.ink

    Args:
        input_path: Absolute path to the raw TCGPlayer CSV export.
        cache_path: Optional path to a previous enriched CSV to speed up re-runs
                    by skipping API calls for cards already seen.
        refresh_prices: If True, overwrite each row's TCG Market Price with a
                        live tcgcsv.com lookup for that exact printing, instead
                        of leaving whatever the raw TCGPlayer export had at
                        download time. Use this to bring an old enriched CSV's
                        prices current without re-exporting from TCGPlayer.
    """
    try:
        result = _enrich_csv(input_path, cache_path=cache_path or None, refresh_prices=refresh_prices)
    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Enrichment failed: {e}"

    fill = result["fill_rates"]
    fill_lines = "\n".join(f"  {f}: {v}" for f, v in fill.items())

    unmatched_block = ""
    if result["unmatched"]:
        unmatched_block = "\n\nUnmatched cards (no API entry found):\n" + "\n".join(
            f"  {u}" for u in result["unmatched"]
        )

    promo_block = ""
    if result["promo_skipped"]:
        rows = [f"| {p['num']} | {p['name']} | {p['printing']} | {p['count']} |"
                for p in result["promo_skipped"]]
        promo_block = (
            "\n\nPromo cards (add manually in dreamborn.ink):\n"
            "| # | Name | Printing | Qty |\n"
            "|---|------|----------|-----|\n" +
            "\n".join(rows)
        )

    prices_line = ""
    if result["prices_refreshed"] is not None:
        prices_line = f"  Prices refreshed: {result['prices_refreshed']}/{result['total_rows']}\n"

    return (
        f"Enrichment complete.\n\n"
        f"Output files:\n"
        f"  Enriched:  {result['enriched_path']}\n"
        f"  Dreamborn: {result['dreamborn_path']}\n\n"
        f"Stats:\n"
        f"  Total rows:   {result['total_rows']}\n"
        f"  Cache hits:   {result['cache_hits']}\n"
        f"  API fetches:  {result['api_fetches']}\n"
        f"  Dreamborn rows written: {result['dreamborn_rows']}\n"
        f"{prices_line}\n"
        f"Fill rates:\n{fill_lines}"
        f"{unmatched_block}"
        f"{promo_block}"
    )


def _format_card_detail(card: dict) -> str:
    """Full stats/abilities/legality block for a single resolved card."""
    set_display = LJCODE_TO_SETNAME.get(str(card.get("setCode")), f"Set {card.get('setCode')}")
    abilities_text = abilities_from_lj(card.get("abilities", []))

    keywords = []
    for ab in card.get("abilities", []):
        if ab.get("type") == "keyword":
            keywords.append(ab.get("fullText", ab.get("keyword", "")))

    strength = card.get("strength", "")
    willpower = card.get("willpower", "")
    lore = card.get("lore", "")
    stats = " | ".join(filter(None, [
        f"STR {strength}" if strength != "" else "",
        f"WIL {willpower}" if willpower != "" else "",
        f"Lore {lore}" if lore != "" else "",
    ])) or "—"

    subtypes = ", ".join(card.get("subtypes", [])) or "—"

    lines = [
        f"**{card.get('fullName', '—')}**",
        f"Set: {set_display} (#{card.get('number')})",
        f"Ink: {card.get('color', '—')}  |  Cost: {card.get('cost', '—')}  |  Inkable: {'Yes' if card.get('inkwell') else 'No'}",
        f"Type: {card.get('type', '—')}  |  Subtypes: {subtypes}",
        f"Stats: {stats}",
        f"Rarity: {card.get('rarity', '—')}",
    ]
    if keywords:
        lines.append(f"Keywords: {', '.join(keywords)}")

    # Supplement with duels.ink: legality + image + structured abilities
    duels_card = _duels_lookup_card(card)
    if duels_card:
        legality = duels_card.get("legality", [])
        if legality:
            lines.append("Legal in: " + ", ".join(
                DUELS_FORMAT_LABELS.get(f, f) for f in legality
            ))
        else:
            lines.append("Legal in: Not legal in any tracked format")

        # Prefer duels.ink rulesText if it's richer than the LJ abilities text
        duels_rules = duels_card.get("rulesText", "").strip()
        if duels_rules and not abilities_text:
            abilities_text = duels_rules

        image = duels_card.get("imageUrl", "")
        if image:
            lines.append(f"Image: {image}")

    if abilities_text:
        lines.append(f"\n{abilities_text}")

    return "\n".join(lines)


@mcp.tool()
def lookup_card(name: str, set_name: str = "") -> str:
    """
    Look up a Lorcana card by name and return its full stats, abilities, and legality.

    Searches LorcanaJSON for an exact name match, then falls back to partial match.
    Supplements with duels.ink data for format legality, structured abilities,
    and card image URL. If the same card exists in multiple sets, the most recent
    printing is returned unless set_name is specified.

    Args:
        name: Card name, e.g. "Mirage - Super Recruiter" or just "Mirage".
        set_name: Optional set name to narrow the search, e.g. "Wilds Unknown".
    """
    card = search_card(name, set_name)
    if not card:
        return f'No card found matching "{name}"' + (f' in set "{set_name}"' if set_name else "") + "."
    return _format_card_detail(card)


@mcp.tool()
def resolve_card(name: str, set_name: str = "") -> str:
    """
    Resolve an informal, misspelled, or subtitle-less card name to specific card(s).

    Unlike lookup_card's simple substring match, this tokenizes the query and
    scores it against every card's name and subtitle, tolerating missing
    dashes ("goofy musketeer"), missing subtitles ("Elsa" — which returns all
    her versions), word order, and minor typos ("musketer"). Use this when
    lookup_card fails or when you're not sure of a card's exact printed name.

    Returns one of three shapes:
      - A single confident match: full card detail (same as lookup_card).
      - Multiple plausible matches: a ranked top-3 list with confidence scores,
        for you to disambiguate (e.g. "Pete" with no further qualifier, or a
        bare character name matching several printings).
      - No match: nothing scored above the noise floor.

    Args:
        name: Informal, partial, or misspelled card name.
        set_name: Optional set name to narrow the search, e.g. "Wilds Unknown".
    """
    result = _resolve_card(name, set_name)

    if result["match_type"] == "not_found":
        return f'No card found matching "{name}"' + (f' in set "{set_name}"' if set_name else "") + "."

    if result["match_type"] == "resolved":
        return _format_card_detail(result["candidates"][0][1])

    lines = [f'Multiple cards could match "{name}" — did you mean one of these?\n']
    for score, card in result["candidates"]:
        set_display = LJCODE_TO_SETNAME.get(str(card.get("setCode")), f"Set {card.get('setCode')}")
        stat_vals = [card.get("strength"), card.get("willpower"), card.get("lore")]
        stats = "/".join(str(v) if v is not None else "—" for v in stat_vals) \
            if any(v is not None for v in stat_vals) else "—"
        lines.append(
            f"- **{card.get('fullName', '—')}** ({int(score * 100)}% match) — "
            f"{set_display}, Cost {card.get('cost', '—')}, {stats}"
        )
    lines.append("\nCall lookup_card or resolve_card again with the exact name to get full details.")
    return "\n".join(lines)


@mcp.tool()
def search_cards(
    colors: str = "",
    card_type: str = "",
    rarity: str = "",
    set_name: str = "",
    cost_min: int = -1,
    cost_max: int = -1,
    keyword: str = "",
    ability_text: str = "",
    subtype: str = "",
    offset: int = 0,
    limit: int = 25,
) -> str:
    """
    Search the full Lorcana card pool by any combination of filters.

    All filters are optional and ANDed together, except colors: a card matches
    if it has ANY of the given colors, so dual-ink cards surface for either half.

    Args:
        colors: Comma-separated ink color(s), e.g. "Amber,Steel". Case-insensitive.
        card_type: "Character", "Action", "Item", "Location", or "Song" (Action
                   cards with the Song subtype).
        rarity: "Common", "Uncommon", "Rare", "Super Rare", "Legendary", "Enchanted",
                "Epic", "Iconic", or "Special".
        set_name: Set name substring, e.g. "Wilds Unknown".
        cost_min: Minimum ink cost, inclusive. Pass -1 (default) for no minimum.
        cost_max: Maximum ink cost, inclusive. Pass -1 (default) for no maximum.
        keyword: Keyword ability name, e.g. "Evasive", "Rush", "Bodyguard", "Shift".
        ability_text: Substring to search for in full ability text (case-insensitive).
        subtype: Subtype/classification, e.g. "Toy", "Hero", "Villain", "Princess".
        offset: Pagination offset, 0-based.
        limit: Max results in this page (default 25, capped at 200).
    """
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    color_list = [c.strip() for c in colors.split(",") if c.strip()]

    try:
        lj_cards = fetch_lorcana_json()
    except Exception as e:
        return f"Failed to fetch card data: {e}"

    matches = filter_cards(
        lj_cards,
        colors=color_list or None,
        card_type=card_type,
        rarity=rarity,
        set_name=set_name,
        cost_min=None if cost_min < 0 else cost_min,
        cost_max=None if cost_max < 0 else cost_max,
        keyword=keyword,
        ability_text=ability_text,
        subtype=subtype,
    )

    if not matches:
        return "No cards matched the given filters."

    total = len(matches)
    page = matches[offset: offset + limit]

    if not page:
        return f"No results at offset {offset} — {total} total match(es) (try a smaller offset)."

    by_ink: dict[str, list] = {}
    for card in page:
        ink = "/".join(_card_colors(card)) or "Unknown"
        by_ink.setdefault(ink, []).append(card)

    lines = [
        f"**Search results** — {total} match(es) (showing {offset + 1}-{offset + len(page)})\n",
    ]

    for ink in sorted(by_ink):
        lines.append(f"### {ink}")
        lines.append("| Card | Cost | Type | STR/WIL/Lore | Keywords |")
        lines.append("|------|------|------|------|------|")
        for card in by_ink[ink]:
            ctype = card.get("type", "—")
            if ctype == "Action" and "Song" in (card.get("subtypes") or []):
                ctype = "Action - Song"

            stat_vals = [card.get("strength"), card.get("willpower"), card.get("lore")]
            stats = "/".join(str(v) if v is not None else "—" for v in stat_vals) \
                if any(v is not None for v in stat_vals) else "—"

            keywords = [
                ab.get("fullText", ab.get("keyword", ""))
                for ab in card.get("abilities", [])
                if ab.get("type") == "keyword"
            ]

            lines.append(
                f"| {card.get('fullName', '—')} "
                f"| {card.get('cost', '—')} "
                f"| {ctype} "
                f"| {stats} "
                f"| {', '.join(keywords) or '—'} |"
            )
        lines.append("")

    if offset + limit < total:
        lines.append(
            f"_{total - offset - limit} more match(es) — pass offset={offset + limit} for the next page._"
        )

    return "\n".join(lines)


@mcp.tool()
def find_song_synergies(
    song_name: str = "",
    cost: int = -1,
    colors: str = "",
    collection_csv: str = "",
    limit: int = 50,
) -> str:
    """
    Find every Character that can sing a given song, for free-song Singer combos.

    A character can sing a song if its printed ink cost meets the song's cost
    outright, OR it has a "Singer X" keyword with X meeting the song's cost —
    Singer lets a cheap character punch above its actual cost for singing
    purposes only (see the Steelsong package: Amber Singers unlocking
    expensive Steel songs for free). Provide either song_name (resolved the
    same fuzzy way as resolve_card) or a raw cost threshold — not both.

    Results are grouped: Singer-keyword characters first (the actual
    "discount" picks — highest Singer value, then cheapest actual cost),
    followed by characters that simply cost enough to sing it outright,
    cheapest first.

    Args:
        song_name: Name of a Song card, e.g. "Be Our Guest". Fuzzy-matched.
        cost: Raw song cost threshold to use instead of song_name, e.g. 5.
        colors: Optional comma-separated ink color(s) to restrict characters to,
                e.g. "Amber,Steel".
        collection_csv: Optional path to an enriched collection CSV — when given,
                        each character is flagged with how many copies you own.
        limit: Max characters to list (default 50, capped at 200).
    """
    if song_name and cost >= 0:
        return "Provide either song_name or cost, not both."

    if song_name:
        result = _resolve_card(song_name)
        if result["match_type"] == "not_found":
            return f'No card found matching "{song_name}".'
        if result["match_type"] == "ambiguous":
            lines = [f'Multiple cards could match "{song_name}" — did you mean one of these?\n']
            for score, card in result["candidates"]:
                lines.append(f"- **{card.get('fullName', '—')}** ({int(score * 100)}% match)")
            lines.append("\nCall find_song_synergies again with the exact song name.")
            return "\n".join(lines)

        song_card = result["candidates"][0][1]
        if not is_song(song_card):
            return f'"{song_card.get("fullName")}" is not a Song card.'
        song_cost = song_card.get("cost")
        song_display = song_card.get("fullName", song_name)
    elif cost >= 0:
        song_cost = cost
        song_display = f"cost {cost}"
    else:
        return "Provide either song_name or cost."

    limit = max(1, min(limit, 200))
    color_list = [c.strip() for c in colors.split(",") if c.strip()]

    try:
        lj_cards = fetch_lorcana_json()
    except Exception as e:
        return f"Failed to fetch card data: {e}"

    matches = find_song_singers(song_cost, lj_cards, colors=color_list or None)

    if not matches:
        return f"No characters can sing a song costing {song_cost}."

    owned = _load_owned_counts(collection_csv) if collection_csv else None

    total = len(matches)
    page = matches[:limit]

    header = ["Card", "Ink", "Cost", "Singer"]
    if owned is not None:
        header.append("Owned")

    singers = [c for c in page if singer_value(c) is not None]
    plain = [c for c in page if singer_value(c) is None]

    lines = [f"**Characters that can sing \"{song_display}\"** (cost {song_cost}) — {total} match(es)\n"]

    def _row(card: dict) -> str:
        ink = "/".join(_card_colors(card)) or "—"
        sv = singer_value(card)
        cells = [
            card.get("fullName", "—"), ink, str(card.get("cost", "—")),
            f"Singer {sv}" if sv is not None else "—",
        ]
        if owned is not None:
            qty = owned.get(card.get("fullName", "").lower(), 0)
            cells.append(f"{qty}x" if qty else "Not owned")
        return "| " + " | ".join(cells) + " |"

    if singers:
        lines.append("### Singer keyword (best discount)")
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join("---" for _ in header) + "|")
        lines.extend(_row(c) for c in singers)
        lines.append("")

    if plain:
        lines.append("### Cost alone qualifies")
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join("---" for _ in header) + "|")
        lines.extend(_row(c) for c in plain)
        lines.append("")

    if total > limit:
        lines.append(f"_{total - limit} more match(es) not shown — raise limit to see them._")

    return "\n".join(lines)


@mcp.tool()
def filter_collection(csv_path: str, format: str = "core") -> str:
    """
    Filter an enriched collection CSV to cards legal in a specific play format.

    Legality data comes from duels.ink, which tracks Core EN, Infinity, Core ZH,
    and Core JA rotation. Poorcana (Common/Uncommon only, 50-card min) is derived
    from the Rarity column in the CSV — no external lookup needed.

    Args:
        csv_path: Absolute path to an enriched Lorcana collection CSV.
        format:   "core", "infinity", "core_zh", "core_ja", or "poorcana".
    """
    fmt = format.lower().strip()
    valid = {"core", "infinity", "core_zh", "core_ja", "poorcana"}
    if fmt not in valid:
        return f'Unknown format "{format}". Valid options: {", ".join(sorted(valid))}.'

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError as e:
        return f"Error: {e}"

    if fmt == "poorcana":
        return _filter_poorcana(rows)

    # Core / Infinity / regional — need duels.ink legality
    try:
        duels_cards = fetch_duels_ink()
    except Exception as e:
        return f"Failed to fetch duels.ink data: {e}"

    duels = build_duels_lookup(duels_cards)
    format_label = DUELS_FORMAT_LABELS.get(fmt, fmt)

    legal_rows = []
    not_found = 0

    for row in rows:
        set_name = row.get("Set Name", "").strip()
        if set_name == "Disney Lorcana Promo Cards":
            continue
        num_i = _num_int(row.get("Number", ""))
        set_code = SETNAME_TO_LJCODE.get(set_name)
        if not set_code or num_i is None:
            not_found += 1
            continue

        duels_card = duels.get((set_code, num_i))
        if duels_card is None:
            not_found += 1
            continue

        if fmt in duels_card.get("legality", []):
            try:
                qty = int(float(row.get("Add to Quantity", "0") or "0"))
            except ValueError:
                qty = 0
            legal_rows.append((row, qty))

    if not legal_rows:
        return f"No cards in your collection are legal in {format_label}."

    total_unique = len(legal_rows)
    total_copies = sum(qty for _, qty in legal_rows)

    # Group by ink color
    by_ink: dict[str, list] = {}
    for row, qty in legal_rows:
        ink = row.get("Ink", "Unknown")
        by_ink.setdefault(ink, []).append((row, qty))

    lines = [
        f"**{format_label} legal cards in your collection**",
        f"{total_unique} unique cards · {total_copies} total copies\n",
    ]

    for ink in sorted(by_ink):
        ink_rows = sorted(by_ink[ink], key=lambda x: (
            int(x[0].get("Ink Cost", "99") or "99"),
            x[0].get("Product Name", ""),
        ))
        lines.append(f"### {ink}")
        lines.append("| Card | Cost | Type | Qty |")
        lines.append("|------|------|------|-----|")
        for row, qty in ink_rows:
            lines.append(
                f"| {row.get('Product Name', '—')} "
                f"| {row.get('Ink Cost', '—')} "
                f"| {row.get('Card Type', '—')} "
                f"| {qty} |"
            )
        lines.append("")

    if not_found:
        lines.append(f"_{not_found} rows skipped (no duels.ink match — may be newer set cards)._")

    return "\n".join(lines)


def _filter_poorcana(rows: list[dict]) -> str:
    legal_rarities = {"Common", "Uncommon"}
    legal_rows = []
    for row in rows:
        rarity = row.get("Rarity", "").strip()
        if rarity not in legal_rarities:
            continue
        try:
            qty = int(float(row.get("Add to Quantity", "0") or "0"))
        except ValueError:
            qty = 0
        legal_rows.append((row, qty))

    if not legal_rows:
        return "No Common or Uncommon cards found in your collection."

    total_unique = len(legal_rows)
    total_copies = sum(qty for _, qty in legal_rows)

    by_ink: dict[str, list] = {}
    for row, qty in legal_rows:
        ink = row.get("Ink", "Unknown")
        by_ink.setdefault(ink, []).append((row, qty))

    lines = [
        "**Poorcana legal cards in your collection** (Common + Uncommon)",
        f"{total_unique} unique cards · {total_copies} total copies\n",
    ]

    for ink in sorted(by_ink):
        ink_rows = sorted(by_ink[ink], key=lambda x: (
            int(x[0].get("Ink Cost", "99") or "99"),
            x[0].get("Product Name", ""),
        ))
        lines.append(f"### {ink}")
        lines.append("| Card | Cost | Rarity | Qty |")
        lines.append("|------|------|--------|-----|")
        for row, qty in ink_rows:
            lines.append(
                f"| {row.get('Product Name', '—')} "
                f"| {row.get('Ink Cost', '—')} "
                f"| {row.get('Rarity', '—')} "
                f"| {qty} |"
            )
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def audit_csv(csv_path: str) -> str:
    """
    Audit an enriched Lorcana collection CSV against live API data.

    Checks Ink color, Ink Cost, Card Type, Subtypes, Inkable, and stats
    (Strength / Willpower / Lore Points) for every non-promo card. Useful after
    a new set releases or if enrichment data looks suspicious.

    Args:
        csv_path: Absolute path to an enriched Lorcana collection CSV.
    """
    try:
        result = _audit_csv(csv_path)
    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Audit failed: {e}"

    issues = result["issues"]

    if not issues:
        return (
            f"Audit complete — no discrepancies found.\n"
            f"Reviewed {result['reviewed']} cards ({result['skipped_promos']} promos skipped)."
        )

    lines = [
        f"Audit complete: {result['reviewed']} cards reviewed, "
        f"{result['skipped_promos']} promos skipped.\n"
        f"**{len(issues)} discrepancies found:**\n",
    ]

    current_card = None
    for issue in issues:
        if issue["card"] != current_card:
            current_card = issue["card"]
            lines.append(f"\n{current_card}")
        lines.append(f"  {issue['field']}: \"{issue['csv_value']}\" → \"{issue['api_value']}\"")

    return "\n".join(lines)


@mcp.tool()
def analyze_deck(deck_list: str) -> str:
    """
    Analyze a raw deck list and return curve, composition, and legality stats.

    Accepts one card per line, e.g. "4x Goofy - Musketeer" or "4 Goofy - Musketeer"
    (both "4x" and "4 " are accepted; qty is optional and defaults to 1).
    Lines starting with "#" or "//" are treated as comments and skipped.

    Reports: ink curve (1-2/3-4/5-6/7+ cost brackets), inkable vs. uninkable count,
    color split, card type split, an estimated lore-per-turn (sum of Character lore
    values), a Core Constructed legality check (60-card minimum, max 4 copies of any
    card, at most 2 ink colors), and any card names that couldn't be resolved.

    Args:
        deck_list: Raw deck list text, one card per line.
    """
    result = _analyze_deck(deck_list)

    if result["total_cards"] == 0:
        return "No cards found in deck list. Expected one card per line, e.g. \"4x Goofy - Musketeer\"."

    curve = result["curve"]
    curve_line = " | ".join(f"{b}: {curve[b]}" for b in ("1-2", "3-4", "5-6", "7+"))

    color_lines = "\n".join(
        f"  {c}: {n}" for c, n in sorted(result["color_counts"].items(), key=lambda x: -x[1])
    ) or "  —"
    type_lines = "\n".join(
        f"  {t}: {n}" for t, n in sorted(result["type_counts"].items(), key=lambda x: -x[1])
    ) or "  —"

    legality = result["legality"]
    legality_lines = [
        f"  {'✓' if legality['min_60_cards'] else '✗'} Minimum 60 cards ({result['total_cards']} total)",
        f"  {'✓' if legality['max_4_copies'] else '✗'} Max 4 copies per card"
        + ("" if legality["max_4_copies"] else
           " — over limit: " + ", ".join(f"{n}x {c}" for c, n in legality["over_limit_cards"])),
        f"  {'✓' if legality['two_ink_colors_or_fewer'] else '✗'} At most 2 ink colors"
        + f" (used: {', '.join(legality['ink_colors_used']) or '—'})",
    ]

    lines = [
        f"**Deck analysis** — {result['total_cards']} cards ({result['unique_cards']} unique)\n",
        f"Ink curve: {curve_line}",
        f"Inkable: {result['inkable_count']}  |  Uninkable: {result['uninkable_count']}",
        f"Estimated lore/turn (all questors): {result['lore_per_turn']}\n",
        "Color split:",
        color_lines,
        "\nCard types:",
        type_lines,
        "\nCore Constructed legality:",
        "\n".join(legality_lines),
    ]

    if result["unresolved"]:
        lines.append(
            "\nUnrecognized card names (excluded from stats above):\n" +
            "\n".join(f"  {u['qty']}x {u['name']}" for u in result["unresolved"])
        )

    return "\n".join(lines)


@mcp.tool()
def what_am_i_missing(deck_list: str, collection_csv: str) -> str:
    """
    Compare a deck list against your collection: what you own, what's missing,
    and the estimated cost to complete it.

    Cross-references a raw deck list (same format as analyze_deck: `4x Card
    Name` per line) against an enriched collection CSV. For every card you're
    short on, first checks the CSV's own TCG Market Price (you already own at
    least one printing, so it's already there — no network needed). Only cards
    you own zero copies of fall back to a live TCGPlayer lookup via tcgcsv.com
    (cheapest printing across all sets/rarities — gameplay is identical
    regardless of rarity or art). That fallback fetch only happens if at least
    one card actually needs it, and its price data is cached 24h.

    Args:
        deck_list: Raw deck list text, one card per line (e.g. "4x Goofy - Musketeer").
        collection_csv: Absolute path to an enriched Lorcana collection CSV.
    """
    try:
        owned_counts, owned_prices = _load_collection_csv(collection_csv)
    except FileNotFoundError as e:
        return f"Error: {e}"

    result = _what_am_i_missing(deck_list, owned_counts)

    if not result["entries"] and not result["unresolved"]:
        return 'No cards found in deck list. Expected one card per line, e.g. "4x Goofy - Musketeer".'

    have_fully = [e for e in result["entries"] if e["missing"] == 0]
    short = [e for e in result["entries"] if e["missing"] > 0]

    lines = [f"**Deck completion check** — {len(result['entries'])} unique card(s)\n"]

    if have_fully:
        lines.append(f"### Already have ({len(have_fully)})")
        for e in have_fully:
            lines.append(f"- {e['name']} — need {e['needed']}, own {e['owned']}")
        lines.append("")

    if short:
        lines.append(f"### Missing or short ({len(short)})")

        # Only reach for live pricing if some card isn't already priced locally.
        needs_live_price = any(e["name"].lower() not in owned_prices for e in short)
        lj_cards, price_by_pid, live_price_failed = [], {}, False
        if needs_live_price:
            try:
                lj_cards = fetch_lorcana_json()
                price_by_pid = fetch_tcgcsv_prices()
            except Exception:
                live_price_failed = True

        total_cost = 0.0
        priced_count = 0
        used_local_price = False
        used_live_price = False
        for e in short:
            local_price = owned_prices.get(e["name"].lower())
            if local_price is not None:
                price = local_price
                used_local_price = True
            elif not live_price_failed:
                price = cheapest_price_for_card(e["name"], lj_cards, price_by_pid)
                if price is not None:
                    used_live_price = True
            else:
                price = None

            if price is not None:
                total_cost += price * e["missing"]
                priced_count += 1
                cost_str = f"${price * e['missing']:.2f}"
            else:
                cost_str = "price unknown"
            lines.append(
                f"- {e['name']} — need {e['needed']}, own {e['owned']}, "
                f"missing {e['missing']} ({cost_str})"
            )
        lines.append("")

        if priced_count:
            note = "" if priced_count == len(short) else f" ({len(short) - priced_count} card(s) had no price data)"
            lines.append(f"**Estimated cost to complete: ${total_cost:.2f}**{note}")
            if used_local_price and used_live_price:
                lines.append(
                    "_Prices from your collection where you already own a printing; "
                    "live TCGPlayer snapshot (tcgcsv.com) for the rest — treat as an estimate, not a quote._"
                )
            elif used_live_price:
                lines.append("_Live TCGPlayer snapshot via tcgcsv.com — treat as an estimate, not a quote._")
            else:
                lines.append("_Prices from your own collection CSV._")
        elif live_price_failed:
            lines.append("_Could not fetch live TCGPlayer prices — cost estimate unavailable._")
        lines.append("")

    if result["unresolved"]:
        lines.append("### Unrecognized card names")
        for u in result["unresolved"]:
            lines.append(f"- {u['qty']}x {u['name']}")

    return "\n".join(lines)


def _duels_lookup_card(lj_card: dict) -> dict | None:
    """Find a LorcanaJSON card in the duels.ink lookup by (setCode, number)."""
    try:
        duels_cards = fetch_duels_ink()
    except Exception:
        return None
    duels = build_duels_lookup(duels_cards)
    set_code = str(lj_card.get("setCode", ""))
    number = lj_card.get("number")
    if not set_code or number is None:
        return None
    return duels.get((set_code, int(number)))


def main() -> None:
    mcp.run()
