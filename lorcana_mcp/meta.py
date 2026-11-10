"""Static, hand-maintained snapshot of the Core Constructed metagame.

Unlike every other data source in this package (LorcanaJSON, lorcana-api.com,
duels.ink, tcgcsv.com), there is no live, structured, freely-fetchable feed
for competitive metagame share or tournament results — inkDecks.com and
lorcana.gg publish this as HTML pages, not an API, and tournament decklists
circulate as social-media images. So unlike card data, which this package
always fetches live, this module is a versioned snapshot: accurate as of
META_SNAPSHOT_DATE, bundled into the package at release time, and only as
fresh as the last release that updated it. `get_meta` is explicit about this
in its own output — treat every call as "what we knew as of this date", not
a live read, and check the URLs in META_SOURCES for anything newer.

Updating this snapshot (e.g. after a new tournament) is a manual edit to the
constants below, followed by a normal package release — it does not require
new fetch logic, since there's nothing live to fetch from.
"""

from __future__ import annotations

from .tournaments import TOURNAMENTS, format_event, list_events

META_SNAPSHOT_DATE = "2026-11-10"

META_SOURCES = [
    "inkDecks.com Core Constructed meta report, November 2026 (Hyperia City era): "
    "Emerald/Steel Evasive #1 at ~20.7%, then Amber/Emerald Circle and Amber/Sapphire "
    "Detectives. Only the top-3 ranking and the #1 share were captured",
    "@onemorelore.au Instagram \"Meta Decks — Hyperia City\" weekly roundup (8 lists, "
    "captured 2026-11-10); full decklists via get_meta(event=\"onemorelore\")",
    "ROK local tournament, 2026-10-26 (6 lists, winner only); full decklists via "
    "get_meta(event=\"rok\")",
    "inkDecks.com (metagame breakdown, tier lists)",
    "lorcana.gg (tier list, rotation tracker)",
    "Disney Lorcana North American Championship 2026, Disneyland Resort, Anaheim CA "
    "(official Top 16 decklist posts + Day 1/2 metagame breakdown graphics)",
    "Disney Lorcana Challenge — Asia Championship 2026, Hong Kong Disneyland Hotel "
    "(@gaetancall Instagram Top 8 decklist post) — standard EN Core Constructed",
    "Disney Lorcana Championship Qualifier (CCQ) — St. Augustine FL "
    "(@gaetancall Instagram champion/finalist decklist post) — EN Core Constructed",
    "Disney Lorcana Challenge Japan 2026 / DLC Kobe (Autumn), Kobe JP "
    "(@gaetancall Instagram Top 8 decklist post) — Core JA / Asia rotation, a "
    "separate metagame from EN Core; full decklists via get_meta(event=\"kobe\")",
    "Disney Lorcana North American Championship 2026 Top 8 "
    "(@gaetancall Instagram official Top 8 decklist post — supersedes an earlier "
    "community-sourced pre-release transcription on any conflict)",
    "Disney Lorcana Challenge — Europe Championship 2026, Disneyland Paris "
    "(@disneylorcana official Instagram Top 16 decklist carousel posts) — EN Core Constructed",
]

