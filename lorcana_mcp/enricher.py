"""CSV enrichment pipeline, dreamborn generation, and collection audit."""
from __future__ import annotations

import csv
from pathlib import Path

from .api import (
    ENRICH_FIELDS, OUT_COLS, SETNAME_TO_LJCODE, PROMO_SETCODE, LJ_ONLY_SETS,
    enrich_from_api, enrich_from_lj, pick_lj_card, load_all_data,
)

_BLANK = ("", "", "", "", "", "", "", "", "", "")

SET_NUM = {name: int(code) for name, code in SETNAME_TO_LJCODE.items()}

# ── Utilities ──────────────────────────────────────────────────────────────────

def _num_str(number_field: str) -> str:
    try:
        return number_field.split("/")[0].strip()
    except AttributeError:
        return ""


def _num_int(number_field: str) -> int | None:
    try:
        return int(number_field.split("/")[0].strip())
    except (ValueError, AttributeError):
        return None

# ── Cache loader (from previous enriched CSV) ──────────────────────────────────

def load_csv_cache(path: str) -> dict:
    """Load enriched fields from an existing CSV, keyed by (Set Name, num, Product Name)."""
    cache: dict = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            num = _num_str(row.get("Number", ""))
            key = (row.get("Set Name", "").strip(), num, row.get("Product Name", "").strip())
            if key not in cache:
                cache[key] = tuple(row.get(col, "") for col in ENRICH_FIELDS)
    return cache

# ── Enrichment ─────────────────────────────────────────────────────────────────

