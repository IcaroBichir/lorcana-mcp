# lorcana-mcp

[![PyPI](https://img.shields.io/pypi/v/lorcana-mcp)](https://pypi.org/project/lorcana-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/lorcana-mcp)](https://pypi.org/project/lorcana-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MCP server that connects Claude to Disney Lorcana card data. Export your collection from TCGPlayer, hand it to Claude, and get it fully enriched with ink cost, stats, keywords, abilities, and format legality — plus a ready-to-import file for [dreamborn.ink](https://dreamborn.ink).

---

## Tools

Four tools are available in Claude once the server is running:

| Tool                | What it does |
|---------------------|---|
| `enrich_csv`        | Enriches a raw TCGPlayer export with Ink, Cost, Type, Subtypes, STR/WIL/Lore, Inkable, Keywords, and Abilities. Writes an enriched CSV and a dreamborn.ink-ready import file next to the input. |
| `lookup_card`       | Looks up any card by name. Returns full stats, ability text, format legality, and card image URL. |
| `filter_collection` | Filters your collection to cards legal in a given format: `core`, `infinity`, `core_zh`, `core_ja`, or `poorcana`. |
| `audit_csv`         | Compares an enriched collection against live API data and reports any stale or wrong fields. |

---

## Install

```bash
pip install lorcana-mcp
```

Or from source:

```bash
git clone https://github.com/IcaroBichir/lorcana-mcp
cd lorcana-mcp
pip install .
```

---

## Add to Claude

### Claude Code (CLI)

```bash
claude mcp add lorcana -- lorcana-mcp serve
```

### Claude Desktop

Find `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`) and add:

```json
{
  "mcpServers": {
    "lorcana": {
      "command": "lorcana-mcp",
      "args": ["serve"]
    }
  }
}
```

Restart Claude Desktop after saving.

### Cursor / other MCP clients

Any client that supports stdio MCP servers can use `lorcana-mcp serve` as the command.

---

## Usage

Once the server is connected, just talk to Claude naturally. No slash commands needed.

### Enrich a collection

Export your collection from TCGPlayer → **My Collection → Export CSV**, then:

> "Enrich my collection at /Users/me/Downloads/Lorcana_063026.csv"

Claude will fetch card data from the APIs and write two files next to your input:
- `enriched_Lorcana_063026.csv` — your collection with 10 new columns
- `dreamborn_Lorcana_063026.csv` — ready to import at dreamborn.ink

On re-runs, pass the previous enriched file as a cache to skip already-seen cards:

> "Enrich /Users/me/Downloads/Lorcana_new.csv using /Users/me/lorcana/enriched_Lorcana_old.csv as cache"

### Look up a card

> "Look up Mirage - Super Recruiter"

> "What are the stats on Alma Madrigal - Heart of the Family?"

> "Is Will o' the Wisp legal in Core?"

Returns: ink color, cost, type, subtypes, STR/WIL/Lore, inkable status, keywords, full ability text, format legality, and a card image URL.

### Filter your collection by format

> "Which of my cards are legal in Core Constructed?"

> "Show me my Infinity-legal cards grouped by ink color"

> "What Poorcana-legal cards do I have in Amber?"

Valid formats: `core`, `infinity`, `core_zh`, `core_ja`, `poorcana`

Poorcana filtering uses the Rarity column in your enriched CSV (Common + Uncommon only) — no API call needed.

Core/Infinity/regional legality comes from [duels.ink](https://duels.ink), which tracks the current rotation for each region.

### Audit an existing enriched file

> "Audit my collection at /Users/me/lorcana/enriched_collection.csv"

Useful after a new set releases or if a card's data looks wrong. Compares every non-promo card against live API data and reports field-by-field discrepancies.

---

## Enriched columns

The enricher adds these 10 columns to the raw TCGPlayer export:

| Column | Description |
|---|---|
| Ink | Ink color(s) — dual-ink cards show both, e.g. `Amber, Steel` |
| Ink Cost | Numeric cost to play (1–12) |
| Card Type | Character / Action / Action - Song / Item / Location |
| Subtypes | e.g. `Storyborn, Hero, Toy` |
| Strength | ⚔ stat — blank for Actions, Items |
| Willpower | 🛡 stat — blank for Actions, Items |
| Lore Points | ◆ gained per quest — blank for Actions, Items |
| Inkable | Yes / No |
| Keywords | Comma-separated: `Evasive`, `Shift 3`, `Singer 5`, `Resist +1`, etc. |
| Abilities | Full card text, pipe-separated lines |

---

## Data sources

| Source | Sets | Used for |
|---|---|---|
| [LorcanaJSON](https://lorcanajson.org) | All sets (1–14+) | Primary source for Set 12+; fallback for 1–11 |
| [lorcana-api.com](https://lorcana-api.com) | Sets 1–11 | Preferred for Sets 1–11 (richer body text) |
| [duels.ink](https://duels.ink) | All sets | Format legality, card images |

Card data is cached locally for 24 hours at `~/.cache/lorcana-mcp/`. Manage the cache with the CLI:

```bash
lorcana-mcp cache stats   # show entry count, expiry status, and file size
lorcana-mcp cache clear   # delete all cached responses (fresh fetch on next use)
```

---

## Supported sets

| Set | Name |
|---|---|
| 1 | The First Chapter |
| 2 | Rise of the Floodborn |
| 3 | Into the Inklands |
| 4 | Ursula's Return |
| 5 | Shimmering Skies |
| 6 | Azurite Sea |
| 7 | Archazia's Island |
| 8 | Reign of Jafar |
| 9 | Fabled |
| 10 | Whispers in the Well |
| 11 | Winterspell |
| 12 | Wilds Unknown |
| 13 | Attack of the Vine! |
| 14 | Hyperia City |

New sets are picked up automatically via LorcanaJSON as long as the set name is added to the internal mapping. Open an issue if a new set isn't resolving.

---

## TCGPlayer export format

Go to [TCGPlayer](https://www.tcgplayer.com) → **My Account → My Collection → Export**. The raw file has columns like Product Name, Set Name, Number, Rarity, Condition, Printing, and `Add to Quantity` (this is the real owned-quantity column — `Total Quantity` is always blank in exports).

> **Promo cards:** skipped in the dreamborn output because dreamborn uses internal promo set numbers that don't match TCGPlayer's format. Add them manually via dreamborn.ink's card search after importing the rest.

---

## CLI reference

```
lorcana-mcp --version
lorcana-mcp serve          Start the MCP server (stdio)
lorcana-mcp cache stats    Show cache info
lorcana-mcp cache clear    Clear cached API responses
```

---

## Development

```bash
git clone https://github.com/IcaroBichir/lorcana-mcp
cd lorcana-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

74 tests, no network calls required.

---

## License

MIT — see [LICENSE](LICENSE).
