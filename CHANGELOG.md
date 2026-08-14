# Changelog

## 1.0.0 — 2026-08-14

First stable release. All 10 tools (`enrich_csv`, `lookup_card`, `resolve_card`, `search_cards`, `find_song_synergies`, `filter_collection`, `audit_csv`, `analyze_deck`, `what_am_i_missing`, `build_deck`) have been in active daily use managing a real collection since v0.1.0, backed by a 278-test suite that now runs in CI on Python 3.11–3.13 for every PR (added in 0.2.8). `Development Status` in `pyproject.toml` moves from Alpha to Production/Stable to match. No functional or breaking changes from 0.2.10 — this release is the docstring rewrite below plus the version/maturity bump.

Rewrote the tool docstrings for `search_cards`, `filter_collection`, `audit_csv`, `lookup_card`, `enrich_csv`, `analyze_deck`, `what_am_i_missing`, and `find_song_synergies` — prompted by Glama's per-tool quality scores (glama.ai grades each tool's description on Behavior, Conciseness, Completeness, Parameters, Purpose, and Usage Guidelines), which had `search_cards` at 2/5 on Usage Guidelines and `filter_collection`/`audit_csv` at 3/5 on Behavior, well below their other dimensions; the next five scorers (`analyze_deck`, `enrich_csv`, `lookup_card` at 4.6/5.0, `what_am_i_missing` at 4.6/5.0, `find_song_synergies` at 4.7/5.0) were still capped at 4/5 on Usage Guidelines and, for some, Conciseness/Completeness.

Every rewritten docstring now explicitly states, where applicable: what's fetched live vs. cached and for how long, silent edge-case behavior (e.g. `lookup_card` silently returning the most recent printing on a cross-set name collision, `filter_collection` excluding promos from legality results rather than marking them illegal, `audit_csv`'s known harmless Subtypes-separator false positives, `what_am_i_missing`'s unresolved-name section, `find_song_synergies` erroring rather than guessing when both/neither of `song_name`/`cost` are given), which upstream tool's output format is required as input, and — the recurring Usage Guidelines gap — when to reach for this tool over a sibling tool that looks similar (`search_cards` vs. `lookup_card`/`resolve_card`; `filter_collection` vs. `build_deck(mode="collection")`; `analyze_deck` vs. `what_am_i_missing` vs. `build_deck(mode="ideal")`; `find_song_synergies` vs. `search_cards`). No behavior changes — docstrings only, all 278 tests still pass unmodified.

## 0.2.9 — 2026-08-12

Fix a broken link in README.md: the MCP Registry badge and "Listed on" table both pointed to `https://registry.modelcontextprotocol.io/servers/io.github.IcaroBichir/lorcana`, which 404s — that domain has no per-server webpage at all, only raw JSON API routes (`/v0/servers/...`). Replaced with the registry's actual homepage, pre-filled via its `?q=` search param: `https://registry.modelcontextprotocol.io/?q=lorcana`, confirmed working. Also found and fixed the underlying cause of why this went unnoticed: the MCP Registry listing itself was silently 2 releases stale (still serving 0.2.6 while PyPI was on 0.2.8) because the registry's CLI auth token had expired and nothing re-published after — re-authenticated and republished during this release.

## 0.2.8 — 2026-08-12

No code changes. Adds a CI workflow (`.github/workflows/tests.yml`) that runs the full 278-test suite on Python 3.11, 3.12, and 3.13 for every pull request and every push to `main` — previously all 278 tests only ran manually, which is exactly how the `mcp` 2.0.0 break fixed in 0.2.7 went unnoticed until a live Glama build failed. README updated with a Tests badge and a corrected test count (was showing a stale "205 tests").

## 0.2.7 — 2026-08-12

Fix a fresh-install crash: `pyproject.toml` pinned `mcp[cli]>=1.0.0` with no upper bound. `mcp` 2.0.0 released today (2026-08-12) and removed `mcp.server.fastmcp` entirely, renaming the class to `MCPServer` at `mcp.server.mcpserver.MCPServer`. `lorcana_mcp/server.py` still imports `from mcp.server.fastmcp import FastMCP`, so any environment resolving dependencies fresh — `pip install lorcana-mcp`, `uv sync` with no lockfile, Glama's Docker-based server builds — picked up `mcp` 2.0.0 and crashed with `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` on startup. Existing installs with `mcp` already pinned to a 1.x version in their own environment were unaffected.

