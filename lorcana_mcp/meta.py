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

META_SNAPSHOT_DATE = "2026-09-10"

META_SOURCES = [
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
    "separate metagame from EN Core; see lorcana/ChallengeJapan2026Kobe_top8_decklists.md",
    "Disney Lorcana North American Championship 2026 Top 8 "
    "(@gaetancall Instagram official Top 8 decklist post — supersedes the earlier "
    "community-sourced NAC2026_top8_decklists.md on any conflict)",
]

# Core Constructed ink-pair tier list. `meta_share` is a rough, mixed-source
# figure (some from general metagame trackers, some from the championship
# results below) — treat it as directional, not a precise stat.
# `verified_recent_event` marks the pairs actually re-checked against a real
# recent championship result (NAC 2026, Asia Championship 2026, and/or the
# FL CCQ — see RECENT_TOURNAMENTS below); every other row is un-refreshed
# June-2026-era data that predates those events and may itself be stale.
CORE_TIER_LIST: list[dict] = [
    {"pair": ("Emerald", "Steel"), "archetype": "Darkwing Duck Tempo", "tier": "S",
     "meta_share": "69% of NAC 2026 Top 16 (but absent from the Asia Championship 2026 Top 8)",
     "style": "Elinor/Mushu/Tod/Ursula/Vixey core + Darkwing Duck package + burn songs",
     "verified_recent_event": True},
    {"pair": ("Amber", "Amethyst"), "archetype": "Madrigal Midrange (was Evasive/Flood)",
     "tier": "S",
     "meta_share": "won NAC 2026; 6 of 8 (incl. runner-up) at Asia Championship 2026",
     "style": "Grandmother Willow/Hamm 2-drop curve-accel + Luisa Madrigal Shift chain "
              "(Pushing Through -> Confident Climber) + Tigger/Isis Vanderchill tempo + "
              "Gaston - Superior Archer removal + Ohana Means Family/The Horseman Strikes! draw",
     "verified_recent_event": True},
    {"pair": ("Amethyst", "Sapphire"), "archetype": "Blurple / Control", "tier": "S",
     "meta_share": "~18%", "style": "Draw-heavy control; hard to run out of resources",
     "verified_recent_event": False},
    {"pair": ("Amber", "Emerald"), "archetype": "Aggro", "tier": "S",
     "meta_share": "~17%", "style": "Fast board + unstoppable Evasive questors",
     "verified_recent_event": False},
    {"pair": ("Amethyst", "Emerald"), "archetype": "Discard / Ramp Control", "tier": "A",
     "meta_share": "won the Asia Championship 2026 (+ a Top 4) and swept the FL CCQ "
                   "St. Augustine final — both EN Core; no tracked field % yet",
     "style": "Lyle Tiberius Rourke discard-matters lore drain + Retro Evolution Device/"
              "Chernabog ramp-reanimate + Hades - Looking for a Deal draw + "
              "Prince Phillip - Vanquisher of Foes / Malicious, Mean, and Scary board wipe",
     "verified_recent_event": True},
    {"pair": ("Emerald", "Sapphire"), "archetype": "Control", "tier": "A",
     "meta_share": "~14%", "style": "Disruption + ramp + card advantage",
     "verified_recent_event": False},
    {"pair": ("Amber", "Steel"), "archetype": "Steelsong", "tier": "A",
     "meta_share": "strong in Infinity", "style": "Singer unlock -> free Songs; tempo value",
     "verified_recent_event": False},
    {"pair": ("Amethyst", "Steel"), "archetype": "Aggro/Control", "tier": "A",
     "meta_share": "competitive", "style": "Sturdy board + card draw; well-rounded",
     "verified_recent_event": False},
    {"pair": ("Amethyst", "Ruby"), "archetype": "Bounce", "tier": "A",
     "meta_share": "top in Infinity", "style": "Bounce + removal + card draw",
     "verified_recent_event": False},
    {"pair": ("Amber", "Ruby"), "archetype": "Toys", "tier": "B",
     "meta_share": "~5%", "style": "Toy Story tribal; board pressure",
     "verified_recent_event": False},
    {"pair": ("Ruby", "Sapphire"), "archetype": "Items/Control", "tier": "B",
     "meta_share": "~12% in Infinity", "style": "Ramp into late-game removal",
     "verified_recent_event": False},
    {"pair": ("Amber", "Sapphire"), "archetype": "Toys/Ramp Midrange", "tier": "C",
     "meta_share": "niche",
     "style": "Ramp/Toys midrange; the NAC 2026 title once credited to this pair was "
              "really Amber/Amethyst (the winning list has zero Sapphire cards)",
     "verified_recent_event": False},
    {"pair": ("Ruby", "Steel"), "archetype": "Midrange", "tier": "C",
     "meta_share": "niche", "style": "Combat-focused midrange",
     "verified_recent_event": False},
    {"pair": ("Emerald", "Ruby"), "archetype": "Aggressive", "tier": "C",
     "meta_share": "niche", "style": "Challenging synergies",
     "verified_recent_event": False},
    {"pair": ("Sapphire", "Steel"), "archetype": "Hero/Ramp", "tier": "C",
     "meta_share": "niche", "style": "Hero tribal + ramp",
     "verified_recent_event": False},
]

