# Changelog

## 0.1.8 — 2026-07-09

Add `what_am_i_missing` tool: cross-references a deck list against an enriched collection CSV, splitting cards into "already have" and "missing or short," then fetches live TCGPlayer prices from tcgcsv.com for anything missing (cheapest printing across all sets, cached 24h) and sums them into a completion cost estimate.

Also fixes a latent bug found while integrating tcgcsv.com: the shared `_fetch()` HTTP helper sent the default `Python-urllib/x.y` User-Agent, which tcgcsv.com rejects with a 401. Added a `lorcana-mcp/1.0` UA to all outgoing requests.

## 0.1.7 — 2026-07-08

Add `find_song_synergies` tool: given a song (fuzzy-resolved by name) or a raw cost threshold, lists every Character that can sing it — either by printed cost alone or via a Singer X keyword — split into a Singer "discount" group (highest Singer value, then cheapest actual cost) and a plain cost-qualifiers group (cheapest first). Supports an ink color filter and an optional `collection_csv` to flag owned copies.

Also fixes a latent duplicate-row bug in `search_cards`/`filter_cards`: `allCards.json` lists each printing (base, Enchanted, reprints, etc.) as a separate entry, so ~580 card names had 2+ near-identical rows in results. Added `dedupe_by_full_name()` and applied it to both `filter_cards` and the new `find_song_singers`, since these variants are gameplay-identical per this repo's own documentation.

## 0.1.6 — 2026-07-08

Add `resolve_card` tool and rework the underlying search engine (`score_candidates` in `api.py`) to fuzzy-match card names instead of a plain substring check. Tokenizes the query and scores it against each card's name (2x weight) and subtitle (1x weight), tolerating missing dashes ("goofy musketeer"), missing subtitles ("elsa" — ranks all versions by set recency), word order, and typos (5+ letter fuzzy-ratio matching). `resolve_card` classifies the result as a single resolved match, a ranked top-3 for ambiguous queries, or not-found. `lookup_card`'s and `analyze_deck`'s existing `search_card` calls benefit automatically since it now uses the same scorer under the hood.

## 0.1.5 — 2026-07-08

Add `search_cards` tool: search the full LorcanaJSON card pool by ink color(s), card type (including Song), rarity, set name, cost range, keyword, ability text substring, and subtype, with pagination. Results grouped by ink and sorted by cost.

## 0.1.4 — 2026-07-08

Add `analyze_deck` tool: given a raw deck list (one card per line, `4x Card Name` format), reports ink curve (1-2/3-4/5-6/7+ brackets), inkable vs. uninkable count, color split (dual-ink cards tracked as combined keys), card type split, estimated lore-per-turn, a Core Constructed legality check (60-card minimum, max 4 copies, ≤2 ink colors), and any unresolved card names.

## 0.1.3 — 2026-07-02

Add MCP Registry and mcp.so badges and "Listed on" directory table to README.

## 0.1.2 — 2026-07-02

Fix MCP Registry server name case: `io.github.IcaroBichir/lorcana` (GitHub auth is case-sensitive).

## 0.1.1 — 2026-07-02

Added MCP Registry verification token to README for official registry listing.

## 0.1.0 — 2026-07-02

Initial release.

### Tools
- **`enrich_csv`** — enriches a raw TCGPlayer collection CSV with card data (Ink, Cost, Type, Subtypes, STR/WIL/Lore, Inkable, Keywords, Abilities) fetched from LorcanaJSON and lorcana-api.com; also produces a dreamborn.ink-ready import CSV
- **`lookup_card`** — looks up any card by name; returns full stats, abilities, format legality, and card image URL (supplemented by duels.ink)
- **`filter_collection`** — filters an enriched collection CSV to cards legal in a given format: `core`, `infinity`, `core_zh`, `core_ja`, or `poorcana`
- **`audit_csv`** — compares an enriched collection against live API data and reports stale or wrong fields

### CLI
- `lorcana-mcp serve` — starts the MCP server (stdio transport)
- `lorcana-mcp cache stats` — shows local cache size and expiry status
- `lorcana-mcp cache clear` — clears cached API responses

### Data sources
- **LorcanaJSON** — primary source for all sets including Set 12+ (Wilds Unknown, Attack of the Vine!, etc.)
- **lorcana-api.com** — preferred for Sets 1–11 (richer body text)
- **duels.ink** — supplemental source for format legality and card images

### Notes
- Card data cached locally for 24h at `~/.cache/lorcana-mcp/`
- Disambiguation logic handles allCards.json duplicate card numbers (Wilds Unknown #43–55)
- Cache key includes card name to prevent stale data reuse across re-runs