def enrich_csv(
    input_path: str,
    output_dir: str | None = None,
    cache_path: str | None = None,
) -> dict:
    """
    Enrich a raw TCGPlayer CSV export with card data from both APIs.

    Returns a dict with keys: enriched_path, dreamborn_path, total_rows,
    cache_hits, api_fetches, unmatched, fill_rates.
    """
    inp = Path(input_path)
    out_dir = Path(output_dir) if output_dir else inp.parent
    enriched_out = out_dir / f"enriched_{inp.name}"
    dreamborn_out = out_dir / f"dreamborn_{inp.name}"

    cache: dict = {}
    if cache_path:
        cache = load_csv_cache(cache_path)

    with open(inp, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Determine which rows need fresh API data
    cache_hits = 0
    needs_api = False
    for row in rows:
        key = (row["Set Name"].strip(), _num_str(row["Number"]), row["Product Name"].strip())
        if key in cache:
            cache_hits += 1
        else:
            needs_api = True

    api_lookup, lj_lookup, lj_cards = load_all_data() if needs_api else ({}, {}, [])

    unmatched: list[str] = []
    out_rows: list[dict] = []

    for row in rows:
        set_name = row["Set Name"].strip()
        num_s = _num_str(row["Number"])
        num_i = _num_int(row["Number"])
        name = row["Product Name"].strip()
        key = (set_name, num_s, name)

        if key in cache:
            enriched = cache[key]
        else:
            enriched = _resolve(row, set_name, num_s, num_i, name,
                                api_lookup, lj_lookup, lj_cards, unmatched)
            cache[key] = enriched

        (ink, cost, ctype, subtypes, strength, willpower, lore, inkable, keywords, abilities) = enriched

        out = {k: row.get(k, "") for k in OUT_COLS}
        out.update({
            "Ink": ink, "Ink Cost": cost, "Card Type": ctype, "Subtypes": subtypes,
            "Strength": "" if strength in ("", "None") else strength,
            "Willpower": "" if willpower in ("", "None") else willpower,
            "Lore Points": "" if lore in ("", "None") else lore,
            "Inkable": inkable, "Keywords": keywords, "Abilities": abilities,
        })
        out_rows.append(out)

    with open(enriched_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLS)
        writer.writeheader()
        writer.writerows(out_rows)

    dreamborn_rows = _build_dreamborn_rows(out_rows)
    with open(dreamborn_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Set Number", "Card Number", "Variant", "Count"])
        writer.writeheader()
        writer.writerows(dreamborn_rows["rows"])

    fill = _fill_rates(out_rows)

    return {
        "enriched_path": str(enriched_out),
        "dreamborn_path": str(dreamborn_out),
        "total_rows": len(out_rows),
        "cache_hits": cache_hits,
        "api_fetches": len(out_rows) - cache_hits,
        "unmatched": unmatched,
        "dreamborn_rows": len(dreamborn_rows["rows"]),
        "promo_skipped": dreamborn_rows["promos"],
        "fill_rates": fill,
    }


def _resolve(
    row: dict, set_name: str, num_s: str, num_i: int | None,
    name: str, api_lookup: dict, lj_lookup: dict, lj_cards: list, unmatched: list,
) -> tuple:
    if set_name == "Disney Lorcana Promo Cards":
        return _resolve_promo(name, num_i, lj_lookup, lj_cards, unmatched)

    if set_name in LJ_ONLY_SETS or set_name not in SET_NUM:
        return _resolve_lj_only(set_name, num_s, num_i, name, lj_lookup, unmatched)

    # Sets 1–11: prefer lorcana-api.com, fall back to LorcanaJSON
    api_card = api_lookup.get((set_name, num_i)) if num_i is not None else None
    if api_card:
        return enrich_from_api(api_card)

    return _resolve_lj_only(set_name, num_s, num_i, name, lj_lookup, unmatched)


def _resolve_promo(
    name: str, num_i: int | None,
    lj_lookup: dict, lj_cards: list, unmatched: list,
) -> tuple:
    sc = PROMO_SETCODE.get(name)
    lj_card = None
    if sc and num_i is not None:
        candidates = lj_lookup.get((sc, num_i), [])
        candidate = pick_lj_card(candidates, name)
        if candidate and candidate.get("fullName", "").lower() == name.lower():
            lj_card = candidate
    if not lj_card:
        matches = [c for c in lj_cards if c.get("fullName", "").lower() == name.lower()]
        lj_card = matches[0] if matches else None
    if lj_card:
        return enrich_from_lj(lj_card)
    unmatched.append(f"[Promo] {name}")
    return _BLANK


def _resolve_lj_only(
    set_name: str, num_s: str, num_i: int | None,
    name: str, lj_lookup: dict, unmatched: list,
) -> tuple:
    lj_code = SETNAME_TO_LJCODE.get(set_name)
    candidates = lj_lookup.get((lj_code, num_i), []) if lj_code and num_i is not None else []
    lj_card = pick_lj_card(candidates, name)
    if lj_card:
        return enrich_from_lj(lj_card)
    unmatched.append(f"[{set_name} #{num_s}] {name}")
    return _BLANK


def _fill_rates(rows: list[dict]) -> dict:
    total = len(rows)
    if not total:
        return {}
    return {
        field: f"{sum(1 for r in rows if r.get(field, '').strip())}/{total}"
        for field in ENRICH_FIELDS
    }

# ── Dreamborn generation ───────────────────────────────────────────────────────

def _build_dreamborn_rows(enriched_rows: list[dict]) -> dict:
    rows = []
    promos = []
    for row in enriched_rows:
        set_name = row.get("Set Name", "").strip()
        num_str = row.get("Number", "").strip().split("/")[0].strip()
        printing = row.get("Printing", "").strip()
        count_str = row.get("Add to Quantity", "").strip()

        try:
            count = int(float(count_str)) if count_str else 0
        except ValueError:
            count = 0

        if set_name == "Disney Lorcana Promo Cards":
            if count > 0:
                promos.append({"num": num_str, "name": row.get("Product Name", ""),
                               "printing": printing, "count": count})
            continue

        set_num = SET_NUM.get(set_name)
        if set_num is None or count <= 0:
            continue
        try:
            card_num = int(num_str)
        except ValueError:
            continue

        rows.append({
            "Set Number": set_num,
            "Card Number": card_num,
            "Variant": "foil" if printing.lower() in ("holofoil", "cold foil") else "normal",
            "Count": count,
        })
    return {"rows": rows, "promos": promos}

# ── Audit ──────────────────────────────────────────────────────────────────────

def audit_csv(csv_path: str) -> dict:
    """
    Compare an enriched CSV against live API data and return discrepancies.

    Returns a dict with keys: reviewed, skipped_promos, issues (list of dicts).
    Each issue has: card, field, csv_value, api_value.
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    api_lookup, lj_lookup, lj_cards = load_all_data()

    issues: list[dict] = []
    reviewed = 0
    skipped = 0

    for row in rows:
        set_name = row.get("Set Name", "").strip()
        num_s = _num_str(row.get("Number", ""))
        num_i = _num_int(row.get("Number", ""))
        name = row.get("Product Name", "").strip()

        if set_name == "Disney Lorcana Promo Cards":
            skipped += 1
            continue

        reviewed += 1

        # Get ground truth
        truth_tuple = _resolve(
            row, set_name, num_s, num_i, name,
            api_lookup, lj_lookup, lj_cards, [],
        )
        if truth_tuple == _BLANK:
            continue

        truth = dict(zip(ENRICH_FIELDS, truth_tuple))
        card_label = f"[{set_name} #{num_s}] {name}"

        for field in ("Ink", "Ink Cost", "Card Type", "Subtypes", "Inkable",
                      "Strength", "Willpower", "Lore Points"):
            csv_val = row.get(field, "").strip()
            api_val = truth.get(field, "").strip()
            if csv_val and api_val and csv_val != api_val:
                issues.append({
                    "card": card_label,
                    "field": field,
                    "csv_value": csv_val,
                    "api_value": api_val,
                })

    return {"reviewed": reviewed, "skipped_promos": skipped, "issues": issues}
