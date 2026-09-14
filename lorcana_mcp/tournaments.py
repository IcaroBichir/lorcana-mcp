"""Full tournament standings + decklists, bundled so `get_meta(event=...)`
can serve them without anyone keeping local files.

Same nature as meta.py: a hand-maintained snapshot, not a live feed. Tournament
decklists circulate as social-media card-grid images, so counts/art are reliable
but a few 1-of tech slots and some subtitles are best-effort — per-list `note`s
flag where. Update by editing the dicts below and cutting a release.

`META_SNAPSHOT_DATE` in meta.py covers this module too.
"""
from __future__ import annotations


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


# One entry per event. `decklists` is ordered best-finish-first.
TOURNAMENTS: dict[str, dict] = {
    "asia-championship-2026": {
        "name": "Disney Lorcana Challenge — Asia Championship 2026",
        "date": "2026-09-10",
        "location": "Hong Kong Disneyland Hotel, Hong Kong",
        "format": "EN Core Constructed",
        "source": "@gaetancall Instagram Top 8 decklist post (card-grid images, no text lists), captured 2026-09-10.",
        "notes": (
            "Transcribed from a low-res image post — card counts/art are reliable, a few 1-of tech "
            "slots in the six near-identical Madrigal Midrange lists are approximate. The champion "
            "and runner-up lists below were cross-checked card-by-card and every printing is "
            "confirmed EN-Core-legal (Sets 9–13). Archetype tally: Amber/Amethyst Madrigal Midrange "
            "6 of 8 (incl. runner-up); Amethyst/Emerald Discard 2 of 8 (incl. champion). "
            "Emerald/Steel — 69% of NAC 2026's Top 16, same format — was shut out of this Top 8 "
            "(different region, ~2 weeks later; possible meta shift, don't over-read)."
        ),
        "standings": [
            {"place": "Champion", "player": "Michele Carretta", "archetype": "Discard / Ramp Control", "inks": "Amethyst / Emerald"},
            {"place": "2nd", "player": "Earlmeister", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst"},
            {"place": "Top 4", "player": "Dillon 'MoleStar'", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst"},
            {"place": "Top 4", "player": "Jordenjorden", "archetype": "Discard / Ramp Control", "inks": "Amethyst / Emerald"},
            {"place": "Top 8", "player": "Samuele Estratti", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst"},
            {"place": "Top 8", "player": "Juancho Morales", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst"},
            {"place": "Top 8", "player": "Jordan 'JV'", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst"},
            {"place": "Top 8", "player": "WetWhale", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst"},
        ],
        "decklists": [
            {
                "label": "Champion — Michele Carretta",
                "archetype": "Discard / Ramp Control", "inks": "Amethyst / Emerald",
                "note": ("Discard-matters: Lyle Tiberius Rourke's DIRTY TRICKS drains opponent lore when "
                         "2+ cards hit your discard; Tod / Aladdin & Genie churn; Retro Evolution Device + "
                         "Chernabog ramp/reanimate; Prince Phillip - Vanquisher of Foes (hard-cast at 9, no "
                         "base Phillip in the 60) + Malicious, Mean, and Scary is the board wipe. Also run "
                         "by Jordenjorden (Top 4) and both FL CCQ finalists (see event fl-ccq-st-augustine-2026)."),
                "cards": [
                    "3x Rafiki - Mystical Fighter",
                    "4x Aladdin - Doing His Part",
                    "3x Lyle Tiberius Rourke - Adventurer for Hire",
                    "3x Piercing Attack",
                    "2x Lenny - Toy Binoculars",
                    "4x The Huntsman - On the Queen's Orders",
                    "4x Tod - Clever Fox",
                    "4x Malicious, Mean, and Scary",
                    "4x Junior Woodchuck Guidebook",
                    "4x Retro Evolution Device",
                    "3x Sven - Leaping Reindeer",
                    "2x To Wither a Flower",
                    "4x Aladdin & Genie - Mischievous Pals",
                    "4x Hades - Looking for a Deal",
                    "2x John Silver - Alien Pirate",
                    "4x Milo Thatch - Getting His Hands Dirty",
                    "4x Prince Phillip - Vanquisher of Foes",
                    "1x Under the Sea",
                    "1x Second Star to the Right",
                ],
            },
            {
                "label": "Runner-up — Earlmeister",
                "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst",
                "note": ("The NAC 2026 champion shell, lightly evolved: Grandmother Willow + Hamm cost-"
                         "reduction into a Luisa Madrigal Shift chain (Pushing Through → Confident Climber), "
                         "Tigger / Isis Vanderchill / Ursula tempo, Gaston - Superior Archer removal, Ohana "
                         "Means Family + The Horseman Strikes! for card flow. Dillon 'MoleStar', Samuele "
                         "Estratti, Juancho Morales, Jordan 'JV', WetWhale all ran near-identical builds "
                         "(tech: Juancho +Angel - Siren Singer / Agustin Madrigal / Akood et Emuti; WetWhale "
                         "+Belle - Bookworm / The Black Cauldron; Jordan 'JV' +Mrs. Incredible - Super Stretchy)."),
                "cards": [
                    "4x Luisa Madrigal - Pushing Through",
                    "4x Rafiki - Mystical Fighter",
                    "4x Grandmother Willow - Ancient Advisor",
                    "4x Hamm - Piggy Bank",
                    "4x Cheshire Cat - Inexplicable",
                    "4x Isis Vanderchill - Ice Queen of St. Canard",
                    "3x Nakoma - Waiting Out the Storm",
                    "2x Sven - Leaping Reindeer",
                    "4x Tigger - Bouncing All the Way",
                    "4x Gaston - Superior Archer",
                    "2x Hades - Looking for a Deal",
                    "1x Luisa Madrigal - Confident Climber",
                    "4x Sulley - The New Boss",
                    "2x Ursula - Whisper of Vanessa",
                    "4x Demona - Scourge of the Wyvern Clan",
                    "2x Stitch - Carefree Surfer",
                    "1x Ohana Means Family",
                    "4x The Horseman Strikes!",
                    "3x Junior Woodchuck Guidebook",
                ],
            },
        ],
    },

    "fl-ccq-st-augustine-2026": {
        "name": "Disney Lorcana Championship Qualifier (CCQ) — St. Augustine, FL",
        "date": "2026-09-10",
        "location": "St. Augustine, FL",
        "format": "EN Core Constructed",
        "source": "@gaetancall Instagram champion/finalist decklist post.",
        "notes": (
            "A US EN-Core event ~1 week after the Asia Championship. Both finalists piloted the same "
            "Amethyst/Emerald Discard shell as the Asia champion — independent confirmation the "
            "archetype is real and repeatable. Only partial card lists were published; the notable "
            "cards are listed rather than a full 60."
        ),
        "standings": [
            {"place": "Champion", "player": "Hector Heras", "archetype": "Discard / Ramp Control", "inks": "Amethyst / Emerald"},
            {"place": "Finalist", "player": "SplooshMcgoo", "archetype": "Discard / Ramp Control", "inks": "Amethyst / Emerald"},
        ],
        "decklists": [
            {
                "label": "Champion — Hector Heras (partial — notable cards)",
                "archetype": "Discard / Ramp Control", "inks": "Amethyst / Emerald",
                "note": "Same shell as the Asia champion. Finalist SplooshMcgoo ran a near-identical list "
                        "(swaps a couple of 1-ofs — e.g. Dumbo where Heras runs an extra Elsa).",
                "cards": [
                    "Aladdin - Doing His Part", "Lyle Tiberius Rourke - Adventurer for Hire",
                    "Elsa - Exploring the Unknown", "Lenny - Toy Binoculars", "Dumbo",
                    "The Huntsman - On the Queen's Orders", "Tod - Clever Fox",
                    "Aladdin & Genie - Mischievous Pals", "Chernabog", "Hades - Looking for a Deal",
                    "Mrs. Incredible - Super Stretchy", "Taran - Magically Armed", "Demona",
                    "John Silver - Alien Pirate", "Milo Thatch - Getting His Hands Dirty",
                    "Prince Phillip - Vanquisher of Foes", "Malicious, Mean, and Scary",
                    "Under the Sea", "Junior Woodchuck Guidebook", "Retro Evolution Device",
                ],
            },
        ],
    },

    "dlc-kobe-2026": {
        "name": "Disney Lorcana Challenge Japan 2026 (DLC Kobe, Autumn)",
        "date": "2026-09-10",
        "location": "Kobe, Japan (神戸)",
        "format": "Core JA (Japanese/Asia rotation — WIDER pool than EN Core; Sets 3–5 still legal)",
        "source": "@gaetancall Instagram Top 8 decklist post (card-grid images), captured 2026-09-10.",
        "notes": (
            "Japan's national Challenge — 2000+ players, BO1, 9 Swiss → Top 64 single elim; Top 8 "
            "qualify for the 2027 Japan Championship. **Core JA is a different metagame — do NOT fold "
            "these into the EN Core tier list.** Cards like Ursula - Deceiver of All (Set 3), Diablo - "
            "Devoted Herald (Set 4), Pete - Games Referee (Set 5), Scrooge McDuck (Set 3), Sisu - "
            "Empowered Sibling (Set 4) are legal here but not in EN Core. A flat field: five "
            "archetypes across eight seats, none over 2 copies. Ink pairs for the six non-finalist "
            "decks are best-guess from card-border colours in the image grid; those lists are given "
            "at archetype level only."
        ),
        "standings": [
            {"place": "Champion", "player": "みどり_K3064 (Midori_K3064)", "archetype": "Diablo Villains — songs/control", "inks": "Emerald / Steel"},
            {"place": "Finalist", "player": "マナベ (Manabe)", "archetype": "Items", "inks": "Ruby / Sapphire"},
            {"place": "Top 4", "player": "けちゃまる (Kechamaru)", "archetype": "Diablo control — big Emerald midrange", "inks": "Emerald / Ruby"},
            {"place": "Top 4", "player": "hakumai", "archetype": "Dogs & Lady tribal", "inks": "Amber / Emerald (may lean Amethyst)"},
            {"place": "Top 8", "player": "ぷぅ (Puu)", "archetype": "Dogs & Lady tribal", "inks": "Amber / Emerald"},
            {"place": "Top 8", "player": "カワウソ_K1415 (Kawauso_K1415)", "archetype": "Singers", "inks": "Amber / Steel"},
            {"place": "Top 8", "player": "ちゃば (Chaba)", "archetype": "Diablo Villains — songs/control", "inks": "Emerald / Steel"},
            {"place": "Top 8", "player": "ハム_K2632 (Hamu_K2632)", "archetype": "Singers", "inks": "Amber / Steel"},
        ],
        "decklists": [
            {
                "label": "Champion — Midori_K3064",
                "archetype": "Diablo Villains — songs/control", "inks": "Emerald / Steel",
                "note": ("Diablo package: cheap Diablo bodies (Maleficent's Spy peeks hands) Shift into "
                         "Diablo - Devoted Herald (Shift by discarding an action, Evasive). Ursula - "
                         "Deceiver of All replays each song from discard for free; Max Goof buys songs "
                         "back; Pete - Games Referee locks opponent out of actions for a turn; The Muses "
                         "bounce a small body per song. Steel burn songs close. #2 Diablo slot subtitle "
                         "unconfirmed (assumed Steam Serpent). Also run by Chaba (Top 8)."),
                "cards": [
                    "4x Diablo - Maleficent's Spy",
                    "4x Ursula - Deceiver",
                    "4x Fergus - King of DunBroch",
                    "4x Diablo - Steam Serpent",
                    "2x Lenny - Toy Binoculars",
                    "4x Max Goof - Rebellious Teen",
                    "4x Diablo - Devoted Herald",
                    "4x Ursula - Deceiver of All",
                    "4x Pete - Games Referee",
                    "4x Elinor - Renowned Diplomat",
                    "3x The Muses - Proclaimers of Heroes",
                    "4x Sudden Chill",
                    "4x Keep the Ancient Ways",
                    "3x Malicious, Mean, and Scary",
                    "4x Strength of a Raging Fire",
                    "4x Let the Storm Rage On",
                ],
            },
            {
                "label": "Finalist — Manabe",
                "archetype": "Items", "inks": "Ruby / Sapphire",
                "note": ("Free-item value engine: Scrooge McDuck, Tamatoa - Happy as a Clam, Belle - "
                         "Apprentice Inventor put items into play / recur them for free; item suite fuels "
                         "ramp/draw/debuffs. Ruby half is the sweeper package — Sisu - Empowered Sibling, "
                         "Scar, Be Prepared, Brawl — plus Tamatoa - So Shiny! top end. "
                         "⚠ transcribes to 61 — one 1-of/2-of count is misread (likely Be Prepared 3→2 or "
                         "Tamatoa - So Shiny! 3→2). Scrooge McDuck subtitle unconfirmed (cost reads 4, "
                         "'exert 4 items to play for free' — not the Set 3 'Richest Duck in the World'). "
                         "Vitalisphere = the Ursula's Return cost-1 item."),
                "cards": [
                    "4x Jebidiah Farnsworth - Cookie",
                    "4x Belle - Apprentice Inventor",
                    "4x Scrooge McDuck",
                    "4x Tamatoa - Happy as a Clam",
                    "2x Scar - Vicious Cheater",
                    "4x Sisu - Empowered Sibling",
                    "3x Tamatoa - So Shiny!",
                    "4x Sail the Azurite Sea",
                    "2x Hide Away",
                    "2x Brawl",
                    "3x Be Prepared",
                    "4x Vitalisphere",
                    "4x Pawpsicle",
                    "2x Inkrunner",
                    "4x Sapphire Coil",
                    "2x Basil's Magnifying Glass",
                    "4x Maurice's Workshop",
                    "4x Fishbone Quill",
                    "1x Lucky Dime",
                ],
            },
        ],
    },

    "nac-2026": {
        "name": "Disney Lorcana North American Championship 2026",
        "date": "2026-08-30",
        "location": "Disneyland Resort, Anaheim, CA",
        "format": "EN Core Constructed",
        "source": ("Official disneylorcana + @gaetancall Instagram Top 8 posts, lorcanacollectors "
                   "card-photo posts, martinlorcana duels.ink graphics. Screenshots 2026-08-30/31."),
        "notes": (
            "Archetype tally: 11 of 16 (69%) ran Emerald/Steel 'Darkwing Duck Tempo', incl. 2nd and "
            "both Top 4. The champion (Dillon LeDuc) won on **Amber/Amethyst 'Madrigal Midrange'** — "
            "originally mislabeled 'Amber/Sapphire'; the winning 60 has zero Sapphire (Rafiki, Luisa "
            "Madrigal, Cheshire Cat - Inexplicable, Isis Vanderchill, Demona, Tigger, Sven, Dumbo are "
            "all Amethyst), confirmed card-for-card against @gaetancall's official Top 8 post. That "
            "post also shows 'Sky' (2nd) and 'S4iler' (Top 4, = Pierre-Marc Duguay) are two different "
            "players. Kurt Spiess / Pierre-Marc Duguay / Luke Vvonderland all ran one identical "
            "'Core 60' Emerald/Steel list. Alphos (55), Robert Serpe (50), Mark Landers (62) lists "
            "don't sum to 60 as transcribed — flagged on each."
        ),
        "standings": [
            {"place": "Champion", "player": "Dillon LeDuc", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst"},
            {"place": "2nd", "player": "Sky", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 4", "player": "Luke Vvonderland", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 4", "player": "Pierre-Marc Duguay ('S4iler')", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 8", "player": "Dave Solberg", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 8", "player": "Dylan Brown", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 8", "player": "Joseph Quigley", "archetype": "Amber/Steel", "inks": "Amber / Steel"},
            {"place": "Top 8", "player": "Alphos Parker-Acheson", "archetype": "Darkwing Duck Tempo (Toys/Gargoyle variant)", "inks": "Emerald / Steel"},
            {"place": "Top 16", "player": "Kurt Spiess", "archetype": "Darkwing Duck Tempo ('Core 60')", "inks": "Emerald / Steel"},
            {"place": "Top 16", "player": "Robert Serpe", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 16", "player": "Ryan Ngoh", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst"},
            {"place": "Top 16", "player": "Jonathanz Williams", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst"},
            {"place": "Top 16", "player": "Mark Landers", "archetype": "Pocahontas midrange", "inks": "Amber / Emerald"},
            {"place": "Top 16", "player": "Matthew Peddle", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 16", "player": "Shane Downey", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 16", "player": "Tyler Novak", "archetype": "Darkwing Duck Tempo (divergent build)", "inks": "Emerald / Steel"},
        ],
        "decklists": [
            {
                "label": "Champion — Dillon LeDuc", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst",
                "note": "Grandmother Willow / Hamm 2-drop core + Besties, Assemble! selection + Luisa "
                        "Madrigal Shift chain. Cheshire Cat - Inexplicable is a Boost / damage-transfer "
                        "tempo piece, not a dig/draw card.",
                "cards": [
                    "4x Rafiki - Mystical Fighter", "4x Luisa Madrigal - Pushing Through",
                    "4x Besties, Assemble!", "4x Grandmother Willow - Ancient Advisor",
                    "4x Hamm - Piggy Bank", "3x Dumbo - The Flying Elephant",
                    "4x The Horseman Strikes!", "4x Cheshire Cat - Inexplicable",
                    "1x Ohana Means Family", "3x Nakoma - Waiting Out the Storm",
                    "4x Tigger - Bouncing All the Way", "4x Isis Vanderchill - Ice Queen of St. Canard",
                    "2x Sven - Leaping Reindeer", "3x Luisa Madrigal - Confident Climber",
                    "4x Gaston - Superior Archer", "4x Demona - Scourge of the Wyvern Clan",
                    "4x Stitch - Carefree Surfer",
                ],
            },
            {
                "label": "2nd — Sky", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "note": "From the duels.ink 'Sky NA DLC' graphic. ⚠ transcribes to 59 — one line "
                        "under-captured (the official Top 16 text post has the same gap); the missing "
                        "card is likely a 4th White Rabbit - Late Again or an extra song.",
                "cards": [
                    "4x Angel - Experiment 624", "3x Angela - Night Warrior",
                    "4x Broadway - Sturdy and Strong", "4x Darkwing Duck - Crime Fighter",
                    "2x Darkwing Duck - Shadowy Superhero", "4x Elinor - Renowned Diplomat",
                    "2x Flynn Rider - Spectral Scoundrel", "4x Launchpad - Trusty Sidekick",
                    "4x Mushu - Stealthy Dragon", "3x The Huntsman - On the Queen's Orders",
                    "2x The Queen - Devious Disguise", "4x Tod - All Alone", "4x Ursula - Deceiver",
                    "4x Vixey - Forest Friend", "4x White Rabbit - Late Again",
                    "2x He Hurled His Thunderbolt", "4x Strength of a Raging Fire",
                    "1x You Broke My Smolder",
                ],
            },
            {
                "label": "'The Core 60' — Kurt Spiess, Pierre-Marc Duguay (Top 4), Luke Vvonderland (Top 4)",
                "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "note": "Three pilots, one identical 60 — the netdecked 'solved' build of the event.",
                "cards": [
                    "4x Angel - Experiment 624", "4x Angela - Night Warrior",
                    "4x Broadway - Sturdy and Strong", "4x Darkwing Duck - Crime Fighter",
                    "1x Darkwing Duck - Shadowy Superhero", "4x Elinor - Renowned Diplomat",
                    "3x Hamish, Hubert & Harris - Troublemaking Triplets", "4x Launchpad - Trusty Sidekick",
                    "4x Mushu - Stealthy Dragon", "2x The Queen - Devious Disguise", "4x Tod - All Alone",
                    "4x Ursula - Deceiver", "4x Vixey - Forest Friend", "4x White Rabbit - Late Again",
                    "2x He Hurled His Thunderbolt", "4x Strength of a Raging Fire",
                    "4x The Terror That Flaps in the Night",
                ],
            },
            {
                "label": "Top 8 — Dave Solberg", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "note": "Core 60 with a Jasmine / Pegasus / The Huntsman evasive package instead of "
                        "Hamish + He Hurled His Thunderbolt.",
                "cards": [
                    "3x Angel - Experiment 624", "3x Angela - Night Warrior",
                    "3x Broadway - Sturdy and Strong", "4x Darkwing Duck - Crime Fighter",
                    "2x Darkwing Duck - Shadowy Superhero", "4x Elinor - Renowned Diplomat",
                    "3x Jasmine - Fearless Princess", "3x Launchpad - Trusty Sidekick",
                    "4x Mushu - Stealthy Dragon", "2x Pegasus - Gift for Hercules",
                    "3x The Huntsman - On the Queen's Orders", "4x The Queen - Devious Disguise",
                    "4x Tod - All Alone", "4x Ursula - Deceiver", "4x Vixey - Forest Friend",
                    "2x White Rabbit - Late Again", "4x Strength of a Raging Fire",
                    "4x The Terror That Flaps in the Night",
                ],
            },
            {
                "label": "Top 8 — Dylan Brown", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "note": "Splashes 2x Aladdin - Doing His Part and 2x Rapunzel - Tower Defender.",
                "cards": [
                    "2x Aladdin - Doing His Part", "4x Angel - Experiment 624",
                    "1x Angela - Night Warrior", "4x Broadway - Sturdy and Strong",
                    "4x Darkwing Duck - Crime Fighter", "3x Darkwing Duck - Shadowy Superhero",
                    "4x Elinor - Renowned Diplomat", "3x Launchpad - Trusty Sidekick",
                    "4x Mushu - Stealthy Dragon", "2x Rapunzel - Tower Defender",
                    "3x The Queen - Devious Disguise", "4x Tod - All Alone", "4x Ursula - Deceiver",
                    "4x Vixey - Forest Friend", "4x White Rabbit - Late Again",
                    "2x He Hurled His Thunderbolt", "4x Strength of a Raging Fire",
                    "4x The Terror That Flaps in the Night",
                ],
            },
            {
                "label": "Top 8 — Alphos Parker-Acheson (⚠ only 55 cards captured)",
                "archetype": "Darkwing Duck Tempo — Toys/Gargoyle variant", "inks": "Emerald / Steel",
                "note": "Source post was labeled 'Incomplete Decklist'. Missing ~5 cards, likely the "
                        "song suite (no Strength of a Raging Fire etc. here). Distinctive: Lexington, "
                        "Omnidroid - V.8, Max Goof, Flynn Rider - Spectral Scoundrel.",
                "cards": [
                    "3x Aladdin - Doing His Part", "4x Angel - Experiment 624",
                    "2x Angela - Night Warrior", "4x Broadway - Sturdy and Strong",
                    "4x Darkwing Duck - Crime Fighter", "3x Darkwing Duck - Shadowy Superhero",
                    "4x Elinor - Renowned Diplomat", "2x Flynn Rider - Spectral Scoundrel",
                    "4x Launchpad - Trusty Sidekick", "1x Lexington - Small in Stature",
                    "4x Max Goof - Rebellious Teen", "2x Omnidroid - V.8",
                    "4x The Huntsman - On the Queen's Orders", "3x The Queen - Devious Disguise",
                    "4x Tod - All Alone", "3x Ursula - Deceiver", "4x Vixey - Forest Friend",
                ],
            },
            {
                "label": "Top 16 — Matthew Peddle", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "note": "Near-identical to Dave Solberg's (same Jasmine/Huntsman package).",
                "cards": [
                    "3x Angel - Experiment 624", "3x Angela - Night Warrior",
                    "4x Broadway - Sturdy and Strong", "4x Darkwing Duck - Crime Fighter",
                    "2x Darkwing Duck - Shadowy Superhero", "4x Elinor - Renowned Diplomat",
                    "2x Jasmine - Fearless Princess", "3x Launchpad - Trusty Sidekick",
                    "4x Mushu - Stealthy Dragon", "4x The Huntsman - On the Queen's Orders",
                    "3x The Queen - Devious Disguise", "4x Tod - All Alone", "4x Ursula - Deceiver",
                    "4x Vixey - Forest Friend", "3x White Rabbit - Late Again",
                    "1x He Hurled His Thunderbolt", "4x Strength of a Raging Fire",
                    "4x The Terror That Flaps in the Night",
                ],
            },
            {
                "label": "Top 16 — Shane Downey", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "note": "Dave Solberg's list with -1 Angel, +1 White Rabbit.",
                "cards": [
                    "2x Angel - Experiment 624", "3x Angela - Night Warrior",
                    "3x Broadway - Sturdy and Strong", "4x Darkwing Duck - Crime Fighter",
                    "2x Darkwing Duck - Shadowy Superhero", "4x Elinor - Renowned Diplomat",
                    "3x Jasmine - Fearless Princess", "3x Launchpad - Trusty Sidekick",
                    "4x Mushu - Stealthy Dragon", "2x Pegasus - Gift for Hercules",
                    "3x The Huntsman - On the Queen's Orders", "4x The Queen - Devious Disguise",
                    "4x Tod - All Alone", "4x Ursula - Deceiver", "4x Vixey - Forest Friend",
                    "3x White Rabbit - Late Again", "4x Strength of a Raging Fire",
                    "4x The Terror That Flaps in the Night",
                ],
            },
            {
                "label": "Top 16 — Tyler Novak (most divergent Emerald/Steel build)",
                "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "note": "Swaps in Kronk, Max Goof, Tod & Copper, Benja, and 1x Mother Knows Best.",
                "cards": [
                    "3x Angel - Experiment 624", "3x Angela - Night Warrior",
                    "2x Benja - Guardian of the Dragon Gem", "1x Broadway - Sturdy and Strong",
                    "4x Darkwing Duck - Crime Fighter", "3x Darkwing Duck - Shadowy Superhero",
                    "4x Elinor - Renowned Diplomat", "1x Kronk - Meat Hut Cook",
                    "4x Launchpad - Trusty Sidekick", "2x Max Goof - Rebellious Teen",
                    "3x Mushu - Stealthy Dragon", "1x Pegasus - Gift for Hercules",
                    "1x The Queen - Devious Disguise", "4x Tod - All Alone",
                    "3x Tod & Copper - Best of Friends", "4x Ursula - Deceiver",
                    "4x Vixey - Forest Friend", "2x White Rabbit - Late Again",
                    "2x He Hurled His Thunderbolt", "1x Mother Knows Best",
                    "4x Strength of a Raging Fire", "4x The Terror That Flaps in the Night",
                ],
            },
            {
                "label": "Top 16 — Robert Serpe (⚠ only 50 cards captured)",
                "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "note": "Song suite likely cropped from the source image. Unusual: Lenny - Toy "
                        "Binoculars, Violet Parr - Force Field Practice, and a 2-name Tod package.",
                "cards": [
                    "2x Angela - Night Warrior", "3x Broadway - Sturdy and Strong",
                    "4x Darkwing Duck - Crime Fighter", "1x Darkwing Duck - Shadowy Superhero",
                    "4x Elinor - Renowned Diplomat", "3x Jasmine - Fearless Princess",
                    "3x Launchpad - Trusty Sidekick", "2x Lenny - Toy Binoculars",
                    "3x Mushu - Stealthy Dragon", "3x Pegasus - Gift for Hercules",
                    "1x Rapunzel - Tower Defender", "4x The Queen - Devious Disguise",
                    "4x Tod - All Alone", "4x Tod - Clever Fox", "2x Ursula - Deceiver",
                    "3x Violet Parr - Force Field Practice", "4x Vixey - Forest Friend",
                ],
            },
            {
                "label": "Top 8 — Joseph Quigley", "archetype": "Amber/Steel", "inks": "Amber / Steel",
                "note": "Grandmother Willow / Hamm 2-drop core again, this time with a Stitch/Angel "
                        "singer package and Akood et Emuti. ⚠ transcribes to 61 — one count is off by "
                        "one in the source (which labeled it 'confirmed 60').",
                "cards": [
                    "2x Prince Charming - Protector of the Realm", "2x Tinker Bell - Giant Fairy",
                    "4x Gaston - Superior Archer", "4x Lilo & Stitch - Fun-Loving Friends",
                    "4x Stitch - Carefree Snowboarder", "1x Jasmine - Fearless Princess",
                    "4x Bambi - Ethereal Fawn", "2x Dale - Ready for His Shot",
                    "2x Tinker Bell - Generous Fairy", "4x Angel - Experiment 624",
                    "2x Benja - Guardian of the Dragon Gem", "1x Dr. Hamsterviel - Evil Observer",
                    "1x Lilo - Best Explorer Ever", "4x Angel - Siren Singer",
                    "4x Grandmother Willow - Ancient Advisor", "4x Hamm - Piggy Bank",
                    "4x Stitch - Protector of Frogs", "3x He Hurled His Thunderbolt",
                    "4x Akood et Emuti", "1x Ohana Means Family", "4x Strength of a Raging Fire",
                ],
            },
            {
                "label": "Top 16 — Ryan Ngoh", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst",
                "note": "Champion's shell built around card-selection engines (Junior Woodchuck "
                        "Guidebook, Eilonwy, Hades) instead of Rafiki / Besties / Nakoma.",
                "cards": [
                    "4x Cheshire Cat - Inexplicable", "1x Demona - Betrayer of the Clan",
                    "4x Demona - Scourge of the Wyvern Clan", "4x Dumbo - Ninth Wonder of the Universe",
                    "4x Eilonwy - Princess of Llyr", "4x Gaston - Superior Archer",
                    "4x Grandmother Willow - Ancient Advisor", "2x Hades - Looking for a Deal",
                    "4x Hamm - Piggy Bank", "4x Isis Vanderchill - Ice Queen of St. Canard",
                    "2x Luisa Madrigal - Confident Climber", "4x Luisa Madrigal - Pushing Through",
                    "2x Stitch - Carefree Surfer", "2x Sven - Leaping Reindeer",
                    "3x Tigger - Bouncing All the Way", "3x Ursula - Whisper of Vanessa",
                    "2x Violet Parr - Learning New Powers", "4x Junior Woodchuck Guidebook",
                    "3x The Horseman Strikes!",
                ],
            },
            {
                "label": "Top 16 — Jonathanz Williams", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst",
                "note": "Very close to the Champion's list.",
                "cards": [
                    "4x Besties, Assemble!", "4x The Horseman Strikes!",
                    "3x Cheshire Cat - Inexplicable", "2x Dale - Ready for His Shot",
                    "4x Demona - Scourge of the Wyvern Clan", "4x Gaston - Superior Archer",
                    "4x Grandmother Willow - Ancient Advisor", "4x Hamm - Piggy Bank",
                    "4x Isis Vanderchill - Ice Queen of St. Canard",
                    "3x Luisa Madrigal - Confident Climber", "4x Luisa Madrigal - Pushing Through",
                    "2x Mrs. Incredible - Super Stretchy", "2x Nakoma - Waiting Out the Storm",
                    "4x Rafiki - Mystical Fighter", "4x Stitch - Carefree Surfer",
                    "4x Tigger - Bouncing All the Way", "4x Ursula - Whisper of Vanessa",
                ],
            },
            {
                "label": "Top 16 — Mark Landers (⚠ transcribes to 62)",
                "archetype": "Pocahontas midrange", "inks": "Amber / Emerald",
                "note": "One 4x line is probably a 2x/3x. The only Amber/Emerald deck in the Top 16 — "
                        "no Darkwing, no Toy tribal; a Pocahontas/'protective' package.",
                "cards": [
                    "4x Aurora - Holding Court", "4x Bobby Zimuruski - Spray Cheese Kid",
                    "4x Dale - Ready for His Shot", "4x David - Protective Snowboarder",
                    "4x Elinor - Renowned Diplomat", "4x Grandmother Willow - Ancient Advisor",
                    "4x Mike Wazowski - Heroic Climber", "4x Nani - Stage Manager",
                    "4x Pluto - Friendly Pooch", "4x Pocahontas - Guiding the Tribe",
                    "4x Pocahontas - Peacekeeper", "4x Rapunzel - Tower Defender",
                    "2x Squeaks - Cozy Caterpillar", "4x The Queen - Regal Monarch",
                    "4x Thomas - Wide-Eyed Recruit", "4x Ursula - Deceiver",
                ],
            },
        ],
    },
    "europe-championship-2026": {
        "name": "Disney Lorcana Challenge — Europe Championship 2026",
        "date": "2026-09-13",
        "location": "Disney Hotel New York - The Art of Marvel, Disneyland Paris",
        "format": "EN Core Constructed",
        "source": "@disneylorcana (official) Instagram Top 16 decklist carousel posts, captured 2026-09-14; "
                  "exact event date inferred from the posts' relative timestamps, not stated directly.",
        "notes": (
            "Official @disneylorcana posts (not a community transcription like the NAC file), one slide "
            "per player, full typed decklists — low transcription risk. Amber/Emerald was the field's "
            "center of gravity (7 of 16, three different sub-archetypes): the champion's Aurora / "
            "Pocahontas Protective shell also took 4 more Top 16 slots (Diogo Araujo, Jannes Fischer, "
            "Mikael Mattila, Thibault Andrieu), plus one Items/Locations control build (Douglas "
            "Auchelie) and one Singer/Song build (Florian Bertin). Emerald/Steel Darkwing Duck Tempo "
            "— dominant at NAC 2026 — also had a strong showing here (4 of 16). Amber/Amethyst "
            "Madrigal Midrange placed twice. Amethyst/Emerald Discard / Ramp Control (the Asia "
            "Championship + FL CCQ archetype) made a single Top 16 appearance."
        ),
        "standings": [
            {"place": "Champion", "player": "Wojciech Złomek", "archetype": "Aurora / Pocahontas Protective", "inks": "Amber / Emerald"},
            {"place": "Top 16", "player": "Thiago Santana", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 16", "player": "Alessandro Danesi", "archetype": "Peter Pan / Scrooge Tempo", "inks": "Amethyst / Ruby"},
            {"place": "Top 16", "player": "Martin Schlusche", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst"},
            {"place": "Top 16", "player": "Diogo Araujo", "archetype": "Aurora / Pocahontas Protective", "inks": "Amber / Emerald"},
            {"place": "Top 16", "player": "Douglas Auchelie", "archetype": "Inkcaster Items/Locations Control", "inks": "Amber / Emerald"},
            {"place": "Top 16", "player": "Jannes Fischer", "archetype": "Aurora / Pocahontas Protective", "inks": "Amber / Emerald"},
            {"place": "Top 16", "player": "Mikael Mattila", "archetype": "Aurora / Pocahontas Protective", "inks": "Amber / Emerald"},
            {"place": "Top 16", "player": "Junior Franco", "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst"},
            {"place": "Top 16", "player": "Nils Jansen", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 16", "player": "Fabrice Bailleux", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 16", "player": "Konstantin Schall", "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel"},
            {"place": "Top 16", "player": "Thibault Andrieu", "archetype": "Aurora / Pocahontas Protective", "inks": "Amber / Emerald"},
            {"place": "Top 16", "player": "Daniele Stella", "archetype": "Mickey & Minnie Duo", "inks": "Emerald / Sapphire"},
            {"place": "Top 16", "player": "Alessandro Cavalli", "archetype": "Discard / Ramp Control", "inks": "Amethyst / Emerald"},
            {"place": "Top 16", "player": "Florian Bertin", "archetype": "Singer / Song Value", "inks": "Amber / Emerald"},
        ],
        "decklists": [
            {
                "label": "Champion — Wojciech Złomek",
                "archetype": "Aurora / Pocahontas Protective", "inks": "Amber / Emerald",
                "cards": [
                    "4x Aurora - Holding Court",
                    "4x Bobby Zimuruski - Spray Cheese Kid",
                    "4x Dale - Ready for His Shot",
                    "4x David - Protective Snowboarder",
                    "4x Elinor - Renowned Diplomat",
                    "4x Grandmother Willow - Ancient Advisor",
                    "2x Mickey Mouse - Expedition Leader",
                    "4x Mike Wazowski - Heroic Climber",
                    "2x Mowgli - Man Cub",
                    "1x Mushu - Stealthy Dragon",
                    "4x Nani - Stage Manager",
                    "4x Pluto - Friendly Pooch",
                    "4x Pocahontas - Guiding the Tribe",
                    "4x Pocahontas - Peacekeeper",
                    "2x The Queen - Devious Disguise",
                    "3x The Queen - Regal Monarch",
                    "3x Thomas - Wide-Eyed Recruit",
                    "3x Ursula - Deceiver",
                ],
            },
            {
                "label": "Top 16 — Thiago Santana",
                "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "cards": [
                    "3x Angela - Night Warrior",
                    "4x Darkwing Duck - Crime Fighter",
                    "4x Elinor - Renowned Diplomat",
                    "2x Flynn Rider - Spectral Scoundrel",
                    "3x Gaetan Moliere - Clever Burrower",
                    "3x Launchpad - Trusty Sidekick",
                    "4x Max Goof - Rebellious Teen",
                    "4x Mushu - Stealthy Dragon",
                    "4x Pegasus - Gift for Hercules",
                    "4x Strength of a Raging Fire",
                    "3x The Huntsman - On the Queen's Orders",
                    "4x The Queen - Devious Disguise",
                    "4x Tod - All Alone",
                    "4x Ursula - Deceiver",
                    "4x Vixey - Forest Friend",
                    "4x White Rabbit - Late Again",
                    "2x You Broke My Smolder",
                ],
            },
            {
                "label": "Top 16 — Alessandro Danesi",
                "archetype": "Peter Pan / Scrooge Tempo", "inks": "Amethyst / Ruby",
                "cards": [
                    "4x Cheshire Cat - Inexplicable",
                    "4x Dash Parr - Dodgeball Dynamo",
                    "4x Demona - Scourge of the Wyvern Clan",
                    "4x Dumbo - Ninth Wonder of the Universe",
                    "4x Jebidiah Farnsworth - Cookie",
                    "4x Junior Woodchuck Guidebook",
                    "1x Mrs. Incredible - Super Stretchy",
                    "1x Peter Pan - High Flyer",
                    "4x Peter Pan - Vine Duelist",
                    "3x Peter Pan & Tinker Bell - Fast Friends",
                    "4x Randall Boggs - Envious Coworker",
                    "4x Red Alert",
                    "4x Scrooge McDuck - Ghostly Ebenezer",
                    "2x Sisu - Daring Visitor",
                    "4x Ursula - Whisper of Vanessa",
                    "4x Vincenzo Santorini - On the Run",
                    "1x Violet Parr - Learning New Powers",
                    "4x Vixey - Expert Fisher",
                ],
            },
            {
                "label": "Top 16 — Martin Schlusche",
                "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst",
                "cards": [
                    "4x Agustin Madrigal - Exceptionally Kind",
                    "4x Besties, Assemble!",
                    "4x Cheshire Cat - Inexplicable",
                    "4x Demona - Scourge of the Wyvern Clan",
                    "4x Gaston - Superior Archer",
                    "4x Grandmother Willow - Ancient Advisor",
                    "4x Hamm - Piggy Bank",
                    "4x Isis Vanderchill - Ice Queen of St. Canard",
                    "2x Luisa Madrigal - Confident Climber",
                    "4x Luisa Madrigal - Pushing Through",
                    "4x Nakoma - Waiting Out the Storm",
                    "2x Ohana Means Family",
                    "4x Rafiki - Mystical Fighter",
                    "4x Stitch - Carefree Surfer",
                    "2x Sven - Leaping Reindeer",
                    "4x The Horseman Strikes!",
                    "2x Ursula - Whisper of Vanessa",
                ],
            },
            {
                "label": "Top 16 — Diogo Araujo",
                "archetype": "Aurora / Pocahontas Protective", "inks": "Amber / Emerald",
                "cards": [
                    "4x Aurora - Holding Court",
                    "4x Bobby Zimuruski - Spray Cheese Kid",
                    "4x Dale - Ready for His Shot",
                    "4x David - Protective Snowboarder",
                    "4x Elinor - Renowned Diplomat",
                    "4x Grandmother Willow - Ancient Advisor",
                    "2x Mickey Mouse - Expedition Leader",
                    "4x Mike Wazowski - Heroic Climber",
                    "4x Nani - Stage Manager",
                    "4x Pluto - Friendly Pooch",
                    "4x Pocahontas - Guiding the Tribe",
                    "4x Pocahontas - Peacekeeper",
                    "3x Rapunzel - Tower Defender",
                    "2x Squeaks - Cozy Caterpillar",
                    "1x The Queen - Devious Disguise",
                    "4x Thomas - Wide-Eyed Recruit",
                    "4x Ursula - Deceiver",
                ],
            },
            {
                "label": "Top 16 — Douglas Auchelie",
                "archetype": "Inkcaster Items/Locations Control", "inks": "Amber / Emerald",
                "cards": [
                    "4x Battering Ram",
                    "4x Buzz's Arm",
                    "4x Enigmatic Inkcaster",
                    "2x Improvise",
                    "3x Inscrutable Map",
                    "4x Malicious, Mean, and Scary",
                    "4x My Adventure Book",
                    "4x Piercing Attack",
                    "4x Potion of Malice",
                    "4x Raging Storm",
                    "2x Sabotage",
                    "2x Scout Ahead",
                    "4x Strange Things",
                    "4x Strike a Good Match",
                    "4x The Horseman Strikes!",
                    "2x Trust In Me",
                    "1x Ursula's Shell Necklace",
                    "4x Zootopia - Tundratown",
                ],
            },
            {
                "label": "Top 16 — Jannes Fischer",
                "archetype": "Aurora / Pocahontas Protective", "inks": "Amber / Emerald",
                "cards": [
                    "4x Aurora - Holding Court",
                    "4x Bobby Zimuruski - Spray Cheese Kid",
                    "3x Dale - Ready for His Shot",
                    "2x David - Protective Snowboarder",
                    "4x Elinor - Renowned Diplomat",
                    "2x Finnick - Tiny Terror",
                    "4x Grandmother Willow - Ancient Advisor",
                    "4x Meilin Lee - Lead Vocalist",
                    "3x Mickey Mouse - Amber Champion",
                    "4x Mickey Mouse - Expedition Leader",
                    "4x Mike Wazowski - Heroic Climber",
                    "1x Mowgli - Man Cub",
                    "4x Nani - Stage Manager",
                    "3x Pluto - Friendly Pooch",
                    "4x Pocahontas - Guiding the Tribe",
                    "4x Pocahontas - Peacekeeper",
                    "1x Rapunzel - Tower Defender",
                    "2x Under the Sea",
                    "3x Ursula - Deceiver",
                ],
            },
            {
                "label": "Top 16 — Mikael Mattila",
                "archetype": "Aurora / Pocahontas Protective", "inks": "Amber / Emerald",
                "cards": [
                    "4x Aurora - Holding Court",
                    "4x Bobby Zimuruski - Spray Cheese Kid",
                    "4x Dale - Ready for His Shot",
                    "3x David - Protective Snowboarder",
                    "4x Elinor - Renowned Diplomat",
                    "2x Finnick - Tiny Terror",
                    "4x Grandmother Willow - Ancient Advisor",
                    "2x Mickey Mouse - Expedition Leader",
                    "4x Mike Wazowski - Heroic Climber",
                    "4x Nani - Stage Manager",
                    "4x Pluto - Friendly Pooch",
                    "2x Pocahontas - Finding the Way",
                    "4x Pocahontas - Guiding the Tribe",
                    "4x Pocahontas - Peacekeeper",
                    "3x Rapunzel - Tower Defender",
                    "4x Thomas - Wide-Eyed Recruit",
                    "4x Ursula - Deceiver",
                ],
            },
            {
                "label": "Top 16 — Junior Franco",
                "archetype": "Madrigal Midrange", "inks": "Amber / Amethyst",
                "cards": [
                    "2x Agustin Madrigal - Exceptionally Kind",
                    "4x Besties, Assemble!",
                    "4x Cheshire Cat - Inexplicable",
                    "4x Demona - Scourge of the Wyvern Clan",
                    "2x Dumbo - The Flying Elephant",
                    "2x Eilonwy - Princess of Llyr",
                    "4x Gaston - Superior Archer",
                    "4x Grandmother Willow - Ancient Advisor",
                    "4x Hamm - Piggy Bank",
                    "4x Isis Vanderchill - Ice Queen of St. Canard",
                    "2x Luisa Madrigal - Confident Climber",
                    "3x Luisa Madrigal - Pushing Through",
                    "4x Nakoma - Waiting Out the Storm",
                    "2x Ohana Means Family",
                    "3x Rafiki - Mystical Fighter",
                    "4x Stitch - Carefree Surfer",
                    "1x Sven - Leaping Reindeer",
                    "4x The Horseman Strikes!",
                    "3x Tigger - Bouncing All the Way",
                ],
            },
            {
                "label": "Top 16 — Nils Jansen",
                "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "cards": [
                    "2x Aladdin - Doing His Part",
                    "3x Angel - Experiment 624",
                    "3x Angela - Night Warrior",
                    "4x Broadway - Sturdy and Strong",
                    "4x Darkwing Duck - Crime Fighter",
                    "2x Darkwing Duck - Shadowy Superhero",
                    "4x Elinor - Renowned Diplomat",
                    "4x Launchpad - Trusty Sidekick",
                    "2x Mother Knows Best",
                    "4x Mushu - Stealthy Dragon",
                    "2x Rapunzel - Tower Defender",
                    "4x Strength of a Raging Fire",
                    "2x The Huntsman - On the Queen's Orders",
                    "2x The Queen - Devious Disguise",
                    "3x The Terror That Flaps in the Night",
                    "4x Tod - All Alone",
                    "4x Ursula - Deceiver",
                    "4x Vixey - Forest Friend",
                    "3x White Rabbit - Late Again",
                ],
            },
            {
                "label": "Top 16 — Fabrice Bailleux",
                "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "cards": [
                    "4x Aladdin - Doing His Part",
                    "4x Angel - Experiment 624",
                    "3x Angela - Night Warrior",
                    "4x Broadway - Sturdy and Strong",
                    "2x Darkwing Duck - Crime Fighter",
                    "4x Elinor - Renowned Diplomat",
                    "3x Hamish, Hubert & Harris - Troublemaking Triplets",
                    "2x Max Goof - Rebellious Teen",
                    "4x Mushu - Stealthy Dragon",
                    "4x Pegasus - Gift for Hercules",
                    "2x Rapunzel - Tower Defender",
                    "4x Strength of a Raging Fire",
                    "2x The Queen - Devious Disguise",
                    "2x The Terror That Flaps in the Night",
                    "4x Tod - All Alone",
                    "4x Ursula - Deceiver",
                    "4x Vixey - Forest Friend",
                    "4x White Rabbit - Late Again",
                ],
            },
            {
                "label": "Top 16 — Konstantin Schall",
                "archetype": "Darkwing Duck Tempo", "inks": "Emerald / Steel",
                "cards": [
                    "3x Angel - Experiment 624",
                    "3x Angela - Night Warrior",
                    "4x Broadway - Sturdy and Strong",
                    "4x Darkwing Duck - Crime Fighter",
                    "2x Darkwing Duck - Shadowy Superhero",
                    "4x Elinor - Renowned Diplomat",
                    "4x He Hurled His Thunderbolt",
                    "4x Launchpad - Trusty Sidekick",
                    "4x Mushu - Stealthy Dragon",
                    "2x Rapunzel - Tower Defender",
                    "4x Strength of a Raging Fire",
                    "3x The Queen - Devious Disguise",
                    "4x The Terror That Flaps in the Night",
                    "4x Tod - All Alone",
                    "4x Ursula - Deceiver",
                    "4x Vixey - Forest Friend",
                    "3x White Rabbit - Late Again",
                ],
            },
            {
                "label": "Top 16 — Thibault Andrieu",
                "archetype": "Aurora / Pocahontas Protective", "inks": "Amber / Emerald",
                "cards": [
                    "4x Aurora - Holding Court",
                    "4x Bobby Zimuruski - Spray Cheese Kid",
                    "4x Dale - Ready for His Shot",
                    "4x David - Protective Snowboarder",
                    "4x Elinor - Renowned Diplomat",
                    "4x Grandmother Willow - Ancient Advisor",
                    "1x Mickey Mouse - Amber Champion",
                    "2x Mickey Mouse - Expedition Leader",
                    "4x Mike Wazowski - Heroic Climber",
                    "4x Nani - Stage Manager",
                    "4x Pluto - Friendly Pooch",
                    "4x Pocahontas - Guiding the Tribe",
                    "4x Pocahontas - Peacekeeper",
                    "3x Rapunzel - Tower Defender",
                    "2x Squeaks - Cozy Caterpillar",
                    "4x Thomas - Wide-Eyed Recruit",
                    "4x Ursula - Deceiver",
                ],
            },
            {
                "label": "Top 16 — Daniele Stella",
                "archetype": "Mickey & Minnie Duo", "inks": "Emerald / Sapphire",
                "cards": [
                    "4x Donald Duck - Perfect Gentleman",
                    "4x Dr. Bushroot - Evil Botanist",
                    "4x Hades - Infernal Schemer",
                    "4x Hades - Meticulous Schemer",
                    "4x Mickey Mouse - Bob Cratchit",
                    "4x Mickey Mouse - Detective",
                    "4x Mickey Mouse & Minnie Mouse - Adventuring Duo",
                    "4x Milo Thatch - Getting His Hands Dirty",
                    "4x Minnie Mouse - Curious Adventurer",
                    "4x Minnie Mouse - Practical Traveler",
                    "4x Minnie Mouse - Spinning Skater",
                    "4x Scuttle - Birdbrained",
                    "4x Strike a Good Match",
                    "4x Tod - Clever Fox",
                    "4x Winifred - Exasperated Elephant",
                ],
            },
            {
                "label": "Top 16 — Alessandro Cavalli (⚠ transcribes to 59)",
                "archetype": "Discard / Ramp Control", "inks": "Amethyst / Emerald",
                "note": ('Same Lyle Tiberius Rourke / Retro Evolution Device / Prince Phillip - Vanquisher of Foes / Malicious, Mean, and Scary shell that won the Asia Championship and swept the FL CCQ final (see event asia-championship-2026) — now also a Top 16 finish in Europe, a third EN-Core region. One line is likely a 2x/3x undercounted by one from the source image.'),
                "cards": [
                    "3x Aladdin - Doing His Part",
                    "4x Aladdin - Prince Ali",
                    "4x Aladdin & Genie - Mischievous Pals",
                    "2x Chernabog - Unnatural Force",
                    "4x Demona - Scourge of the Wyvern Clan",
                    "1x Elsa - Exploring the Unknown",
                    "4x Hades - Looking for a Deal",
                    "4x Junior Woodchuck Guidebook",
                    "1x Lenny - Toy Binoculars",
                    "2x Lyle Tiberius Rourke - Adventurer for Hire",
                    "4x Malicious, Mean, and Scary",
                    "1x Max Goof - Rebellious Teen",
                    "4x Milo Thatch - Getting His Hands Dirty",
                    "1x Mother Knows Best",
                    "4x Prince Phillip - Vanquisher of Foes",
                    "3x Rapunzel - Tower Defender",
                    "4x Retro Evolution Device",
                    "1x Second Star to the Right",
                    "1x Sven - Leaping Reindeer",
                    "3x The Huntsman - On the Queen's Orders",
                    "4x Tod - Clever Fox",
                ],
            },
            {
                "label": "Top 16 — Florian Bertin",
                "archetype": "Singer / Song Value", "inks": "Amber / Emerald",
                "cards": [
                    "4x Akood et Emuti",
                    "2x Alan-a-Dale - Loyal Bard",
                    "4x Angel - Siren Singer",
                    "4x Ariel - Ethereal Voice",
                    "4x Chernabog - Unnatural Force",
                    "4x Circle of Life",
                    "3x Lenny - Toy Binoculars",
                    "4x Malicious, Mean, and Scary",
                    "2x Max Goof - Chart Topper",
                    "2x Max Goof - Rebellious Teen",
                    "4x Meilin Lee - Losing Control",
                    "4x Milo Thatch - Getting His Hands Dirty",
                    "4x Prince Phillip - Vanquisher of Foes",
                    "4x Strike a Good Match",
                    "3x To Wither a Flower",
                    "4x Tod - Clever Fox",
                    "4x Ursula - Vanessa",
                ],
            },
        ],
    },
}


def _match_event(query: str) -> list[str]:
    """Slug keys whose slug or name matches the query (case/space-insensitive
    substring). Exact slug match short-circuits to a single result."""
    q = _slug(query)
    if q in TOURNAMENTS:
        return [q]
    hits = []
    for key, t in TOURNAMENTS.items():
        if q and (q in key or q in _slug(t["name"])):
            hits.append(key)
    return hits


def list_events() -> str:
    lines = ["Full standings + decklists are available for these events "
             "(call `get_meta(event=\"<key or name fragment>\")`):", ""]
    for key, t in TOURNAMENTS.items():
        n_lists = len(t["decklists"])
        lines.append(f"- **{key}** — {t['name']} ({t['date']}, {t['format'].split('(')[0].strip()}) "
                     f"— {len(t['standings'])} placements, {n_lists} decklist(s)")
    return "\n".join(lines)


def format_event(query: str) -> str:
    keys = _match_event(query)
    if not keys:
        return (f'No tournament matches "{query}".\n\n' + list_events())
    if len(keys) > 1:
        opts = ", ".join(keys)
        return f'"{query}" matches several events: {opts}. Call again with one of those keys.'

    t = TOURNAMENTS[keys[0]]
    out = [
        f"# {t['name']}",
        f"{t['date']} · {t['location']} · **{t['format']}**",
        f"Source: {t['source']}",
        "",
        t["notes"],
        "",
        "## Final standings",
        "| Place | Player | Archetype | Inks |",
        "|---|---|---|---|",
    ]
    for s in t["standings"]:
        out.append(f"| {s['place']} | {s['player']} | {s['archetype']} | {s['inks']} |")
    out.append("")
    out.append("## Decklists")
    for d in t["decklists"]:
        out.append("")
        out.append(f"### {d['label']} — {d['inks']} · {d['archetype']}")
        if d.get("note"):
            out.append(f"_{d['note']}_")
        total = sum(_leading_count(c) for c in d["cards"])
        out.append(f"```")
        out.extend(d["cards"])
        out.append(f"```")
        out.append(f"({total} cards)" if total else "")
    return "\n".join(l for l in out if l is not None)


def _leading_count(line: str) -> int:
    head = line.split("x", 1)[0].strip()
    return int(head) if head.isdigit() else 0
