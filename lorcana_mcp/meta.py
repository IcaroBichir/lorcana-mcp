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

META_SNAPSHOT_DATE = "2026-08-30"

META_SOURCES = [
    "inkDecks.com (metagame breakdown, tier lists)",
    "lorcana.gg (tier list, rotation tracker)",
    "Disney Lorcana North American Championship 2026, Disneyland Resort, Anaheim CA "
    "(official Top 16 decklist posts + Day 1/2 metagame breakdown graphics)",
]

# Core Constructed ink-pair tier list. `meta_share` is a rough, mixed-source
# figure (some from general metagame trackers, some from the NAC 2026 result
# below) — treat it as directional, not a precise stat. `verified_nac_2026`
# marks the two pairs actually re-checked against real NAC 2026 Top 16
# results (see RECENT_TOURNAMENTS below); every other row is un-refreshed
# June-2026-era data that predates that event and may itself be stale.
CORE_TIER_LIST: list[dict] = [
    {"pair": ("Emerald", "Steel"), "archetype": "Darkwing Duck Tempo", "tier": "S",
     "meta_share": "69% of NAC 2026 Top 16",
     "style": "Elinor/Mushu/Tod/Ursula/Vixey core + Darkwing Duck package + burn songs",
     "verified_nac_2026": True},
    {"pair": ("Amethyst", "Sapphire"), "archetype": "Blurple / Control", "tier": "S",
     "meta_share": "~18%", "style": "Draw-heavy control; hard to run out of resources",
     "verified_nac_2026": False},
    {"pair": ("Amber", "Emerald"), "archetype": "Aggro", "tier": "S",
     "meta_share": "~17%", "style": "Fast board + unstoppable Evasive questors",
     "verified_nac_2026": False},
    {"pair": ("Amber", "Amethyst"), "archetype": "Evasive / Flood", "tier": "S",
     "meta_share": "~14%", "style": "Cheap board flood + evasive questing",
     "verified_nac_2026": False},
    {"pair": ("Amber", "Sapphire"), "archetype": "Toys/Ramp Midrange", "tier": "A",
     "meta_share": "3 of 16 at NAC 2026, incl. the win",
     "style": "Grandmother Willow/Hamm core + Luisa Madrigal damage-sponge + "
              "Besties Assemble!/Junior Woodchuck Guidebook dig",
     "verified_nac_2026": True},
    {"pair": ("Emerald", "Sapphire"), "archetype": "Control", "tier": "A",
     "meta_share": "~14%", "style": "Disruption + ramp + card advantage",
     "verified_nac_2026": False},
    {"pair": ("Amber", "Steel"), "archetype": "Steelsong", "tier": "A",
     "meta_share": "strong in Infinity", "style": "Singer unlock → free Songs; tempo value",
     "verified_nac_2026": False},
    {"pair": ("Amethyst", "Steel"), "archetype": "Aggro/Control", "tier": "A",
     "meta_share": "competitive", "style": "Sturdy board + card draw; well-rounded",
     "verified_nac_2026": False},
    {"pair": ("Amethyst", "Ruby"), "archetype": "Bounce", "tier": "A",
     "meta_share": "top in Infinity", "style": "Bounce + removal + card draw",
     "verified_nac_2026": False},
    {"pair": ("Amber", "Ruby"), "archetype": "Toys", "tier": "B",
     "meta_share": "~5%", "style": "Toy Story tribal; board pressure",
     "verified_nac_2026": False},
    {"pair": ("Ruby", "Sapphire"), "archetype": "Items/Control", "tier": "B",
     "meta_share": "~12% in Infinity", "style": "Ramp into late-game removal",
     "verified_nac_2026": False},
    {"pair": ("Ruby", "Steel"), "archetype": "Midrange", "tier": "C",
     "meta_share": "niche", "style": "Combat-focused midrange",
     "verified_nac_2026": False},
    {"pair": ("Emerald", "Ruby"), "archetype": "Aggressive", "tier": "C",
     "meta_share": "niche", "style": "Challenging synergies",
     "verified_nac_2026": False},
    {"pair": ("Sapphire", "Steel"), "archetype": "Hero/Ramp", "tier": "C",
     "meta_share": "niche", "style": "Hero tribal + ramp",
     "verified_nac_2026": False},
    {"pair": ("Amethyst", "Emerald"), "archetype": "Flexible", "tier": "D",
     "meta_share": "niche", "style": "Tricks + evasion; inconsistent",
     "verified_nac_2026": False},
]

# One entry per known event. Placement counts only — no full decklists here
# (that's what build_deck/analyze_deck are for); this is a shape-of-the-field
# summary, not a decklist database.
RECENT_TOURNAMENTS: list[dict] = [
    {
        "name": "Disney Lorcana North American Championship 2026",
        "date": "2026-08-30",
        "location": "Disneyland Resort, Anaheim, CA",
        "champion": {"pair": ("Amber", "Sapphire"), "note": "Toys/Ramp Midrange shell"},
        "runner_up": {"pair": ("Emerald", "Steel"), "note": "Darkwing Duck Tempo"},
        "top_16_archetype_counts": {
            "Emerald/Steel": 11,
            "Amber/Sapphire": 3,
            "Amber/Steel": 1,
            "Amber/Emerald": 1,
        },
        "headline": "11 of 16 (69%) of the Top 16 ran Emerald/Steel, including 3 players "
                    "on an identical 60-card list — but the eventual champion won on "
                    "Amber/Sapphire, a pair this snapshot's general tier list otherwise "
                    "under-rates.",
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

    lines.append("| Pair | Archetype | Tier | Meta share | Style | Verified vs. NAC 2026? |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        a, b = r["pair"]
        verified = "yes" if r["verified_nac_2026"] else "no — pre-dates that event"
        lines.append(
            f"| {a}/{b} | {r['archetype']} | {r['tier']} | {r['meta_share']} | "
            f"{r['style']} | {verified} |"
        )

    if wanted is None:
        lines.append("")
        lines.append(
            "Only the Emerald/Steel and Amber/Sapphire rows above have been directly "
            "verified against a real recent tournament result (NAC 2026) — every other "
            "row is older, unverified metagame-tracker data and may itself be stale."
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
            lines.append("- **Top 16 archetype breakdown:** " + ", ".join(
                f"{pair} ×{count}" for pair, count in t["top_16_archetype_counts"].items()
            ))
            lines.append(f"- {t['headline']}")

    return "\n".join(lines)