# Core Constructed ink-pair tier list. `meta_share` is a rough, mixed-source
# figure (some from general metagame trackers, some from the championship
# results below) — treat it as directional, not a precise stat.
# `verified_recent_event` marks the pairs seen in a Hyperia City-era (Set 14+)
# result or meta report; older comment follows. Originally it marked pairs re-checked against a real
# recent championship result (NAC 2026, Asia Championship 2026, and/or the
# FL CCQ — see RECENT_TOURNAMENTS below); every other row is un-refreshed
# June-2026-era data that predates those events and may itself be stale.
CORE_TIER_LIST: list[dict] = [
    {"pair": ('Emerald', 'Steel'), "archetype": 'Evasive Tempo (Darkwing Duck / Elinor)', "tier": 'S',
     "meta_share": "#1 in inkDecks' November 2026 Core report (~20.7%). Also the pre-Set-14 powerhouse (69% of the NAC 2026 Top 16)",
     "style": 'Cheap Evasive bodies (Pegasus, White Rabbit, Mushu, Vixey) + Elinor - Renowned Diplomat + Gaetan Moliere draw + Angela/Francine Resist + Strength of a Raging Fire',
     "verified_recent_event": True},
    {"pair": ('Amber', 'Emerald'), "archetype": 'Circle of Life Songs', "tier": 'S',
     "meta_share": "#2 in inkDecks' November 2026 report (share not captured). In the onemorelore roundup. Was also the Europe Championship's biggest pair (7 of 16), as a different, Aurora/Pocahontas shell",
     "style": 'Singers (Angel - Siren Singer, Ursula - Vanessa, Max Goof - Karaoke Star) + Circle of Life + Malicious, Mean, and Scary -> Prince Phillip wipe + Milo Thatch',
     "verified_recent_event": True},
    {"pair": ('Amber', 'Sapphire'), "archetype": 'Zootopia Detectives', "tier": 'A',
     "meta_share": "#3 in inkDecks' November 2026 report. In the onemorelore roundup and the ROK field",
     "style": 'All-character Detective tribal: five Judy Hopps printings, Nick Wilde Support, Elisa Maza, Fangmeyer, Gaston - Superior Archer removal',
     "verified_recent_event": True},
    {"pair": ('Emerald', 'Sapphire'), "archetype": 'Mickey & Minnie Go-Wide', "tier": 'A',
     "meta_share": 'Won the ROK local (2 of 6 lists). In the onemorelore roundup',
     "style": 'Minnie/Mickey 1-3 drops + Mickey & Minnie - Adventuring Duo + Ward top end (Scuttle - Birdbrained, Winifred, Hades - Meticulous Schemer) + Hades - Infernal Schemer',
     "verified_recent_event": True},
    {"pair": ('Amethyst', 'Emerald'), "archetype": 'Retro Discard / Don Karnage', "tier": 'A',
     "meta_share": 'Won the Asia Championship + FL CCQ before Set 14. Its Hyperia City version is in the onemorelore roundup',
     "style": 'Don Karnage Shift + Aladdin & Genie / Tod draw + Retro Evolution Device + Malicious, Mean, and Scary -> Prince Phillip wipe',
     "verified_recent_event": True},
    {"pair": ('Emerald', 'Ruby'), "archetype": 'Discard-Matters Control (Olaf / Leviathan)', "tier": 'A',
     "meta_share": "New with Set 14: in the onemorelore roundup and the ROK field ('Rg retro')",
     "style": 'Rivera Family Photo / The Torn Corner discard engine + Olaf - Snowman of Action + The Leviathan + Lyle Tiberius Rourke + Prince Phillip wipe',
     "verified_recent_event": True},
    {"pair": ('Amber', 'Amethyst'), "archetype": 'Madrigal Midrange', "tier": 'A',
     "meta_share": "Won NAC 2026 and went 6 of 8 at Asia before Set 14. Still in the onemorelore roundup, but not in inkDecks' November top 3",
     "style": 'Grandmother Willow/Hamm curve-accel + Luisa Madrigal Shift chain + Tigger/Isis tempo + Gaston - Superior Archer + Demona draw',
     "verified_recent_event": True},
    {"pair": ('Amethyst', 'Ruby'), "archetype": 'Mulan / Gargoyles Tempo', "tier": 'B',
     "meta_share": 'In the onemorelore roundup and the ROK field',
     "style": "Rafiki/Luisa/Pepita Challenger 1-2 drops + Mulan - Martial Arts Master + Demona - Scourge + Hades - Looking for a Deal + Medallion Weights / Merlin's Shop",
     "verified_recent_event": True},
    {"pair": ('Amber', 'Ruby'), "archetype": 'Discard-Matters Removal', "tier": 'B',
     "meta_share": "One list in the ROK field ('RYL')",
     "style": 'Rivera Family Photo / The Torn Corner + Red Alert, Raging Storm, Gaston removal + Olaf / Maleficent - Monstrous Dragon top end',
     "verified_recent_event": True},
    {"pair": ('Amber', 'Steel'), "archetype": 'Steelsong', "tier": 'B',
     "meta_share": "No Hyperia City-era result tracked. Podcana's early tier list put it at B",
     "style": 'Singer unlock -> free Songs; tempo value',
     "verified_recent_event": False},
    {"pair": ('Amethyst', 'Steel'), "archetype": 'Midrange', "tier": 'B',
     "meta_share": "No Hyperia City-era result tracked. Podcana's early tier list put it at B",
     "style": 'Sturdy board + card draw; ink-drop payoffs from Set 14',
     "verified_recent_event": False},
    {"pair": ('Amethyst', 'Sapphire'), "archetype": 'Blurple / Control', "tier": 'C',
     "meta_share": "No Hyperia City-era result tracked. Podcana's early tier list put it at D",
     "style": 'Draw-heavy control',
     "verified_recent_event": False},
    {"pair": ('Ruby', 'Sapphire'), "archetype": 'Items/Control', "tier": 'C',
     "meta_share": "No Hyperia City-era result tracked. Podcana's early tier list put it at D",
     "style": 'Ramp into late-game removal',
     "verified_recent_event": False},
    {"pair": ('Ruby', 'Steel'), "archetype": 'Midrange', "tier": 'C',
     "meta_share": "No Hyperia City-era result tracked. Podcana's early tier list put it at C",
     "style": 'Combat-focused midrange',
     "verified_recent_event": False},
    {"pair": ('Sapphire', 'Steel'), "archetype": 'Hero/Ramp', "tier": 'D',
     "meta_share": "No Hyperia City-era result tracked. Podcana's early tier list put it at D",
     "style": 'Hero tribal + ramp',
     "verified_recent_event": False},
]

