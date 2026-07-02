# Changelog

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