Found while debugging a failing Glama admin build/test for this server (see `glama.json`, added in 0.2.6-adjacent work) — the container's `uv sync` had no lockfile to pin against and resolved straight to the new major version.

Fix: pin `mcp[cli]>=1.0.0,<2.0.0` in `pyproject.toml`. No code changes — migrating to `mcp` 2.0.0's `MCPServer` API is a separate, deliberately deferred task (v2.0.0 released same-day as this fix; needs a full audit of what else changed beyond the `FastMCP` rename, plus retesting all 10 tools, before treating it as safe).

## 0.2.6 — 2026-08-10

Metadata-only release, no code changes. Tightened the `description` field in `pyproject.toml` (PyPI) and `server.json` (MCP Registry / aggregator listings like PulseMCP and Claude Skills Hub) — the old copy ("Connect Claude to Disney Lorcana card data: enrich, search, and analyze decks.") undersold the tool by only mentioning enrichment. New copy calls out the actual breadth (TCGPlayer export enrichment, card lookup/search, automated deck building, collection auditing against live data) to differentiate from thinner competing Lorcana MCP listings.

## 0.2.5 — 2026-08-10

Add scoped Shift-family synergy detection to `build_deck`, closing the gap 0.2.4 (the keyword-scoring fix) didn't: even scored correctly, a Shift/Duo Shift/Combo Shift payoff was still just one card competing on raw score against the whole pool, with nothing biasing its named enabler(s) toward inclusion. Confirmed empirically against a real Emerald/Sapphire collection build around Mickey Mouse & Minnie Mouse - Adventuring Duo (Duo Shift) — post-0.2.4, it *still* built zero Mickey Mouse or Minnie Mouse-named characters.

New in `deckbuilder.py`:
- `_shift_target_names(card)` — for a name-targeted Shift-family card, returns the required enabler name(s) and whether they're an AND ("all", currently only Duo Shift) or OR ("any", Combo Shift and plain Shift's compound "X or Y" cards) requirement. Notably needs **no reminder-text parsing** for Shift/Duo Shift/Combo Shift: verified against every such card in the live pool (311+ Shift, 4 Combo Shift, 2 Duo Shift) that the required name(s) are always already encoded in LorcanaJSON's own `name` field — solo name shifts onto itself, a compound name joined by `" & "` or `" 'n' "` shifts onto its parts. This sidesteps punctuation edge cases a regex would trip on (e.g. "Dr. Facilier", "Fix-It Felix, Jr."). Potato Shift is the one case genuinely parsed from reminder text, since the item name isn't reflected in the character's own name. Floodborn/Madrigal/Puppy/Red Panda Shift (subtype-targeted, not name-targeted) and Universal Shift (no target) are explicitly out of scope.
- `compute_shift_synergy(pool)` — finds every satisfiable named-Shift synergy in a candidate pool (a required name with zero pool matches gets no bonus — never rewards an unreachable combo) and returns a per-card score bonus plus a description list, both threaded through `allocate_deck`.
- `_enforce_all_relation_synergies(...)` — the score bonus alone turned out to be enough for "any"-relation synergies but *not* reliably enough for "all"-relation ones (Duo Shift): in a deep pool, one required name's enablers can clear the bar on boosted score while the other still loses to unrelated cards, leaving a picked Duo Shift payoff that can never actually be played for its 0-cost Shift. This runs as a final pass, guaranteeing at least 1 copy of an enabler for every required name once a payoff has landed, trimming the current weakest pick to hold the deck at 60.

`build_deck`'s output now includes a "Shift synergies built together" section listing which detected synergies actually made it into the final decklist (payoff + at least one real enabler both present) — not just what was theoretically detected in the pool.

Re-verified end-to-end against two different real collections after the fix: the Mickey/Minnie build now includes the Duo card plus real Mickey Mouse and Minnie Mouse enablers; a separate Ruby/Steel collection correctly landed Dash Parr & Violet Parr - Super Siblings (Combo Shift) together with both its Dash Parr and Violet Parr enabler lines, with no regression to the existing curve/type-cap/backfill behavior. Added 15 new tests (`TestShiftTargetNames`, `TestComputeShiftSynergy`, `TestAllocateDeckSynergyGuarantee`) — full suite: 278/278 passing.