# One entry per known event, newest first. Placement counts only — no full
# decklists here (call get_meta(event="...") for those, or see tournaments.py);
# this is a shape-of-the-field summary, not a decklist database.
RECENT_TOURNAMENTS: list[dict] = [
    {
        "name": "ROK local tournament — Hyperia City",
        "date": "2026-10-26",
        "location": "Local game store (EN Core Constructed), first weekend after Set 14",
        "champion": {"pair": ("Emerald", "Sapphire"),
                     "note": "Mickey & Minnie Go-Wide (\"Mickey 14\")"},
        "runner_up": None,
        "placement_label": "Field (6 lists)",
        "placement_counts": {
            "Emerald/Sapphire Mickey & Minnie": 2,
            "Amber/Sapphire Detectives": 1,
            "Emerald/Ruby Discard-Matters": 1,
            "Amber/Ruby Discard-Matters": 1,
            "Amethyst/Ruby Mulan Tempo": 1,
        },
        "headline": "Small local event, only the winner reported. It's here because it's one of "
                    "the few real Hyperia City-era results with full lists. Full lists via "
                    "get_meta(event=\"rok\"). See also get_meta(event=\"onemorelore\") for "
                    "8 curated post-Set-14 lists, one per archetype.",
    },
    {
        "name": "Disney Lorcana Challenge — Europe Championship 2026",
        "date": "2026-09-13",
        "location": "Disney Hotel New York - The Art of Marvel, Disneyland Paris (EN Core Constructed)",
        "champion": {"pair": ("Amber", "Emerald"),
                     "note": "Aurora / Pocahontas Protective (Wojciech Złomek)"},
        "runner_up": None,
        "placement_label": "Top 16 archetype breakdown",
        "placement_counts": {
            "Amber/Emerald Aurora/Pocahontas Protective": 5,
            "Emerald/Steel Darkwing Duck Tempo": 4,
            "Amber/Amethyst Madrigal Midrange": 2,
            "Amber/Emerald (other)": 2,
            "Amethyst/Ruby": 1,
            "Emerald/Sapphire": 1,
            "Amethyst/Emerald Discard": 1,
        },
        "headline": "Official @disneylorcana decklist posts (not community-sourced, unlike the "
                    "NAC file) — full typed lists, low transcription risk. Amber/Emerald was the "
                    "field's center of gravity at 7 of 16, but split across three distinct "
                    "shells: the champion's Aurora - Holding Court / Pocahontas cost-discount "
                    "'Protective' build (5 of 16), an Items/Locations control build (Douglas "
                    "Auchelie), and a Singer/Song build (Florian Bertin) — don't conflate them "
                    "as one archetype. Emerald/Steel Darkwing Duck Tempo (NAC 2026's dominant "
                    "deck) placed 4 of 16 here too. Amethyst/Emerald Discard / Ramp Control (the "
                    "Asia Championship + FL CCQ champion shell) made one Top 16 appearance, "
                    "corroborating it as a real cross-region contender rather than a two-event "
                    "fluke. Full standings + all 16 decklists via get_meta(event=\"europe\").",
    },
    {
        "name": "Disney Lorcana Challenge Japan 2026 (DLC Kobe, Autumn)",
        "date": "2026-09-10",
        "location": "Kobe, Japan — Core JA / Asia rotation (2000+ players; Top 8 -> 2027 Japan Championship)",
        "champion": {"pair": ("Emerald", "Steel"),
                     "note": "Diablo Villains (Midori_K3064) — Diablo Shift chain (Maleficent's "
                             "Spy / Steam Serpent / Devoted Herald) + Ursula - Deceiver of All "
                             "song recursion + Pete - Games Referee action-lock + burn songs"},
        "runner_up": {"pair": ("Ruby", "Sapphire"),
                      "note": "Items (Manabe) — Scrooge McDuck / Tamatoa / Belle - Apprentice "
                              "Inventor free-item engine + Sisu / Scar / Be Prepared sweepers"},
        "placement_label": "Top 8 archetype breakdown",
        "placement_counts": {
            "Emerald/Steel Diablo Villains": 2,
            "Amber/Emerald Dogs & Lady tribal": 2,
            "Amber/Steel Singers": 2,
            "Ruby/Sapphire Items": 1,
            "Emerald/Ruby Diablo Control": 1,
        },
        "headline": "Japan's national Challenge, played in Core JA (Japanese rotation — Sets "
                    "3-5 still legal, e.g. Ursula - Deceiver of All, Diablo - Devoted Herald, "
                    "Pete - Games Referee), so this is a DIFFERENT metagame from the EN-Core "
                    "tier list above and must not be folded into it. Far more diverse than "
                    "the EN events: five archetypes across the Top 8, none more than 2 copies. "
                    "Emerald/Steel 'Diablo Villains' won. Ink pairs for the six non-finalist "
                    "decks are best-guess from card colours in the image grid. Full lists via "
                    "get_meta(event=\"kobe\").",
    },
    {
        "name": "Disney Lorcana Challenge — Asia Championship 2026",
        "date": "2026-09-10",
        "location": "Hong Kong Disneyland Hotel, Hong Kong (EN Core Constructed)",
        "champion": {"pair": ("Amethyst", "Emerald"),
                     "note": "Discard / Ramp Control (Michele Carretta)"},
        "runner_up": {"pair": ("Amber", "Amethyst"),
                      "note": "Madrigal Midrange (Earlmeister)"},
        "placement_label": "Top 8 archetype breakdown",
        "placement_counts": {
            "Amber/Amethyst": 6,
            "Amethyst/Emerald": 2,
        },
        "headline": "Amethyst/Emerald Discard — a pair this snapshot's tier list rated "
                    "D / 'Flexible' as recently as the NAC 2026 update — won outright and "
                    "also took a Top 4, while the Amber/Amethyst Madrigal Midrange shell "
                    "(the deck that won NAC 2026) took 6 of the Top 8 including the "
                    "runner-up. Emerald/Steel (69% of the NAC field) did not appear in the "
                    "Asia Top 8 — though a different Emerald/Steel build, 'Diablo Villains', "
                    "won the Core JA DLC Kobe the same period, so the pair is far from dead. "
                    "Source: @gaetancall Top 8 post; full lists via "
                    "get_meta(event=\"asia\").",
    },
    {
        "name": "Disney Lorcana Championship Qualifier (CCQ) — St. Augustine, FL",
        "date": "2026-09-10",
        "location": "St. Augustine, FL (EN Core Constructed)",
        "champion": {"pair": ("Amethyst", "Emerald"),
                     "note": "Discard / Ramp Control (Hector Heras)"},
        "runner_up": {"pair": ("Amethyst", "Emerald"),
                      "note": "Discard / Ramp Control (SplooshMcgoo) — near-identical list"},
        "placement_label": "Finals",
        "placement_counts": {"Amethyst/Emerald": 2},
        "headline": "Both finalists piloted the same Amethyst/Emerald Discard shell as the "
                    "Asia champion — a second EN-Core event, one week apart, confirming the "
                    "archetype is real and repeatable, not a one-off. Source: @gaetancall "
                    "CCQ decklist post.",
    },
    {
        "name": "Disney Lorcana North American Championship 2026",
        "date": "2026-08-30",
        "location": "Disneyland Resort, Anaheim, CA",
        "champion": {"pair": ("Amber", "Amethyst"),
                     "note": "Madrigal Midrange (Dillon LeDuc) — once mislabeled 'Amber/Sapphire' "
                             "here, in an earlier snapshot; @gaetancall's official Top 8 "
                             "post shows the winning 60 card-for-card with zero Sapphire (Rafiki / "
                             "Luisa Madrigal / Cheshire Cat - Inexplicable / Isis Vanderchill / "
                             "Demona are all Amethyst)"},
        "runner_up": {"pair": ("Emerald", "Steel"), "note": "Darkwing Duck Tempo"},
        "placement_label": "Top 16 archetype breakdown",
        "placement_counts": {
            "Emerald/Steel": 11,
            "Amber/Amethyst": 3,
            "Amber/Steel": 1,
            "Amber/Emerald": 1,
        },
        "headline": "11 of 16 (69%) of the Top 16 ran Emerald/Steel, including 3 players "
                    "on an identical 60-card list — but the eventual champion won on "
                    "Amber/Amethyst (the Madrigal Midrange shell), a pair this snapshot's "
                    "general tier list otherwise under-rates.",
    },
]


