# lorcana-mcp

[![PyPI](https://img.shields.io/pypi/v/lorcana-mcp)](https://pypi.org/project/lorcana-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/lorcana-mcp)](https://pypi.org/project/lorcana-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-listed-blue)](https://registry.modelcontextprotocol.io/servers/io.github.IcaroBichir/lorcana)
[![mcp.so](https://img.shields.io/badge/mcp.so-lorcana--mcp-orange)](https://mcp.so/server/lorcana-mcp)

MCP server that connects Claude to Disney Lorcana card data. Export your collection from TCGPlayer, hand it to Claude, and get it fully enriched with ink cost, stats, keywords, abilities, and format legality — plus a ready-to-import file for [dreamborn.ink](https://dreamborn.ink).

---

## The simple version

**What it does:** plug this into Claude and it becomes a Disney Lorcana expert that knows your actual collection — no more tab-switching between TCGPlayer, dreamborn.ink, and a wiki.

Once it's connected, you can just talk to Claude like:

- 🗂️ **"Enrich my collection at ~/Downloads/export.csv"** — turns a bare TCGPlayer export into a full card database (cost, stats, keywords, abilities) plus a file ready to import into dreamborn.ink
- 🔎 **"What's that card, big pete?"** — finds cards even if you don't remember the exact name or spelling
- 🎴 **"Show me cheap Evasive characters in Amber"** — searches the entire card pool by color, cost, keyword, rarity, whatever
- 🎵 **"Who can sing Be Our Guest for free?"** — finds the best Singer combos for a song
- 📋 **"Is this deck legal? 4x Goofy - Musketeer, 4x..."** — checks curve, colors, and tournament legality of any deck list
- 💰 **"What am I missing to finish this deck, and what would it cost?"** — compares a deck list to your collection and prices the gap with live market data
- ✅ **"Is my collection data still accurate?"** — audits your CSV against live card data and flags anything stale

Everything reads from public card APIs plus your own exported CSV — no account, no login, nothing to configure.

### Get it running in under a minute

**1. Install it:**
```bash
pip install lorcana-mcp
```

**2. Connect it to Claude:**
```bash
claude mcp add lorcana -- lorcana-mcp serve
```
*(Using Claude Desktop instead? See [Add to Claude](#add-to-claude) below.)*

**3. Talk to it:**
Export your collection from TCGPlayer (**My Account → My Collection → Export**), then just say:
> "Enrich my collection at /path/to/your/export.csv"

That's it — Claude does the rest. Everything below is reference detail for when you want more control.

---

## Tools

Nine tools are available in Claude once the server is running:

| Tool                  | What it does |
|-----------------------|---|
| `enrich_csv`          | Enriches a raw TCGPlayer export with Ink, Cost, Type, Subtypes, STR/WIL/Lore, Inkable, Keywords, and Abilities. Writes an enriched CSV and a dreamborn.ink-ready import file next to the input. `refresh_prices=True` also refreshes TCG Market Price with a live tcgcsv.com lookup. |
| `lookup_card`         | Looks up any card by name. Returns full stats, ability text, format legality, and card image URL. |
| `resolve_card`        | Fuzzy-resolves an informal, misspelled, or subtitle-less card name (e.g. "goofy musketeer", "elsa"). Returns a single confident match, a ranked top-3 to disambiguate, or nothing found. |
| `search_cards`        | Searches the full card pool by color, type, rarity, set, cost range, keyword, ability text, or subtype — with pagination. |
| `find_song_synergies` | Finds every character that can sing a given song (or a raw cost threshold), split into Singer-keyword discount picks and plain cost-qualifiers. Optionally flags which ones you own. |
| `filter_collection`   | Filters your collection to cards legal in a given format: `core`, `infinity`, `core_zh`, `core_ja`, or `poorcana`. |
| `audit_csv`           | Compares an enriched collection against live API data and reports any stale or wrong fields. |
| `analyze_deck`        | Analyzes a raw deck list (`4x Card Name` per line) for ink curve, inkable split, color split, card types, estimated lore/turn, and Core Constructed legality (60-card min, max 4 copies, ≤2 ink colors). |
| `what_am_i_missing`   | Compares a deck list against your collection: what you already own, what's missing or short, and a live TCGPlayer cost estimate (via tcgcsv.com) to complete it. |

---

## Listed on

| Directory | Link |
|---|---|
| MCP Registry (official) | [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io/servers/io.github.IcaroBichir/lorcana) |
| mcp.so | [mcp.so/server/lorcana-mcp](https://mcp.so/server/lorcana-mcp) |
| PyPI | [pypi.org/project/lorcana-mcp](https://pypi.org/project/lorcana-mcp/) |

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

To refresh prices on demand without re-exporting from TCGPlayer:

> "Re-enrich my collection at /Users/me/lorcana/enriched_Lorcana_063026.csv and refresh prices"

`refresh_prices=True` overwrites each row's TCG Market Price with a live tcgcsv.com lookup for that exact printing — useful when an enriched CSV's prices are stale.

### Look up a card

> "Look up Mirage - Super Recruiter"

> "What are the stats on Alma Madrigal - Heart of the Family?"

> "Is Will o' the Wisp legal in Core?"

Returns: ink color, cost, type, subtypes, STR/WIL/Lore, inkable status, keywords, full ability text, format legality, and a card image URL.

### Resolve an informal or misspelled card name

> "Find the card 'goofy musketeer'"

> "What's that card 'big pete'?"

> "Look up 'elsa' — not sure which version"

Tokenizes the query and scores it against every card's name and subtitle, tolerating missing dashes, missing subtitles, word order, and minor typos. Returns full detail for a single confident match, a ranked top-3 with confidence scores when several cards are plausible (e.g. a bare name matching every printing of that character), or nothing if the query doesn't resemble any card.

### Search the full card pool

> "Show me all Evasive characters in Amethyst that cost 3 or less"

> "Find Toy characters"

> "Search for Rare Steel cards from Wilds Unknown"

Filters: ink color(s), card type (`Character` / `Action` / `Item` / `Location` / `Song`), rarity, set name, cost range, keyword, ability text substring, and subtype — all combinable, plus pagination (`offset` + `limit`). Results are grouped by ink color and sorted by cost.

### Find who can sing a song

> "Which characters can sing Be Our Guest?"

> "Show me Amber characters that can sing a cost-7 song"

> "Who can sing Friends on the Other Side, and which ones do I own?" (pass your enriched collection CSV)

A character can sing a song if its printed cost meets the song's cost outright, or it has a matching `Singer X` keyword — Singer lets a cheap character punch above its actual cost for singing purposes only. Results split into Singer-keyword "discount" picks (highest Singer value, then cheapest actual cost) and plain cost-qualifiers (cheapest first). Pass `collection_csv` to flag ownership.

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

### Analyze a deck list

> "Analyze this deck: 4x Goofy - Musketeer, 4x Elsa - Spirit of Winter, ..." (paste a full list, one card per line)

Accepts `4x Card Name` or `4 Card Name`; quantity defaults to 1 if omitted. Lines starting with `#` or `//` are treated as comments.

Returns: ink curve (1-2/3-4/5-6/7+ cost brackets), inkable vs. uninkable count, color split, card type split, an estimated lore-per-turn (sum of Character lore values), a Core Constructed legality check (60-card minimum, max 4 copies of any card, at most 2 ink colors), and any card names that couldn't be resolved.

### Check what a deck list is missing

> "What am I missing to build this deck?" (paste the deck list and point me at your collection CSV)

> "How much would it cost to finish this Amber/Steel list?"

Same deck list format as `analyze_deck`. Cross-references against your enriched collection CSV, then splits results into cards you already have enough of and cards you're missing or short on. For cards you're short on (own at least one printing already), the cost comes straight from the CSV's own TCG Market Price column — no network call needed. Only cards you own zero copies of fall back to a live TCGPlayer lookup via [tcgcsv.com](https://tcgcsv.com) (cheapest printing across all sets/rarities, since gameplay is identical), and even then only if at least one card actually needs it. Live price data is cached for 24h, so the first call that needs it takes a bit longer while it warms up.

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

205 tests, no network calls required.

---

## License

MIT — see [LICENSE](LICENSE).

---

## 🤖 CLAUDE READ THIS

If you're an AI agent (Claude or otherwise) with this MCP server connected, read this section before making tool calls. It's the fast path to using this correctly.

### Which tool to call

| The user wants... | Call... | Not... |
|---|---|---|
| Their raw TCGPlayer export turned into a real database | `enrich_csv` | — |
| To bring stale prices up to date without re-exporting | `enrich_csv` with `refresh_prices=True` | manually curling TCGPlayer |
| Stats on a card whose exact name they gave you | `lookup_card` | — |
| A card by an informal, partial, or misspelled name (e.g. "goofy musketeer", "big pete", "elsa") | `resolve_card` | `lookup_card` — it only does plain substring matching and will falsely report "not found" for anything without exact dashes/spelling |
| To browse/filter the whole card pool (by color, type, rarity, set, cost, keyword, ability text, subtype) | `search_cards` | — |
| Singer combos / "who can sing this song for free" | `find_song_synergies` | — |
| Format legality of their collection (Core, Infinity, Poorcana, etc.) | `filter_collection` | — |
| To sanity-check an enriched CSV against live data | `audit_csv` | — |
| A decklist rated for curve, color balance, and legality | `analyze_deck` | — |
| "What do I need to buy to finish this deck, and how much?" | `what_am_i_missing` | — |

### Hard rules

1. **Always pass absolute paths** for `csv_path` / `input_path` / `collection_csv`. Relative paths resolve against the server process's cwd, not the user's — this fails silently or points at the wrong file. If you don't have an absolute path, ask the user or find the file first.
2. **Default to `resolve_card` over `lookup_card`** unless the user gave you a name you're confident is exact and correctly spelled. When in doubt, `resolve_card` is strictly more forgiving and costs nothing extra.
3. **Never hand-roll price lookups.** `find_song_synergies` and `what_am_i_missing` already call tcgcsv.com internally with 24h caching and cheapest-printing logic. Don't `curl` TCGPlayer or scrape prices yourself.
4. **Gameplay is identical across printings** (base, Enchanted, Epic, promo — same name, cost, stats, abilities). Every price-aware tool already picks the cheapest printing automatically; don't second-guess a suspiciously low result, and don't treat rarity as a gameplay signal.
5. **If a user says data looks wrong or stale**, suggest `lorcana-mcp cache clear` before assuming a tool is broken — card and price data is cached 24h.
6. **Ambiguous tool output is a feature, not an error.** `resolve_card` and `find_song_synergies` can return a ranked "did you mean" list instead of a single answer — present it to the user rather than guessing which one they meant.

### Known gotchas (found the hard way — see CHANGELOG.md)

- **`Product ID` (CSV column 1) ≠ `TCGplayer Id` (column 2).** Only `Product ID` matches external pricing APIs (LorcanaJSON's `externalLinks.tcgPlayerId`, tcgcsv.com's `productId`). Column 2 is an unrelated secondary ID — if you're ever writing custom code against this data, matching on it silently returns zero results.
- **Promo cards are skipped in the dreamborn.ink output** — their numbering doesn't correspond to TCGPlayer's. Tell the user to add promos manually via dreamborn.ink's search after importing.
- **Duplicate-looking rows in search results are printings, not bugs** — `search_cards` and `find_song_synergies` already deduplicate alt-art/Enchanted reprints by name internally, so don't be surprised the count is lower than you'd expect from a raw card list.

### If you're modifying this codebase

- Run `pytest` before and after any change — 205 tests, all network-free (external calls are mocked).
- Code layout: pure/testable logic lives in `api.py` (card data + fuzzy matching + pricing), `deck.py` (deck list parsing/analysis), and `enricher.py` (CSV pipeline). `server.py` only wraps those as MCP tools and formats output — keep it that way rather than putting logic directly in tool functions.
- A release touches four files together: `pyproject.toml` (version), `server.json` (version, for the MCP Registry), `CHANGELOG.md` (entry), and this README if tool behavior changed. Check `git log` for the pattern.
- Publishing is a separate, explicit step (`python -m build`, `twine upload`, `mcp-publisher publish`) — never assume a version bump in `pyproject.toml` means it's live on PyPI or the registry. Check before telling a user a feature is "available."

<!-- mcp-name: io.github.IcaroBichir/lorcana -->
