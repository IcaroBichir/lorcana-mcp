# Changelog

## 0.2.0 — 2026-07-09

Add `build_deck` tool: automatically assembles a legal, curve-balanced ~60-card decklist for an ink pair and format, in one of 3 modes — `collection` (only cards you own, copies capped at owned quantity, honest shortfall reporting instead of padding), `ideal` (best deck regardless of ownership, priced to complete against a collection CSV if given), or `market` (best deck, fully priced via tcgcsv.com, ownership ignored). It's a heuristic curve/keyword-value builder (ink-curve targets and per-card scoring from stat efficiency + keyword value), not a synergy/combo detector — every result says so.

New supporting pieces: `lorcana_mcp/deckbuilder.py` (candidate-pool assembly, scoring, curve-target apportionment, greedy allocation, stats summary), `rotation_safe_set_codes()` (dynamically computes the newest Core-legal rotation group from LorcanaJSON's per-set metadata instead of a hardcoded "rotationGroup >= 3" — self-updates as rotation groups shift), and `filter_by_format()`/`lj_card_format_legal()` in `api.py` (format-legality filtering applied directly to the full card pool, not just a collection CSV row).

Found and fixed two real bugs while building this:
- `filter_cards()`'s ink-color filter uses ANY-match semantics (correct for search, since a dual-ink card should surface under either color) — but candidate-pool assembly for deck building needs SUBSET semantics (every color on the card must be within the chosen ink pair, or a Ruby/Emerald dual-ink card would wrongly be admitted into a Ruby/Amber deck). `build_candidate_pool()` implements its own subset check rather than reusing `filter_cards`.
- The soft type-composition caps (Character≤24, Action≤16, Item≤8, Location≤4, from this repo's own composition guideline ranges) sum to only 52 — less than a 60-card deck — so treating them as hard caps made a full 60-card deck structurally unreachable whenever a color pair was thin on non-Character cards. Fixed by making the caps apply only to the primary curve-bucket-filling pass; a backfill pass ignores them (keeping only the 4-copy-per-card cap) so the real deck size is always reached when the pool allows it.

Also found mid-implementation: `build_deck`'s stats block originally called the existing `deck.analyze_deck()` on its own generated decklist text, which re-resolves every card name via fuzzy matching against the full live card pool — pure overhead (and a real network hit) for names we'd already resolved exactly while building the deck. Replaced with `deckbuilder.summarize_picks()`, which computes the same curve/inkable/color/type/lore stats directly from the already-resolved `(card, qty)` picks. Cut a synthetic full-pool build from ~13s to well under 1s (warm cache). The `ideal`-mode ownership diff has the same fix — computed directly from `sorted_picks` instead of round-tripping through `deck.what_am_i_missing()`'s fuzzy resolution.

## 0.1.9 — 2026-07-09

Add `refresh_prices` flag to `enrich_csv`: when set, overwrites each row's TCG Market Price with a live tcgcsv.com lookup for that exact printing (matched via the row's own Product ID), instead of leaving whatever the raw TCGPlayer export had at download time. Lets an old enriched CSV's prices be brought current without re-exporting from TCGPlayer. Report output now includes a "Prices refreshed: N/Total" line when used.

Found and fixed a real bug while building this: initially matched on the CSV's "TCGplayer Id" column, which is a secondary listing ID unrelated to tcgcsv.com's `productId` — it silently refreshed 0/391 rows against the real collection. The correct match key is "Product ID" (TCGPlayer's actual product ID, the same one LorcanaJSON's `externalLinks.tcgPlayerId` uses). Added a regression test that deliberately sets a non-matching "TCGplayer Id" to guard against this recurring.

## 0.1.8 — 2026-07-09

Add `what_am_i_missing` tool: cross-references a deck list against an enriched collection CSV, splitting cards into "already have" and "missing or short." For cards you're short on, the cost comes straight from the CSV's own TCG Market Price column (already there, no network call needed) — only cards you own zero copies of fall back to a live TCGPlayer lookup via tcgcsv.com (cheapest printing across all sets, cached 24h), and only if at least one card actually needs it.

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
