from __future__ import annotations

import csv

from mcp.server.fastmcp import FastMCP

from .api import (
    search_card, abilities_from_lj, LJCODE_TO_SETNAME, SETNAME_TO_LJCODE,
    fetch_duels_ink, build_duels_lookup, DUELS_FORMAT_LABELS,
)
from .enricher import enrich_csv as _enrich_csv, audit_csv as _audit_csv, _num_int
from .deck import analyze_deck as _analyze_deck

mcp = FastMCP(
    "Lorcana",
    instructions=(
        "Use these tools to enrich Disney Lorcana TCG collection exports from TCGPlayer, "
        "look up individual card data, filter a collection by play format, "
        "audit an enriched collection for stale or wrong card data, "
        "or analyze a deck list for curve, composition, and format legality."
    ),
)


@mcp.tool()
def enrich_csv(input_path: str, cache_path: str = "") -> str:
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
    """
    try:
        result = _enrich_csv(input_path, cache_path=cache_path or None)
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

    return (
        f"Enrichment complete.\n\n"
        f"Output files:\n"
        f"  Enriched:  {result['enriched_path']}\n"
        f"  Dreamborn: {result['dreamborn_path']}\n\n"
        f"Stats:\n"
        f"  Total rows:   {result['total_rows']}\n"
        f"  Cache hits:   {result['cache_hits']}\n"
        f"  API fetches:  {result['api_fetches']}\n"
        f"  Dreamborn rows written: {result['dreamborn_rows']}\n\n"
        f"Fill rates:\n{fill_lines}"
        f"{unmatched_block}"
        f"{promo_block}"
    )


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
        f"**{card.get('fullName', name)}**",
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