Docstrings/disclaimers updated in both `deckbuilder.py` and `server.py`'s `_BUILD_DECK_DISCLAIMER` to describe this scoped capability accurately — the tool is still not a general synergy engine (Merlin/Mim Bounce Loop, Steelsong package, and subtype-targeted Shift remain undetected).

## 0.2.4 — 2026-08-10

Fix `build_deck`'s heuristic scoring silently giving 0.0 keyword bonus to every named Shift variant. `_KEYWORD_SCORE` did an exact-match dict lookup keyed on `"shift"`, but LorcanaJSON stores each variant under its own literal keyword name — `"Duo Shift"`, `"Combo Shift"`, `"Potato Shift"`, etc. — not `"Shift"`. Set 13 alone introduced 7 of these (Combo Shift, Duo Shift, Potato Shift, Madrigal Shift, Floodborn Shift, Temporary Shift, Temporary Red Panda Shift), on top of the 311 plain-Shift cards already in the pool across every set. Every one of those 7 was scoring as if it had no keyword at all.

Found via a real `build_deck` run for an Emerald/Sapphire collection deck built around Mickey Mouse & Minnie Mouse - Adventuring Duo (Duo Shift 0, no other keywords) — the tool included zero Mickey Mouse or Minnie Mouse-named characters, because the Duo card itself scored *below* a plain vanilla same-cost body (2.857 vs. 3.0), and nothing biased the enabler characters toward inclusion either. Confirmed against the real card: post-fix it scores 4.357, correctly above the vanilla comparison.

`character_score()` and `item_location_score()` now call a new `_keyword_score()` helper: exact dict match first, then a substring fallback on `"shift"` so any current or future named variant scores the same as plain Shift without needing a new dict entry per name. Deliberately a substring fallback rather than a hardcoded list of the 7 known names — self-updates for whatever Set 14+ calls its next Shift variant.

This only fixes the keyword-value bug (the payoff card's own score). It does **not** add synergy-aware bias toward including matching-named enabler characters when a Shift/Duo Shift/Combo Shift payoff is in the pool — `build_deck` remains a curve/keyword-value heuristic, not a synergy engine, per its own docstring. For a named-payoff deck like this, still hand-build or hand-tune around the payoff (see the parent repo's `NANDA_emerald+sapphire_v1.md` for how this was done manually).

## 0.2.3 — 2026-07-30

Re-add promo→dreamborn resolution, this time verified against a **real dreamborn.ink CSV export** (promos-only, ~186 rows, user-provided) rather than the card-browser display that fooled v0.2.1. The export revealed the actual bulk-import schema for promos: `Set Number` is the plain LJ set code of whichever set the promo drop is tied to (not always the newest set — e.g. `P3` promos are tied to set 12, `P4`/`PD1` to set 13, the `CC1` Tinker Bell to set 9), and `Card Number` is the **full `"N/Series"` string as one field** (e.g. `"57/P3"`) rather than split into a separate series column — that splitting is what broke v0.2.1.

`PROMO_DREAMBORN_ROW` in `api.py` now covers all 144 promo names in the export that map to exactly one print. A further 17 names have more than one promo print sharing a name (e.g. two different "Woody - Jungle Guide" promos, `53/P3` and `54/P3`) — `PROMO_DREAMBORN_ROW_BY_NUMBER` disambiguates these using TCGPlayer's own promo `Number` column, which — checked across every one of these — equals the numeric prefix of dreamborn's `Card Number` for the same physical card. Two names (`Maleficent - Monstrous Dragon`, `Mickey Mouse - Brave Little Tailor`) have two prints that *also* share that numeric prefix and genuinely can't be disambiguated from TCGPlayer data alone; deliberately left out, so they fall through to the manual-add list rather than guessing.

`resolve_promo_dreamborn_row(name, number)` also strips a trailing `"(...)"` suffix from `name` before lookup (e.g. `"Woody - Jungle Guide (Store Championship Participant)"` → `"Woody - Jungle Guide"`), matching this repo's own documented promo-name convention (parent `CLAUDE.md`'s "tips for future data tasks" note about `Product Name` suffixes).

