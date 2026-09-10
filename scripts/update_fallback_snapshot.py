#!/usr/bin/env python3
"""Refresh the bundled LorcanaJSON fallback snapshot.

`lorcana_mcp/data/allcards_fallback.json.gz` is a gzipped copy of
https://lorcanajson.org/files/current/en/allCards.json — the offline safety
net used by `api._fetch_lorcana_json_full()` when the live fetch fails.

It only matters when LorcanaJSON / the network is down, and only needs to be
"recent enough that a degraded session still knows about the current set", so
refreshing it once per release (or whenever a new set drops) is plenty.

Usage:  python scripts/update_fallback_snapshot.py
"""
from __future__ import annotations

import gzip
import json
import sys
import urllib.request
from pathlib import Path

URL = "https://lorcanajson.org/files/current/en/allCards.json"
DEST = Path(__file__).resolve().parent.parent / "lorcana_mcp" / "data" / "allcards_fallback.json.gz"


def main() -> int:
    print(f"Fetching {URL} ...")
    raw = urllib.request.urlopen(URL, timeout=120).read()
    data = json.loads(raw)
    meta = data.get("metadata", {})
    n_cards = len(data.get("cards", []))
    if n_cards < 2000 or "sets" not in data:
        print(f"Refusing to write: payload looks wrong ({n_cards} cards).", file=sys.stderr)
        return 1

    DEST.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(DEST, "wb", compresslevel=9) as f:
        f.write(raw)

    size_mb = DEST.stat().st_size / 1_048_576
    print(
        f"Wrote {DEST.relative_to(DEST.parent.parent.parent)} "
        f"({n_cards} cards, {len(data['sets'])} sets, "
        f"generated {meta.get('generatedOn', '?')}, {size_mb:.2f} MB gzipped)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