def _pair_key(pair: tuple[str, str]) -> frozenset[str]:
    return frozenset(p.strip().lower() for p in pair)


def _parse_ink_colors(ink_colors: str) -> frozenset[str] | None:
    parts = [p.strip().lower() for p in ink_colors.replace("/", ",").split(",") if p.strip()]
    return frozenset(parts) if parts else None


def format_meta_snapshot(ink_colors: str = "", event: str = "") -> str:
    """Render the bundled metagame snapshot as markdown.

    With `event` set, returns that tournament's full standings + decklists
    (see tournaments.py) instead of the tier list. Otherwise returns the
    tier list, optionally filtered to one ink pair, plus the recent-results
    summary and a pointer to the events that have full decklists.
    """
    if event.strip():
        return format_event(event)

    wanted = _parse_ink_colors(ink_colors)
    if wanted is not None and len(wanted) != 2:
        return (
            f'ink_colors must name exactly two ink colors (got "{ink_colors}"). '
            "Example: \"Emerald,Steel\"."
        )

    rows = CORE_TIER_LIST
    if wanted is not None:
        rows = [r for r in rows if _pair_key(r["pair"]) == wanted]
        if not rows:
            valid_pairs = ", ".join(f"{a}/{b}" for a, b in (r["pair"] for r in CORE_TIER_LIST))
            return (
                f'No tier-list entry for "{ink_colors}". Every two-ink combination is '
                f"tracked; valid pairs: {valid_pairs}."
            )

    lines = [
        f"**Core Constructed metagame snapshot — as of {META_SNAPSHOT_DATE}, "
        "not live data.**",
        "This is a hand-maintained snapshot bundled into the lorcana-mcp package at "
        "release time (see the package CHANGELOG for when it was last refreshed) — "
        "there is no live tournament-results feed to fetch from, unlike this "
        "server's card data. Treat every figure below as \"known as of this date\", "
        "and check these sources directly for anything newer:",
    ]
    lines += [f"- {s}" for s in META_SOURCES]
    lines.append("")

    lines.append("| Pair | Archetype | Tier | Meta share | Style | Seen in Hyperia City-era results? |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        a, b = r["pair"]
        verified = "yes" if r["verified_recent_event"] else "no — no Set 14 data"
        lines.append(
            f"| {a}/{b} | {r['archetype']} | {r['tier']} | {r['meta_share']} | "
            f"{r['style']} | {verified} |"
        )

    if wanted is None:
        lines.append("")
        lines.append(
            "Rows flagged \"yes\" were seen in a Hyperia City-era (Set 14+) result or meta "
            "report: inkDecks' November 2026 Core report, the onemorelore.au weekly roundup, "
            "or the ROK local. Rows flagged \"no\" have no post-Set-14 data and rely on "
            "Podcana's pre-release tier list, so treat them as guesses."
        )

    if RECENT_TOURNAMENTS:
        lines.append("")
        lines.append("## Recent tournament results")
        for t in RECENT_TOURNAMENTS:
            champ_a, champ_b = t["champion"]["pair"]
            lines.append(f"### {t['name']} — {t['date']}, {t['location']}")
            lines.append(
                f"- **Champion:** {champ_a}/{champ_b} ({t['champion']['note']})"
            )
            if t.get("runner_up"):
                runner_a, runner_b = t["runner_up"]["pair"]
                lines.append(
                    f"- **Runner-up:** {runner_a}/{runner_b} ({t['runner_up']['note']})"
                )
            label = t.get("placement_label", "Placement breakdown")
            lines.append(f"- **{label}:** " + ", ".join(
                f"{pair} ×{count}" for pair, count in t["placement_counts"].items()
            ))
            lines.append(f"- {t['headline']}")

    if TOURNAMENTS:
        lines.append("")
        lines.append(
            "**Full standings + decklists** for "
            + ", ".join(f"`{k}`" for k in TOURNAMENTS)
            + " — call `get_meta(event=\"<key or name fragment>\")` (e.g. "
            "`get_meta(event=\"nac\")`, `get_meta(event=\"kobe\")`)."
        )

    return "\n".join(lines)