Resolved 18 of 19 promos in the reference collection (same result as v0.2.1's — but this time actually correct). The 19th, Maleficent - Exultant Spellcaster, is confirmed absent from dreamborn's real export too, not just its card browser — still correctly falls through to manual-add.

## 0.2.2 — 2026-07-30

**Revert 0.2.1's promo→dreamborn mapping — it silently corrupted the dreamborn import.** Confirmed against a real dreamborn.ink bulk-CSV import attempt: dreamborn's importer only accepts a numeric `Set Number`. Given a promo series string (e.g. `"P3"`), it doesn't reject the row — it silently falls back to resolving the bare `Card Number` against the newest real set (Attack of the Vine!, set 13)'s own numbering. So `P3,57` (meant as Buzz Lightyear - Space Ranger) resolved to Set 13 card #57, which is actually **Morph - Little Imitator** — a wrong, unrelated card. Same failure for every other promo in the map (`P3,42` → Lumpy - Hunny Druid instead of Stitch; `P3,49` → Ming Lee instead of Lenny; `P3,50` → Merida instead of Zipper; `P3,51` → Mrs. Incredible instead of Will o' the Wisp; `P4,9`/`10`/`11`/`12`/`13`/`14` and `PD1,3`/`5`/`6`/`8` all happened to line up with Set 13's own numbering for a *different* card at that slot each time). Had the import been confirmed, this would have added the wrong cards at fabricated quantities to a real collection.

Removed `PROMO_DREAMBORN_ID` / `PROMO_DREAMBORN_ID_BY_PRINTING` / `resolve_promo_dreamborn_id` from `api.py` and reverted `_build_dreamborn_rows()` in `enricher.py` to the pre-0.2.1 behavior: every promo row goes to the manual-add list, none are guessed into a fabricated CSV row. The hand-verified name→series/number research from 0.2.1 is preserved as reference in the parent repo's `CLAUDE.md` ("Promo cards" section) since the underlying card identification work was correct — only the leap from "dreamborn's card-browser display numbering" to "dreamborn's bulk-import Set Number" was wrong. Re-enabling this needs dreamborn's actual promo import format confirmed first (likely an internal DB id, not anything derivable from the card browser UI) — not attempted again without that.

Lesson: verifying a card ID against dreamborn's *display* (card browser, search results) is not the same as verifying it against dreamborn's *bulk import parser* — they can silently disagree, and the importer doesn't error on a bad row, it happily resolves to something else. A "did the promo rows write to the CSV" check isn't sufficient; the file needs an actual import dry-run before being called safe.

## 0.2.1 — 2026-07-30

Add promo-card resolution to dreamborn output. Previously **every** promo row was skipped in `dreamborn_*.csv` and dumped into a "add manually" list, because dreamborn.ink groups promos into their own numbered series (`P1`, `P2`, `P3`, `P4`, `PD1`, `PD2`, `C1`, `C2`, `CC1`, `D23`, `DIS`, ...) instead of using TCGPlayer's flat promo `Number` column — and the same bare number can be a completely different card in a different series (e.g. "11" is Tinker Bell in `P3` but Randall Boggs in `P4`).

Added `PROMO_DREAMBORN_ID` and `PROMO_DREAMBORN_ID_BY_PRINTING` in `api.py` — a hand-verified name (+ printing, where two promos share a name) → `(series, number)` lookup, checked card-by-card against dreamborn.ink's own card browser and detail pages (never guessed from price or bare number alone — an earlier guess based on price for Minnie Mouse - Pirate Lookout would have picked the wrong one of two same-named candidates; the real match came from an exact Cost/Str/Wil/Lore/ability-text comparison). `_build_dreamborn_rows()` in `enricher.py` now emits a normal dreamborn row (`Set Number` = series string, `Card Number` = number, same foil/normal `Variant` logic as retail sets) for any promo with a known mapping, and only falls through to the manual-add list for genuinely unmapped promos.

Resolved 18 of 19 promos in the reference collection this way. The 19th (Maleficent - Exultant Spellcaster) isn't in dreamborn's catalog at all yet — likely because it's a brand-new Attack of the Vine! (Set 13, released 2026-07-24) era promo dreamborn hasn't added — so it correctly still falls through to manual-add.

This map only covers promos actually seen in this collection so far; extend `PROMO_DREAMBORN_ID` / `PROMO_DREAMBORN_ID_BY_PRINTING` by hand as new ones turn up (there's no API for dreamborn's internal promo series — resolving a new one still means searching dreamborn's card browser and reading the detail page).

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