# One entry per known event, newest first. Placement counts only — no full
# decklists here (that's what build_deck/analyze_deck are for, plus the
# lorcana/*_top8_decklists.md files); this is a shape-of-the-field summary,
# not a decklist database.
RECENT_TOURNAMENTS: list[dict] = [
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
                    "decks are best-guess from card colours in the image grid. Full lists in "
                    "lorcana/ChallengeJapan2026Kobe_top8_decklists.md.",
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
                    "Source: @gaetancall Top 8 post; full lists in "
                    "lorcana/AsiaChampionship2026_top8_decklists.md.",
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
                             "here and in NAC2026_top8_decklists.md; @gaetancall's official Top 8 "
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


def format_meta_snapshot(ink_colors: str = "") -> str:
    """Render the bundled metagame snapshot as markdown, optionally filtered
    to a single ink pair. See module docstring for what this is and isn't.
    """
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

    lines.append("| Pair | Archetype | Tier | Meta share | Style | Verified vs. a recent championship? |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        a, b = r["pair"]
        verified = "yes" if r["verified_recent_event"] else "no — pre-dates those events"
        lines.append(
            f"| {a}/{b} | {r['archetype']} | {r['tier']} | {r['meta_share']} | "
            f"{r['style']} | {verified} |"
        )

    if wanted is None:
        lines.append("")
        lines.append(
            "Only the rows flagged \"yes\" above (Emerald/Steel, Amber/Amethyst, "
            "Amethyst/Emerald) have been directly verified against a real recent "
            "championship result (NAC 2026 Anaheim, Asia Championship 2026 Hong Kong, "
            "and/or the FL CCQ St. Augustine). Every other row is older, unverified "
            "metagame-tracker data and may itself be stale."
        )

    if RECENT_TOURNAMENTS:
        lines.append("")
        lines.append("## Recent tournament results")
        for t in RECENT_TOURNAMENTS:
            champ_a, champ_b = t["champion"]["pair"]
            runner_a, runner_b = t["runner_up"]["pair"]
            lines.append(f"### {t['name']} — {t['date']}, {t['location']}")
            lines.append(
                f"- **Champion:** {champ_a}/{champ_b} ({t['champion']['note']})"
            )
            lines.append(
                f"- **Runner-up:** {runner_a}/{runner_b} ({t['runner_up']['note']})"
            )
            label = t.get("placement_label", "Placement breakdown")
            lines.append(f"- **{label}:** " + ", ".join(
                f"{pair} ×{count}" for pair, count in t["placement_counts"].items()
            ))
            lines.append(f"- {t['headline']}")

    return "\n".join(lines)
