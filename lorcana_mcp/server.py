from __future__ import annotations

import csv
import re

from mcp.server.fastmcp import FastMCP

from .api import (
    search_card, abilities_from_lj, LJCODE_TO_SETNAME, SETNAME_TO_LJCODE,
    fetch_duels_ink, build_duels_lookup, DUELS_FORMAT_LABELS,
    fetch_lorcana_json, fetch_lorcana_sets, filter_cards, filter_by_format,
    _card_colors, resolve_card as _resolve_card,
    singer_value, is_song, find_song_singers,
    fetch_tcgcsv_prices, cheapest_price_for_card,
    fetch_format_coconut_cards, resolve_coconut_card,
)
from .enricher import enrich_csv as _enrich_csv, audit_csv as _audit_csv, _num_int
from .deck import analyze_deck as _analyze_deck, what_am_i_missing as _what_am_i_missing
from .deckbuilder import (
    build_candidate_pool, allocate_deck, rotation_safe_set_codes, summarize_picks,
    compute_shift_synergy, compute_coconut_synergy, ensure_coconut_associated_card,
)

mcp = FastMCP(
    "Lorcana",
    instructions=(
        "Use these tools to enrich Disney Lorcana TCG collection exports from TCGPlayer, "
        "look up individual card data, resolve an informal/misspelled card name, "
        "search the full card pool by filters, find characters that can sing a given song, "
        "filter a collection by play format, "
        "audit an enriched collection for stale or wrong card data, "
        "analyze a deck list for curve, composition, and format legality, "
        "check a deck list against your collection for what's missing and its cost to complete, "
        "or automatically build a legal decklist for an ink pair/format from your collection, "
        "an ideal deck priced to complete, or the full market-price build."
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


def _price_missing_entries(entries: list[dict], owned_prices: dict[str, float]) -> dict:
    """Price each {"name","needed","owned","missing"} entry: prefer the
    collection CSV's own cheapest known price, else a live tcgcsv.com lookup
    (only fetched if at least one entry needs it — and only fetched once).

    Order-preserving: `entries` in the result carries `unit_price`/
    `line_cost` (None if unpriced) in the same order as the input, so
    callers can print one line per entry the way what_am_i_missing does.
    `priced`/`unpriced` are convenience subsets for summary counts.
    """
    needs_live_price = any(e["name"].lower() not in owned_prices for e in entries)
    lj_cards, price_by_pid, live_price_failed = [], {}, False
    if needs_live_price:
        try:
            lj_cards = fetch_lorcana_json()
            price_by_pid = fetch_tcgcsv_prices()
        except Exception:
            live_price_failed = True

    priced_entries: list[dict] = []
    total_cost = 0.0
    used_local_price = False
    used_live_price = False

    for e in entries:
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
            line_cost = price * e["missing"]
            total_cost += line_cost
            priced_entries.append({**e, "unit_price": price, "line_cost": line_cost})
        else:
            priced_entries.append({**e, "unit_price": None, "line_cost": None})

    return {
        "entries": priced_entries,
        "priced": [e for e in priced_entries if e["unit_price"] is not None],
        "unpriced": [e for e in priced_entries if e["unit_price"] is None],
        "total_cost": total_cost,
        "used_local_price": used_local_price,
        "used_live_price": used_live_price,
        "live_price_failed": live_price_failed,
    }


@mcp.tool()
def enrich_csv(input_path: str, cache_path: str = "", refresh_prices: bool = False) -> str:
    """
    Enrich a raw TCGPlayer Lorcana CSV export with full card data — the
    required first step before any other tool here can read your collection
    (`filter_collection`, `audit_csv`, `what_am_i_missing`, `build_deck`, and
    `find_song_synergies`'s `collection_csv` all expect this tool's output,
    not the raw TCGPlayer export).

    Fetches card data from LorcanaJSON (sets 12+) and lorcana-api.com (sets
    1–11) and adds Ink color, Ink Cost, Card Type, Subtypes, Strength,
    Willpower, Lore Points, Inkable, Keywords, and Abilities to each row. Both
    sources are disk-cached 24h, so a second run soon after the first is
    fast regardless of `cache_path`.

    Behavior: writes two new files next to the input — never modifies
    `input_path` itself — and always reports fill-rate stats per column plus
    any cards it couldn't match (usually a name typo in the export, or a
    brand-new card the APIs haven't indexed yet). Promo cards (Set Name
    "Disney Lorcana Promo Cards") are matched by name against their
    non-promo equivalent for stats, and separately resolved to a
    dreamborn.ink-importable `(Set Number, Card Number)` row when this
    server's built-in promo table covers that card; promos it doesn't
    recognize are listed for manual entry rather than guessed. `cache_path`
    only skips re-fetching for card names already present in that prior
    enriched CSV — it does not skip enrichment for new cards in the input.

    Writes two output files next to the input:
      enriched_{filename}  — enriched collection CSV
      dreamborn_{filename} — import-ready CSV for dreamborn.ink

    Usage guidelines: run this on every fresh TCGPlayer export before doing
    anything else with it. Pass `cache_path` pointing at your previous
    enriched CSV on a re-export to speed things up — otherwise every row
    re-fetches from the API even for cards you've already enriched before.
    Use `refresh_prices=True` specifically to bring an existing enriched
    CSV's prices current without a fresh TCGPlayer export (it only touches
    the price column, not the card-data columns); leave it off for a
    same-day fresh export, since the TCGPlayer download already has current
    prices and refreshing adds an extra tcgcsv.com call per row.

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
    Look up one specific, already-known Lorcana card by (near-)exact name and
    return its full stats, abilities, and format legality in one call.

    Behavior: tries an exact name match against LorcanaJSON first, then falls
    back to a plain substring match — this is simple matching, not fuzzy
    scoring. If the same card name exists across multiple sets/printings and
    `set_name` isn't given, it silently returns the most recent printing
    rather than listing the alternatives (Enchanted/Epic/promo variants are
    gameplay-identical to the base card either way, so this rarely matters
    for stats — but a specific older printing's card ID/legality nuance won't
    surface without `set_name`). Card data (LorcanaJSON + duels.ink) is
    fetched live and cached on disk for 24h — see `lorcana-mcp cache stats` /
    `cache clear` if you suspect stale data right after a new set drops.

    Usage guidelines: reach for this first when you already have a specific
    printed card name (even with the subtitle omitted, e.g. "Mirage") — it's
    the cheapest, most precise lookup. If it returns "no card found" for a
    name you're unsure is spelled/formatted correctly (informal phrasing,
    missing dashes, a likely typo, or a bare first name meant to cover several
    printings), retry with `resolve_card` instead, which fuzzy-matches and
    will disambiguate multiple candidates rather than failing outright. For
    browsing/filtering many cards by criteria instead of one known name, use
    `search_cards`.

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
    Search the full Lorcana card pool (all sets, every printed card) by any
    combination of filters — not your collection. This is a discovery tool for
    "what cards fit X criteria", independent of what you own or have priced.

    All filters are optional and ANDed together, except colors: a card matches
    if it has ANY of the given colors, so dual-ink cards surface for either half.
    Calling with no filters at all returns the entire card pool, paginated.

    Behavior: always fetches from a live, in-process-cached copy of
    LorcanaJSON (see the "Card data APIs" reference) — never reads a local CSV,
    so results always include the newest released set. A card that has no
    Strength/Willpower/Lore (Action, Item, Location) shows "—" for those
    stats rather than being excluded. Results are grouped and displayed by ink
    color, then returned as one or more Markdown tables; when more results
    exist than `limit`, the response tells you the exact `offset` to pass next
    — call again with that offset rather than guessing pages.

    Usage guidelines: use this to browse/filter by criteria (e.g. "every
    Evasive Sapphire character costing 3 or less") — if you already have a
    specific (possibly misspelled or subtitle-less) card name in mind, use
    `resolve_card` or `lookup_card` instead, they're cheaper and more precise
    for a single known card. Results carry no ownership or price information;
    to check what you already own, cross-reference the card names against an
    enriched collection CSV yourself, or use `what_am_i_missing` /
    `find_song_synergies`'s `collection_csv` param for tools that do that
    automatically. To narrow to a specific play format's legal pool, combine
    with `set_name`, or post-filter the result against `filter_collection`'s
    format logic.

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
    Find every Character that can sing a given song — the tool for building or
    checking a Singer/song combo (e.g. the Amber/Steel Steelsong package), not
    for general card search (use `search_cards` for that).

    A character can sing a song if its printed ink cost meets the song's cost
    outright, OR it has a "Singer X" keyword with X meeting the song's cost —
    Singer lets a cheap character punch above its actual cost for singing
    purposes only (see the Steelsong package: Amber Singers unlocking
    expensive Steel songs for free). Provide either song_name (resolved the
    same fuzzy way as resolve_card, so "beauty and beast" or a slight typo
    still works) or a raw cost threshold — exactly one is required; passing
    neither, or both, returns an error message instead of guessing.

    Results are grouped: Singer-keyword characters first (the actual
    "discount" picks — highest Singer value, then cheapest actual cost),
    followed by characters that simply cost enough to sing it outright,
    cheapest first. This only tells you who *can* sing — it doesn't check
    whether that character is otherwise good (stats, other abilities) or
    whether you own enough copies to make the combo consistent unless you
    pass `collection_csv`, in which case each result is annotated with owned
    quantity so you can see the combo's real consistency at a glance.

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
    Filter an enriched collection CSV down to the cards you own that are legal
    in a specific play format — answers "which of my cards can I actually play
    in format X", grouped by ink color with owned quantities.

    Legality data comes from a live duels.ink fetch, which tracks Core EN,
    Infinity, Core ZH, and Core JA rotation. Poorcana (Common/Uncommon only,
    50-card min) is the one exception: it's derived purely from the CSV's own
    Rarity column, no external lookup, so it still works offline and always
    reflects the CSV's rarity data exactly.

    Behavior: promo rows (Set Name == "Disney Lorcana Promo Cards") are always
    excluded from Core/Infinity/regional results, not flagged as illegal —
    duels.ink's legality table is keyed by (set, number) and promos don't map
    onto that cleanly (see "Promo cards" in the reference doc). Any other row
    duels.ink doesn't recognize (usually a card from a set duels.ink hasn't
    indexed yet) is silently skipped and counted in a "rows skipped" footer —
    that's a data-lag note, not a legality verdict, so don't read a skipped
    row as "illegal". Requires the enriched CSV's columns (Set Name, Number,
    Ink, Ink Cost, Add to Quantity, etc.) — running this against the raw
    TCGPlayer export (pre-`enrich_csv`) will silently undercount or return
    nothing useful.

    Usage guidelines: run this when you want to see your full legal card pool
    for a format before hand-building a deck, or to sanity-check whether a
    deck idea is even feasible with what you own. If you want a finished
    decklist rather than just the eligible pool, use `build_deck` with
    `mode="collection"` instead — it already applies this same legality
    filter internally as part of assembling a curve-balanced list, so you
    don't need to call both.

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
    Audit an already-enriched Lorcana collection CSV against live API data and
    report exactly which fields drifted from the current source of truth —
    a correctness check on data already in the CSV, not a re-enrichment.

    Checks Ink color, Ink Cost, Card Type, Subtypes, Inkable, and stats
    (Strength / Willpower / Lore Points) for every non-promo card, one live
    API call per unique card. Promo rows are always skipped entirely (counted
    separately as "promos skipped") since there's no reliable live source to
    diff a promo printing against. Ability/Keyword text is not checked — only
    the structured fields above.

    Behavior: reports every field-level mismatch as `"csv_value" →
    "api_value"`, grouped by card. One known, harmless false-positive class:
    Subtypes differences that are purely separator/ordering (e.g.
    `"Storyborn/Ally/Toy"` vs `"Storyborn, Ally, Toy"`) — same data, different
    formatting convention, most common in newer sets. Skim for those before
    treating every reported line as a real error. A completely clean CSV
    returns a one-line "no discrepancies found" summary instead of an empty
    list.

    Usage guidelines: run this after a new set releases, after any manual CSV
    edits, or whenever enrichment output looks suspicious — not as a routine
    step after every `enrich_csv` call, since it re-fetches from the live API
    per unique card and adds real latency on a large collection. If it turns
    up genuine (non-Subtypes-formatting) discrepancies, the fix is to re-run
    `enrich_csv`, not to hand-edit the CSV — this tool only reports drift, it
    does not write any changes back to the file.

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
    Analyze a raw deck list (a list of card names, not a collection CSV) and
    return its ink curve, composition, and Core Constructed legality — the
    tool for "is this decklist actually good/legal", independent of what you
    own or can afford.

    Accepts one card per line, e.g. "4x Goofy - Musketeer" or "4 Goofy - Musketeer"
    (both "4x" and "4 " are accepted; qty is optional and defaults to 1).
    Lines starting with "#" or "//" are treated as comments and skipped.

    Reports: ink curve (1-2/3-4/5-6/7+ cost brackets), inkable vs. uninkable count,
    color split, card type split, an estimated lore-per-turn (sum of Character lore
    values), a Core Constructed legality check (60-card minimum, max 4 copies of any
    card, at most 2 ink colors), and any card names that couldn't be resolved.

    Behavior: card names are matched the same simple way as `lookup_card`
    (exact, then substring) — not fuzzy-resolved like `resolve_card` — so a
    typo'd or oddly-abbreviated name lands in the unresolved list rather than
    being guessed. Unresolved lines are excluded from every stat (curve,
    color split, lore/turn, legality counts), so a deck list with several
    unresolved names will under-report its true totals; always check that
    list before trusting the numbers. The legality check is Core Constructed
    only — it does not check rotation-group safety (whether the deck's cards
    survive the *next* rotation) or Infinity/Poorcana rules; for rotation
    safety, cross-reference the card list against `search_cards` filtered by
    set, or build fresh via `build_deck(rotation_safe=True)`.

    Usage guidelines: use this on a decklist you already have — hand-written,
    pasted from elsewhere, or `build_deck`'s output — to sanity-check curve
    and legality before playtesting or buying anything. It never touches your
    collection, so it can't tell you what's missing or what it costs; for
    that, feed the same deck list to `what_am_i_missing` instead.

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
    Compare a deck list against your collection: what you already own, what's
    missing or short, and the estimated cost to complete it — the shopping-list
    counterpart to `analyze_deck`, which checks curve/legality but never looks
    at ownership.

    Cross-references a raw deck list (same format as `analyze_deck`: `4x Card
    Name` per line) against an enriched collection CSV. Card names are matched
    the same simple exact-then-substring way as `lookup_card` (not fuzzy like
    `resolve_card`); a name that doesn't resolve is dropped from the "Already
    have"/"Missing" tallies and listed separately under an "unresolved" section
    instead of being silently skipped — check that section if the totals look
    short. For every card you're short on, price comes first from the CSV's
    own TCG Market Price if you already own at least one printing (no network
    needed); only cards you own zero copies of fall back to a live TCGPlayer
    lookup via tcgcsv.com for the cheapest printing across all sets/rarities
    (gameplay is identical regardless of rarity or art). That fallback fetch
    only fires if at least one card actually needs it, and its price data is
    cached 24h — the reported total is always a snapshot, not a quote.

    Usage guidelines: use this once you have a specific decklist in hand
    (hand-written, or `build_deck`'s output) and want to know what to buy or
    borrow before playtesting it. It doesn't check Core Constructed legality
    or curve — run `analyze_deck` on the same list for that. If instead you
    want a deck built around what you can realistically complete rather than
    checking a fixed list, use `build_deck(mode="ideal")`, which folds this
    same ownership/pricing logic into deck construction itself.

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

        priced = _price_missing_entries(short, owned_prices)
        for e in priced["entries"]:
            cost_str = f"${e['line_cost']:.2f}" if e["unit_price"] is not None else "price unknown"
            lines.append(
                f"- {e['name']} — need {e['needed']}, own {e['owned']}, "
                f"missing {e['missing']} ({cost_str})"
            )
        lines.append("")

        priced_count = len(priced["priced"])
        if priced_count:
            note = "" if priced_count == len(short) else f" ({len(short) - priced_count} card(s) had no price data)"
            lines.append(f"**Estimated cost to complete: ${priced['total_cost']:.2f}**{note}")
            if priced["used_local_price"] and priced["used_live_price"]:
                lines.append(
                    "_Prices from your collection where you already own a printing; "
                    "live TCGPlayer snapshot (tcgcsv.com) for the rest — treat as an estimate, not a quote._"
                )
            elif priced["used_live_price"]:
                lines.append("_Live TCGPlayer snapshot via tcgcsv.com — treat as an estimate, not a quote._")
            else:
                lines.append("_Prices from your own collection CSV._")
        elif priced["live_price_failed"]:
            lines.append("_Could not fetch live TCGPlayer prices — cost estimate unavailable._")
        lines.append("")

    if result["unresolved"]:
        lines.append("### Unrecognized card names")
        for u in result["unresolved"]:
            lines.append(f"- {u['qty']}x {u['name']}")

    return "\n".join(lines)


_BUILD_DECK_DISCLAIMER = (
    "_This is a heuristic curve/keyword-value deck builder — it optimizes ink curve, "
    "stat efficiency, and keyword value. It has scoped synergy awareness for named "
    "Shift/Duo Shift/Combo Shift/Potato Shift payoffs (boosted alongside their matching "
    "enablers — see \"Shift synergies built together\" above, if any landed) and, for "
    "format=\"coconut\", a hand-curated tag per Coconut card (see CLAUDE.md's \"Format "
    "Coconut\" section), but it still does not detect general multi-card combos or synergy "
    "packages (e.g. the Merlin/Mim Bounce Loop, the Steelsong package, subtype-targeted "
    "Shift like Floodborn/Madrigal/Puppy/Red Panda Shift — see CLAUDE.md's \"Key combos and "
    "synergies\"). Review the decklist before playing; swap in known synergy pieces manually._"
)


# Short, hand-written archetype hint per Coconut (keyed by the Coconut's own
# `name` field, lowercased) — presentation only, purely to help a caller
# pick between the 18 options in _coconut_card_menu. Deliberately separate
# from deckbuilder._COCONUT_SYNERGY_TAGS (which drives scoring, not prose):
# auto-generating readable phrasing from those mechanical tags produced
# awkward repeated wording for cards with several tags (e.g. Moana's three
# name_contains tags), so this is hand-tuned instead — same judgment calls
# already written up in the project CLAUDE.md's "Format Coconut" section.
_COCONUT_FOCUS: dict[str, str] = {
    "scar":            "Ally cost reduction",
    "ariel":           "Princess + Song lore burst",
    "winnie the pooh": "vanilla stat-stick value, beginner-friendly",
    "stitch":          "cheap-character swarm/flood",
    "ursula":          "Sing Together / big songs",
    "mickey mouse":    "Mickey Mouse Shift chain",
    "mufasa":          "heavy inkwell ramp into big finishers",
    "nick wilde":      "items-matter, 4-item lore burst",
    "snow white":      "Snow White + Seven Dwarfs combo",
    "donald duck":     "Boost payoff",
    "mr. incredible":  "Super challenge/removal",
    "moana":           "Moana/Heihei/Pua ramp",
    "john silver":     "Location tank",
    "robin hood":      "Robin Hood damage chain",
    "tinker bell":     "damage amplifier",
    "sisu":            "combat-stat questing (pairs with Ward/Resist)",
    "pocahontas":      "lore/challenge control",
    "dumbo":           "turn-1 activated (⟳) abilities",
}


def _coconut_card_menu(coconut_cards: list[dict], filter_colors: set[str] | None = None) -> str:
    """Markdown listing of the beta Format Coconut cards, grouped by ink,
    for build_deck(format="coconut") calls made with no coconut_card.

    filter_colors (e.g. {"Amber"}), if given, restricts the listing to only
    those ink(s) instead of showing all 18 — used when the caller passed
    ink_colors without a coconut_card yet.
    """
    scope = ""
    if filter_colors:
        coconut_cards = [c for c in coconut_cards if c.get("color") in filter_colors]
        scope = f"{'/'.join(sorted(filter_colors))} "
    lines = [
        f'**Format Coconut** needs a `coconut_card` — pick one of the {len(coconut_cards)} '
        f'{scope}beta card(s) below, then call build_deck again with format="coconut" '
        'and coconut_card="<name>".\n',
    ]
    by_color: dict[str, list[dict]] = {}
    for c in coconut_cards:
        by_color.setdefault(c.get("color", "—"), []).append(c)
    for color in sorted(by_color):
        lines.append(f"**{color}**")
        for c in sorted(by_color[color], key=lambda c: c.get("name", "")):
            subtitle = (c.get("subtitle") or "").strip('"')
            effect = next(
                (ab.get("effect", "") for ab in c.get("abilities", [])
                 if "up to 4 copies" not in ab.get("effect", "")),
                "",
            )
            focus = _COCONUT_FOCUS.get((c.get("name") or "").strip().lower(), "")
            focus_suffix = f" _(Focus: {focus})_" if focus else ""
            lines.append(f"- **{c.get('name')} - {subtitle}** — {effect}{focus_suffix}")
        lines.append("")
    if not coconut_cards:
        lines.append("_No Coconut cards found for that ink — this shouldn't happen; try again with no ink filter._")
    return "\n".join(lines)


@mcp.tool()
def build_deck(
    ink_colors: str = "",
    mode: str = "ideal",
    format: str = "core",
    collection_csv: str = "",
    rotation_safe: bool = False,
    coconut_card: str = "",
) -> str:
    """
    Automatically assemble a legal, curve-balanced ~60-card decklist for an
    ink pair and format, in one of 3 modes:

    - "collection": build only from cards you own (capped at owned quantity
      per card). If fewer than 60 legal owned cards exist, reports the
      shortfall honestly instead of padding with irrelevant fillers.
    - "ideal": build the best deck regardless of ownership. If
      collection_csv is given, also shows what you already own, what's
      missing, and the price to complete it (via tcgcsv.com).
    - "market": build the best deck ignoring any collection, and prices
      every card in it (not just the gap) via tcgcsv.com.

    This is a heuristic curve/keyword-value builder — it optimizes ink
    curve, stat efficiency, and keyword value, not multi-card combos or
    synergy packages. See the disclaimer at the bottom of every result.

    format="coconut" builds for Format Coconut (Ravensburger's multiplayer
    singleton beta, open since 2026-07-28 — rules/card pool may still
    change; see the project CLAUDE.md's "Format Coconut" section). It needs
    coconut_card, allows up to 3 ink colors (one must match the Coconut's
    own ink), has no rotation and no tracked banned list (every released
    card is treated as legal), and every card in the build is capped at 1
    copy except the Coconut's associated real character, which may run up
    to 4 — this replaces the usual max-4-of-anything rule entirely. Call
    with format="coconut" and no coconut_card to get the full list of the
    18 beta Coconuts to choose from.

    Args:
        ink_colors: Comma-separated ink color(s), e.g. "Amber,Sapphire".
                    1-2 colors for core/core_zh/core_ja/poorcana, 1-6 for
                    infinity, 1-3 for coconut (must include the Coconut
                    card's own ink — see coconut_card). May be omitted
                    entirely when format="coconut" and coconut_card is also
                    omitted — that combination just lists the 18 beta
                    Coconut cards (filtered to the given ink(s), if any) and
                    doesn't build anything yet.
        mode: "collection", "ideal", or "market".
        format: "core", "infinity", "core_zh", "core_ja", "poorcana", or "coconut".
        collection_csv: Absolute path to an enriched collection CSV. Required
                        for mode="collection"; optional for "ideal"; ignored for "market".
        rotation_safe: If True and format="core", restrict to the rotation
                       group that will still be legal after the next
                       rotation event. No-op (with a note) for other formats.
        coconut_card: Required when format="coconut" — fuzzy name of one of
                      the 18 beta Coconut cards (e.g. "Ariel", "Mickey
                      Mouse", "snow white"). Ignored for every other format.
    """
    valid_inks = {
        "amber": "Amber", "amethyst": "Amethyst", "emerald": "Emerald",
        "ruby": "Ruby", "sapphire": "Sapphire", "steel": "Steel",
    }
    valid_modes = {"collection", "ideal", "market"}
    valid_formats = {"core", "infinity", "core_zh", "core_ja", "poorcana", "coconut"}

    mode = mode.lower().strip()
    fmt = format.lower().strip()

    if mode not in valid_modes:
        return f'Unknown mode "{mode}". Valid options: {", ".join(sorted(valid_modes))}.'
    if fmt not in valid_formats:
        return f'Unknown format "{format}". Valid options: {", ".join(sorted(valid_formats))}.'

    raw_colors = [c.strip().lower() for c in ink_colors.split(",") if c.strip()]
    unknown = [c for c in raw_colors if c not in valid_inks]

    if fmt == "coconut" and not coconut_card:
        # Listing mode: ink_colors is optional here (unlike every other
        # path below) — show the full 18-card menu, or just the cards for
        # the given ink(s) if any were passed, so the caller can pick one
        # before calling again with coconut_card to actually build.
        if unknown:
            return f'Unknown ink color(s): {", ".join(unknown)}. Valid: {", ".join(sorted(valid_inks.values()))}.'
        try:
            coconut_pool = fetch_format_coconut_cards()
        except Exception as e:
            return f"Failed to fetch Format Coconut card data: {e}"
        filter_colors = {valid_inks[c] for c in raw_colors} if raw_colors else None
        return _coconut_card_menu(coconut_pool, filter_colors)

    if not raw_colors:
        return 'Provide at least one ink color, e.g. "Amber,Sapphire".'
    if unknown:
        return f'Unknown ink color(s): {", ".join(unknown)}. Valid: {", ".join(sorted(valid_inks.values()))}.'

    max_colors = 6 if fmt == "infinity" else (3 if fmt == "coconut" else 2)
    if len(raw_colors) > max_colors:
        return (
            f'{DUELS_FORMAT_LABELS.get(fmt, fmt)} allows at most {max_colors} '
            f'ink color(s), got {len(raw_colors)}.'
        )

    colors = [valid_inks[c] for c in raw_colors]
    colors_display = "/".join(colors)
    fmt_label = DUELS_FORMAT_LABELS.get(fmt, fmt.capitalize() if fmt in ("poorcana", "coconut") else fmt)

    coconut: dict | None = None
    coconut_associated_name = ""
    if fmt == "coconut":
        # coconut_card is guaranteed non-empty here — the no-coconut_card
        # case already returned the card menu above.
        try:
            coconut_pool = fetch_format_coconut_cards()
        except Exception as e:
            return f"Failed to fetch Format Coconut card data: {e}"
        coconut = resolve_coconut_card(coconut_card, coconut_pool)
        if coconut is None:
            return (
                f'Could not match "{coconut_card}" to one of the 18 beta Format Coconut '
                'cards. Call build_deck(format="coconut") with no coconut_card to see the full list.'
            )
        coconut_color = coconut.get("color", "")
        if coconut_color.lower() not in raw_colors:
            subtitle = (coconut.get("subtitle") or "").strip('"')
            return (
                f'"{coconut.get("name")} - {subtitle}" is {coconut_color} — ink_colors must '
                f'include {coconut_color} (one of your chosen colors has to match the Coconut\'s ink).'
            )
        coconut_associated_name = coconut.get("associatedCardName", "")

    if mode == "collection" and not collection_csv:
        return 'mode="collection" requires collection_csv (absolute path to your enriched collection CSV).'

    owned_counts: dict[str, int] = {}
    owned_prices: dict[str, float] = {}
    if collection_csv and mode != "market":
        try:
            owned_counts, owned_prices = _load_collection_csv(collection_csv)
        except FileNotFoundError as e:
            return f"Error: {e}"

    try:
        lj_cards = fetch_lorcana_json()
    except Exception as e:
        return f"Failed to fetch card data: {e}"

    duels_lookup = None
    if fmt not in ("poorcana", "coconut"):
        try:
            duels_lookup = build_duels_lookup(fetch_duels_ink())
        except Exception as e:
            return f"Failed to fetch duels.ink legality data: {e}"

    rotation_note = ""
    rotation_safe_codes = None
    if rotation_safe:
        if fmt == "core":
            try:
                rotation_safe_codes = rotation_safe_set_codes(fetch_lorcana_sets())
            except Exception as e:
                return f"Failed to fetch rotation data: {e}"
            if not rotation_safe_codes:
                return "Could not determine a rotation-safe set pool from current rotation data."
        else:
            rotation_note = f"_rotation_safe is a Core-only concept — ignored for {fmt_label}._\n"

    pool = build_candidate_pool(
        lj_cards, colors, fmt,
        duels_lookup=duels_lookup,
        rotation_safe_codes=rotation_safe_codes,
        owned_counts=owned_counts if mode == "collection" else None,
    )

    if not pool:
        owned_note = " from your collection" if mode == "collection" else ""
        return f"No {colors_display} cards are legal in {fmt_label}{owned_note}."

    def _max_copies(card: dict) -> int:
        # Coconut is singleton except the Coconut's own associated character,
        # which may run up to 4 — this replaces the normal "always up to 4"
        # rule entirely rather than adding to it.
        cap = 1 if (fmt == "coconut" and card.get("fullName") != coconut_associated_name) else 4
        if mode == "collection":
            cap = min(cap, owned_counts.get((card.get("fullName") or "").lower(), 0))
        return cap

    max_copies_fn = _max_copies if (mode == "collection" or fmt == "coconut") else None
    synergy_bonus, synergy_info = compute_shift_synergy(pool)
    if coconut is not None:
        for name, bonus in compute_coconut_synergy(pool, coconut).items():
            synergy_bonus[name] = max(synergy_bonus.get(name, 0.0), bonus)
    picks = allocate_deck(
        pool, max_copies_fn=max_copies_fn,
        synergy_bonus=synergy_bonus, synergy_info=synergy_info,
    )
    if coconut is not None:
        picks = ensure_coconut_associated_card(picks, pool, coconut_associated_name, max_copies_fn)
    total_cards = sum(qty for _, qty in picks)

    if not picks:
        return f"Could not assemble any legal cards for {colors_display} {fmt_label}."

    sorted_picks = sorted(picks, key=lambda p: (p[0].get("cost") or 0, p[0].get("fullName", "")))

    lines = [f"**Built deck** — {colors_display} · {fmt_label} · {mode} mode\n"]

    if coconut is not None:
        subtitle = (coconut.get("subtitle") or "").strip('"')
        lines.append(f"### Coconut: {coconut.get('name')} - {subtitle} ({coconut.get('color')})")
        for ability in coconut.get("abilities", []):
            effect = ability.get("effect", "")
            if effect and "up to 4 copies" not in effect:
                lines.append(f"- {effect}")
        lines.append(
            f"- Up to 4 copies of **{coconut_associated_name}** allowed; "
            "every other card in this deck is singleton (1 copy max)."
        )
        lines.append(
            "- Format Coconut plays to 25 lore (not 20) and is designed for 3-4 players. "
            "Open beta since 2026-07-28 — rules and the Coconut card pool may still change."
        )
        lines.append("")

    if rotation_note:
        lines.append(rotation_note)

    lines.append(f"### Decklist ({total_cards} cards)")
    lines.append("| Cost | Card | Type | Qty |")
    lines.append("|------|------|------|-----|")
    for card, qty in sorted_picks:
        ctype = card.get("type", "—")
        if ctype == "Action" and "Song" in (card.get("subtypes") or []):
            ctype = "Action - Song"
        lines.append(f"| {card.get('cost', '—')} | {card.get('fullName', '—')} | {ctype} | {qty} |")
    lines.append("")

    lines.append("### duels.ink import")
    lines.append("```")
    lines.extend(f"{qty}x {card.get('fullName', '')}" for card, qty in sorted_picks)
    lines.append("```")
    lines.append("")

    picked_names = {card.get("fullName") for card, _ in sorted_picks}
    landed_synergies = [
        s for s in synergy_info
        if s["payoff"] in picked_names and any(e in picked_names for e in s["enablers_found"])
    ]
    if landed_synergies:
        lines.append("### Shift synergies built together")
        for s in landed_synergies:
            enablers_in = [e for e in s["enablers_found"] if e in picked_names]
            lines.append(f"- **{s['payoff']}** ← {', '.join(enablers_in)}")
        lines.append("")

    stats = summarize_picks(sorted_picks)
    curve = stats["curve"]
    lines.append("### Stats")
    lines.append(
        f"- Curve: 1-2⬡ {curve['1-2']} · 3-4⬡ {curve['3-4']} · "
        f"5-6⬡ {curve['5-6']} · 7+⬡ {curve['7+']}"
    )
    lines.append(f"- Inkable: {stats['inkable_count']} · Uninkable: {stats['uninkable_count']}")
    lines.append(f"- Colors: {', '.join(f'{k} {v}' for k, v in stats['color_counts'].items())}")
    lines.append(f"- Types: {', '.join(f'{k} {v}' for k, v in stats['type_counts'].items())}")
    lines.append(f"- Estimated lore/turn (all questors): {stats['lore_per_turn']}")

    format_min_cards = 50 if fmt == "poorcana" else 60
    lines.append(
        f"- {'OK' if total_cards >= format_min_cards else 'SHORT'}: "
        f"minimum {format_min_cards} cards ({total_cards} built)"
    )
    lines.append(
        f"- {'OK' if len(colors) <= max_colors else 'OVER'}: "
        f"at most {max_colors} ink color(s) ({len(colors)} used)"
    )
    if fmt == "coconut":
        over_singleton = [
            card.get("fullName", "") for card, qty in sorted_picks
            if card.get("fullName") != coconut_associated_name and qty > 1
        ]
        lines.append(
            f"- {'OK' if not over_singleton else 'OVER'}: singleton respected "
            f"(only {coconut_associated_name} may exceed 1 copy)"
        )
    lines.append("")

    if mode == "collection":
        lines.append("### Collection coverage")
        if total_cards >= 60:
            lines.append(f"All {total_cards} cards drawn from your collection — nothing to buy.")
        else:
            lines.append(
                f"Built {total_cards}/60 cards — no more legal, owned {colors_display} cards "
                f"available for {fmt_label}. Buy more copies of cards above, or other legal "
                "cards, to reach 60."
            )
        lines.append("")

    elif mode == "ideal":
        if collection_csv:
            # Built directly from sorted_picks rather than deck.what_am_i_missing() —
            # we already have the exact resolved card dicts, so there's no fuzzy
            # name resolution to redo (unlike the what_am_i_missing tool, which has
            # to fuzzy-resolve a user's raw pasted decklist text).
            diff_entries = [
                {
                    "name": card.get("fullName", ""),
                    "needed": qty,
                    "owned": owned_counts.get((card.get("fullName") or "").lower(), 0),
                    "missing": max(qty - owned_counts.get((card.get("fullName") or "").lower(), 0), 0),
                }
                for card, qty in sorted_picks
            ]
            have_fully = [e for e in diff_entries if e["missing"] == 0]
            short = [e for e in diff_entries if e["missing"] > 0]

            lines.append("### Ownership & cost to complete")
            lines.append(f"Already own {len(have_fully)}/{len(diff_entries)} unique cards in full.")
            if short:
                priced = _price_missing_entries(short, owned_prices)
                lines.append(f"\n**Missing or short ({len(short)}):**")
                for e in priced["entries"]:
                    cost_str = f"${e['line_cost']:.2f}" if e["unit_price"] is not None else "price unknown"
                    lines.append(
                        f"- {e['name']} — need {e['needed']}, own {e['owned']}, "
                        f"missing {e['missing']} ({cost_str})"
                    )
                priced_count = len(priced["priced"])
                if priced_count:
                    note = "" if priced_count == len(short) else (
                        f" ({len(short) - priced_count} card(s) had no price data)"
                    )
                    lines.append(f"\n**Estimated cost to complete: ${priced['total_cost']:.2f}**{note}")
                    if priced["used_local_price"] and priced["used_live_price"]:
                        lines.append(
                            "_Prices from your collection where you already own a printing; "
                            "live TCGPlayer snapshot (tcgcsv.com) for the rest — "
                            "treat as an estimate, not a quote._"
                        )
                    elif priced["used_live_price"]:
                        lines.append(
                            "_Live TCGPlayer snapshot via tcgcsv.com — treat as an estimate, not a quote._"
                        )
                    else:
                        lines.append("_Prices from your own collection CSV._")
                elif priced["live_price_failed"]:
                    lines.append("_Could not fetch live TCGPlayer prices — cost estimate unavailable._")
            else:
                lines.append("You already own every card in this deck.")
            lines.append("")
        else:
            lines.append(
                "_Pass collection_csv to see what you already own and the price to complete this deck._\n"
            )

    else:  # market
        if collection_csv:
            lines.append(
                "_collection_csv was ignored — market mode prices the full deck "
                "regardless of ownership._\n"
            )
        entries = [
            {"name": card.get("fullName", ""), "needed": qty, "owned": 0, "missing": qty}
            for card, qty in sorted_picks
        ]
        priced = _price_missing_entries(entries, {})
        lines.append("### Full deck cost")
        if priced["priced"]:
            note = "" if not priced["unpriced"] else f" ({len(priced['unpriced'])} card(s) had no price data)"
            lines.append(f"**Estimated total: ${priced['total_cost']:.2f}**{note}")
            lines.append(
                "_Live TCGPlayer snapshot via tcgcsv.com, cheapest printing per card — "
                "treat as an estimate, not a quote._"
            )
            if priced["unpriced"]:
                lines.append("\nNo price data: " + ", ".join(e["name"] for e in priced["unpriced"]))
        elif priced["live_price_failed"]:
            lines.append("_Could not fetch live TCGPlayer prices — cost estimate unavailable._")
        else:
            lines.append("_No price data available for any card in this deck._")
        lines.append("")

    lines.append("---")
    lines.append(_BUILD_DECK_DISCLAIMER)

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
