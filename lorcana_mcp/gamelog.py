"""Read a duels.ink game log and turn it into a game review with tips.

duels.ink has no export or replay API, but its in-game log panel can be
copied as plain text. This module parses that text (one event per line, or
the same events run together on a single line, which is what you get when
the copy loses its line breaks). It replays the game to track lore, ink, your
hand, both boards and who banished what, and then looks for the usual
mistakes: missed ink, unspent ink, questing into a challenge, unanswered
questers, sweepers into a wide board, and inking the wrong card.

The log only shows what both players could see. The opponent's hand is
hidden, so tips about the opponent describe what they revealed. Activated
ability costs and ink-drop payments aren't itemised in the log, so the ink
math is "card costs paid", not a perfect ink ledger.
"""
from __future__ import annotations

import copy
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

YOU, OPP = "you", "opp"
_SIDE = {"You": YOU, "Your": YOU, "Opponent": OPP, "Opponent's": OPP}


def _other(side: str) -> str:
    return OPP if side == YOU else YOU


# ── Normalising the pasted text ────────────────────────────────────────────────

# A run-together log (copy lost its newlines) has every event glued to the
# next: "...Advisor was banishedOpponent gained 45 seconds...". Each event
# starts with a capital letter right after a lowercase letter, ')', ']', '!',
# a digit, or a closing quote (a quote that doesn't follow a space). Card names
# almost never have that shape internally; the exceptions (McDuck, LeFou,
# MacGuffin) are excluded.
_GLUE = re.compile(r"(?:(?<=[a-z\)\]!\d])|(?<=\S\"))(?<!Mc)(?<!Mac)(?<!\bLe)(?=[A-Z])")
_TURN_HDR = re.compile(r"\s*(--- Turn \d+ ---)\s*")


def split_log_lines(text: str) -> list[str]:
    """Split a pasted duels.ink log into event lines, whether or not the copy
    kept its line breaks."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    raw = [l.strip() for l in text.split("\n") if l.strip()]
    # A real multi-line copy has dozens of lines; a glued one has a handful
    # of very long ones.
    glued = len(raw) < 15 and len(text) > 400
    out: list[str] = []
    for line in raw:
        line = _TURN_HDR.sub(r"\n\1\n", line)
        for part in line.split("\n"):
            part = part.strip()
            if not part:
                continue
            if glued:
                out.extend(p.strip() for p in _GLUE.split(part) if p.strip())
            else:
                out.append(part)
    return out


# ── Card data ──────────────────────────────────────────────────────────────────

CardIndex = dict  # fullName -> LorcanaJSON card dict


def default_card_index() -> CardIndex:
    from .api import fetch_lorcana_json
    idx: CardIndex = {}
    for c in fetch_lorcana_json():
        name = c.get("fullName")
        if name and name not in idx:
            idx[name] = c
    return idx


def split_card_list(s: str, known: CardIndex) -> list[str]:
    """Split "A, B, Malicious, Mean, and Scary" into card names. Commas inside
    card names are why this can't be a plain split: tokens are re-joined while
    the joined text is a prefix of a known card name."""
    toks = [t.strip() for t in s.split(", ")]
    out: list[str] = []
    i = 0
    while i < len(toks):
        best_j, cur = i, toks[i]
        acc = toks[i]
        for j in range(i + 1, len(toks)):
            acc = acc + ", " + toks[j]
            if acc in known:
                best_j, cur = j, acc
        out.append(cur)
        i = best_j + 1
    return out


# ── Game state ─────────────────────────────────────────────────────────────────

@dataclass
class TurnRec:
    number: int
    side: str
    inked: list[str] = field(default_factory=list)
    played: list[tuple[str, int]] = field(default_factory=list)   # (card, ink paid)
    sang: list[tuple[str, str]] = field(default_factory=list)     # (song, singer)
    quests: list[tuple[str, int]] = field(default_factory=list)
    challenges: list[dict] = field(default_factory=list)
    banished_mine: list[tuple[str, str]] = field(default_factory=list)    # side's own losses (card, cause)
    banished_theirs: list[tuple[str, str]] = field(default_factory=list)  # kills of the other side
    lore_after: dict = field(default_factory=dict)
    ink_after: int = 0
    hand_after: Counter | None = None
    drew: int = 0


@dataclass
class State:
    lore: dict = field(default_factory=lambda: {YOU: 0, OPP: 0})
    ink: dict = field(default_factory=lambda: {YOU: 0, OPP: 0})
    board: dict = field(default_factory=lambda: {YOU: Counter(), OPP: Counter()})
    hand: Counter = field(default_factory=Counter)        # yours only
    hand_known: bool = False
    drawn: dict = field(default_factory=lambda: {YOU: 0, OPP: 0})
    revealed_opp: Counter = field(default_factory=Counter)
    seen_you: Counter = field(default_factory=Counter)
    last_owner: dict = field(default_factory=dict)
    quest_lore_by_card: dict = field(default_factory=lambda: {YOU: Counter(), OPP: Counter()})
    turns: list[TurnRec] = field(default_factory=list)
    cause: str = ""
    dmg_source: dict = field(default_factory=dict)        # target -> last damage source this turn
    winner: str | None = None
    first_player: str | None = None
    mulligan: dict = field(default_factory=dict)
    starting_hand: list[str] = field(default_factory=list)
    undo_count: int = 0
    banish_log: list = field(default_factory=list)
    quest_log: list = field(default_factory=list)   # (turn, side, card, gain)
    unparsed: int = 0


_TOP_ACTION = re.compile(
    r"^(You|Opponent) (played|shifted|sang|quested|added|activated|challenged) "
)


class GameLog:
    """Replays a duels.ink log line by line."""

    def __init__(self, lines: list[str], cards: CardIndex):
        self.lines = lines
        self.cards = cards
        self.s = State()
        self._snapshot: State | None = None
        self._free_next: set[str] = set()
        self._hint: dict = {}

    # helpers
    @property
    def cur(self) -> TurnRec | None:
        return self.s.turns[-1] if self.s.turns else None

    def _owner_of(self, name: str, prefer: str | None = None) -> str | None:
        b = self.s.board
        has = [sd for sd in (YOU, OPP) if b[sd][name] > 0]
        if len(has) == 1:
            return has[0]
        if len(has) == 2:
            return prefer or self.s.last_owner.get(name)
        return self.s.last_owner.get(name)

    def _enter_play(self, side: str, name: str) -> None:
        self.s.board[side][name] += 1
        self.s.last_owner[name] = side
        if side == OPP:
            self.s.revealed_opp[name] += 1
        else:
            self.s.seen_you[name] += 1

    def _hand_remove(self, name: str) -> None:
        if self.s.hand[name] > 0:
            self.s.hand[name] -= 1
            if self.s.hand[name] == 0:
                del self.s.hand[name]

    def _lore_set(self, side: str, new: int) -> None:
        self.s.lore[side] = new

    def run(self) -> State:
        for line in self.lines:
            self._line(line)
        self._close_turn()
        return self.s

    def _close_turn(self) -> None:
        t = self.cur
        if t is None:
            return
        t.lore_after = dict(self.s.lore)
        t.ink_after = self.s.ink[t.side]
        if t.side == YOU and self.s.hand_known:
            t.hand_after = Counter(self.s.hand)

    # main dispatcher
    def _line(self, line: str) -> None:  # noqa: C901 — one flat dispatcher reads best here
        s = self.s
        if re.match(r'^(You|Opponent): "', line):
            return  # chat

        m = _TOP_ACTION.match(line)
        if m and " | " not in line:
            self._hint = {}
            card = None
            pm = re.match(r"^(?:You|Opponent) played (.+?) \(cost", line)
            if pm:
                card = pm.group(1)
            if not (card and card in self._free_next):
                self._snapshot = copy.deepcopy(s)
            if card:
                self._free_next.discard(card)

        if line.startswith("You took back their action") or line.startswith("Opponent took back their action"):
            if self._snapshot is not None:
                undo = s.undo_count + 1
                self.s = copy.deepcopy(self._snapshot)
                self.s.undo_count = undo
                self._snapshot = None
            return

        if m2 := re.match(r"^Your starting hand: (.+)$", line):
            s.starting_hand = split_card_list(m2.group(1), self.cards)
            s.hand = Counter(s.starting_hand)
            s.hand_known = True
            s.seen_you.update(s.starting_hand)
            return
        if m2 := re.match(r"^You mulliganed (\d+) cards?(?:: (.+?)\. Drew: (.+))?$", line):
            n = int(m2.group(1))
            out = split_card_list(m2.group(2), self.cards) if m2.group(2) else []
            new = split_card_list(m2.group(3), self.cards) if m2.group(3) else []
            for c in out:
                self._hand_remove(c)
            s.hand.update(new)
            s.seen_you.update(new)
            s.mulligan[YOU] = {"count": n, "out": out, "in": new}
            return
        if m2 := re.match(r"^Opponent mulliganed (\d+) cards?", line):
            s.mulligan[OPP] = {"count": int(m2.group(1))}
            return
        if m2 := re.match(r"^--- Turn (\d+) ---$", line):
            self._close_turn()
            s.turns.append(TurnRec(number=int(m2.group(1)), side=YOU))
            s.dmg_source = {}
            return
        if m2 := re.match(r"^(Your|Opponent's) turn begins$", line):
            side = _SIDE[m2.group(1)]
            if self.cur is None:
                s.turns.append(TurnRec(number=1, side=side))
            self.cur.side = side
            if s.first_player is None:
                s.first_player = side
            return

        # Draws
        if m2 := re.match(r"^(You|Opponent) drew (.+)$", line):
            side = _SIDE[m2.group(1)]
            what = m2.group(2)
            if mm := re.match(r"^(\d+) cards?(?:: (.+))?$", what):
                n = int(mm.group(1))
                if side == YOU and mm.group(2):
                    names = split_card_list(mm.group(2), self.cards)
                    s.hand.update(names)
                    s.seen_you.update(names)
            elif what == "a card":
                n = 1
            else:
                n = 1
                if side == YOU:
                    s.hand[what] += 1
                    s.seen_you[what] += 1
            s.drawn[side] += n
            if self.cur:
                if self.cur.side == side:
                    self.cur.drew += n
            return

        if m2 := re.match(r"^(You|Opponent) added (.+) to ink$", line):
            side, card = _SIDE[m2.group(1)], m2.group(2)
            s.ink[side] += 1
            if side == YOU:
                self._hand_remove(card)
                s.seen_you[card] += 0
            else:
                s.revealed_opp[card] += 1
            if self.cur and self.cur.side == side:
                self.cur.inked.append(card)
            return

        if m2 := re.match(r"^(You|Opponent) played (.+?) \(cost (\d+)(?: → (\d+))?(?:, [^)]*)?\)$", line):
            side, card = _SIDE[m2.group(1)], m2.group(2)
            paid = int(m2.group(4) if m2.group(4) is not None else m2.group(3))
            if side == YOU:
                self._hand_remove(card)
            ctype = (self.cards.get(card) or {}).get("type", "")
            if ctype in ("Character", "Item", "Location"):
                self._enter_play(side, card)
            elif side == OPP:
                s.revealed_opp[card] += 1
            s.cause = card
            if self.cur and self.cur.side == side:
                self.cur.played.append((card, paid))
            return

        if m2 := re.match(r"^(You|Opponent) shifted (.+?) onto (.+?) \(Shift (\d+)\)$", line):
            side, card, base = _SIDE[m2.group(1)], m2.group(2), m2.group(3)
            if side == YOU:
                self._hand_remove(card)
            if s.board[side][base] > 0:
                s.board[side][base] -= 1
            self._enter_play(side, card)
            s.cause = card
            if self.cur and self.cur.side == side:
                self.cur.played.append((card, int(m2.group(4))))
            return

        if m2 := re.match(r"^(You|Opponent) sang (.+?) with (.+)$", line):
            side, song, singer = _SIDE[m2.group(1)], m2.group(2), m2.group(3)
            if side == YOU:
                self._hand_remove(song)
            else:
                s.revealed_opp[song] += 1
            s.cause = song
            if self.cur and self.cur.side == side:
                self.cur.sang.append((song, singer))
            return

        if m2 := re.match(r"^(You|Opponent) quested with (.+?) \(\+(\d+) \[LORE\], (\d+) -> (\d+)\)$", line):
            side, card, gain = _SIDE[m2.group(1)], m2.group(2), int(m2.group(3))
            self._lore_set(side, int(m2.group(5)))
            s.quest_lore_by_card[side][card] += gain
            s.quest_log.append((self.cur.number if self.cur else 0, side, card, gain))
            if self.cur:
                self.cur.quests.append((card, gain))
            return

        if m2 := re.match(r"^(You|Opponent) challenged (.+?) with (.+?) \| (.+)$", line):
            side, defender, attacker, detail = _SIDE[m2.group(1)], m2.group(2), m2.group(3), m2.group(4)
            left, _, right = detail.partition(", took ")
            d_dead = "banished!" in left
            a_dead = "banished!" in right
            s.cause = attacker
            s.dmg_source[defender] = attacker
            s.dmg_source[attacker] = defender
            self._hint = {defender: _other(side), attacker: side}
            if self.cur:
                self.cur.challenges.append({
                    "side": side, "attacker": attacker, "defender": defender,
                    "attacker_died": a_dead, "defender_died": d_dead,
                })
            return
        if re.match(r"^(You|Opponent) challenged ", line):
            return  # header line; the " | " detail line follows

        if m2 := re.match(r"^(.+?) dealt (\d+) damage to (.+)$", line):
            s.dmg_source[m2.group(3)] = m2.group(1)
            return

        if m2 := re.match(r"^(.+?) was banished(?: \(.*\))?$", line):
            card = m2.group(1)
            hint = self._hint.get(card)
            active = self.cur.side if self.cur else None
            owner = hint or self._owner_of(card, prefer=_other(active) if active else None)
            if owner is None:
                owner = _other(active) if active else OPP
            if s.board[owner][card] > 0:
                s.board[owner][card] -= 1
            s.last_owner[card] = owner
            cause = s.dmg_source.get(card) or s.cause or "?"
            kind = "challenge" if hint else "effect"
            s.banish_log.append({"turn": self.cur.number if self.cur else 0, "card": card,
                                 "owner": owner, "cause": cause, "kind": kind})
            if self.cur:
                if owner == self.cur.side:
                    self.cur.banished_mine.append((card, cause))
                else:
                    self.cur.banished_theirs.append((card, cause))
            return

        if m2 := re.match(r"^(.+?) returned to (your|their|opponent's) hand$", line):
            card = m2.group(1)
            side = YOU if m2.group(2) == "your" else OPP
            if s.board[side][card] > 0:
                s.board[side][card] -= 1
            if side == YOU:
                s.hand[card] += 1
            return

        if m2 := re.match(r"^(.+?)'s .+? Played (.+) for free$", line):
            self._free_next.add(m2.group(2))
            return
        if m2 := re.match(r"^(.+?)'s .+? Returned (.+?) from discard to hand$", line):
            card = m2.group(2)
            owner = self._owner_of(m2.group(1)) or (self.cur.side if self.cur else YOU)
            if owner == YOU:
                s.hand[card] += 1
            return
        if m2 := re.match(r"^You revealed (.+?) ?\((.+)\) - put into hand$", line):
            s.hand[m2.group(1)] += 1
            s.seen_you[m2.group(1)] += 1
            return
        if m2 := re.match(r"^(You|Opponent) discarded (.+)$", line):
            side, card = _SIDE[m2.group(1)], m2.group(2)
            if side == YOU:
                self._hand_remove(card)
            else:
                s.revealed_opp[card] += 1
            return

        if m2 := re.match(r"^(You|Opponent) won with (\d+)", line):
            s.winner = _SIDE[m2.group(1)]
            self._lore_set(s.winner, max(s.lore[s.winner], int(m2.group(2))))
            return

        # Lore from abilities/locations: "(a -> b)" without a quest.
        if mm := re.search(r"\((\d+) -> (\d+)\)", line):
            a, b = int(mm.group(1)), int(mm.group(2))
            side = None
            if "grants You " in line:
                side = YOU
            elif "grants Opponent " in line:
                side = OPP
            else:
                src = re.match(r"^(?:Set step: )?(.+?)'s ", line)
                if src:
                    side = self._owner_of(src.group(1))
            if side is None or s.lore[side] != a:
                matches = [sd for sd in (YOU, OPP) if s.lore[sd] == a]
                if len(matches) == 1:
                    side = matches[0]
            if side:
                self._lore_set(side, b)
            return

        # Known noise
        if re.match(r"^(Ready step|Set step|Draw step|Game started|Your timer|Opponent's timer|"
                    r"You gained|Opponent gained|You ended|Opponent ended|You chose|Opponent chose|"
                    r"You reordered|Opponent reordered|Moved \d+ damage|Opponent looked|You looked|"
                    r"You activated|Opponent activated)", line):
            return
        if "'s " in line:
            return  # ability narration ("X's ABILITY deals 2 damage") — effects show up on their own lines
        s.unparsed += 1


# ── Analysis ───────────────────────────────────────────────────────────────────

def _deck_counts(deck_text: str) -> Counter:
    from .deck import parse_deck_list
    c: Counter = Counter()
    for qty, name in parse_deck_list(deck_text):
        c[name.strip()] += qty
    return c


_STALE_HEADING = re.compile(r"\b(retired|archived|old|previous|superseded|budget|alt)\b", re.I)


def read_deck_file(path: str) -> str:
    """Pull a deck list out of a file such as a deck .md.

    Deck notes often keep several lists (an official reference list, the
    current import list, retired versions). Picks the first code block made
    entirely of "4x Card Name" lines whose nearest heading mentions "import"
    and isn't marked retired/archived/old/budget. Falls back to the first
    such block of any heading, then to every list-shaped line in the file."""
    text = open(path, encoding="utf-8").read()
    line_re = re.compile(r"^\s*\d+\s*[xX]?\s+\S")
    blocks = []
    for m in re.finditer(r"```[^\n]*\n(.*?)```", text, re.S):
        body = m.group(1)
        if not body.strip() or not all(line_re.match(l) for l in body.strip().splitlines()):
            continue
        heads = re.findall(r"^#+\s*(.+)$", text[:m.start()], re.M)
        blocks.append((heads[-1] if heads else "", body))
    for head, body in blocks:
        if "import" in head.lower() and not _STALE_HEADING.search(head):
            return body
    fresh = [b for h, b in blocks if not _STALE_HEADING.search(h)]
    if fresh:
        return fresh[0]
    if blocks:
        return blocks[0][1]
    return "\n".join(l for l in text.splitlines() if line_re.match(l) and not l.lstrip().startswith("|"))


def _guess_opponent_deck(revealed: Counter, inks: list[str]) -> tuple[str, str, int, int] | None:
    """Best-overlap known tournament list, restricted to the opponent's two
    most-revealed inks when those are known."""
    from .tournaments import TOURNAMENTS
    names = set(revealed)
    if not names:
        return None
    want = {i.lower() for i in inks[:2]}
    best = None
    for ev in TOURNAMENTS.values():
        for d in ev["decklists"]:
            pair = {p.strip().lower() for p in d["inks"].split("/")}
            if len(want) == 2 and pair != want:
                continue
            listed = {l.split("x ", 1)[1].strip() for l in d["cards"] if "x " in l}
            hit = len(names & listed)
            if best is None or hit > best[2]:
                best = (f"{d['inks']} {d['archetype']}", f"{ev['name']} — {d['label']}", hit, len(names))
    return best if best and best[2] >= 3 else None


def _colors(card: dict | None) -> list[str]:
    if not card:
        return []
    col = card.get("color") or ""
    return [c for c in col.split("-") if c]


def analyze_game_log(log_text: str, deck_text: str = "",
                     card_index: CardIndex | None = None) -> dict:
    """Parse a duels.ink log and compute stats + tips. Returns a dict that
    format_game_review renders."""
    cards = card_index if card_index is not None else default_card_index()
    lines = split_log_lines(log_text)
    if not any(l.startswith("--- Turn") for l in lines):
        return {"error": "This doesn't look like a duels.ink game log (no '--- Turn N ---' lines)."}
    g = GameLog(lines, cards)
    s = g.run()

    you_turns = [t for t in s.turns if t.side == YOU]
    opp_turns = [t for t in s.turns if t.side == OPP]
    tips: list[str] = []
    moments: list[str] = []

    def cost(n):
        return (cards.get(n) or {}).get("cost")

    def inkable(n):
        return bool((cards.get(n) or {}).get("inkwell"))

    def ctype(n):
        return (cards.get(n) or {}).get("type", "")

    # 1. Your losses in a single opponent turn, and to removal effects overall.
    for t in s.turns:
        losses = t.banished_theirs if t.side == OPP else []
        if len(losses) >= 2:
            causes = Counter(c for _, c in losses)
            cause_txt = ", ".join(f"{c} ×{n}" if n > 1 else c for c, n in causes.most_common())
            moments.append(f"Turn {t.number}: opponent killed {len(losses)} of your characters "
                           f"({', '.join(n for n, _ in losses)}) via {cause_txt}.")
    your_deaths = [b for b in s.banish_log if b["owner"] == YOU]
    effect_kills = Counter(b["cause"] for b in your_deaths
                           if b["kind"] == "effect" and ctype(b["cause"]).startswith("Action"))
    if sum(effect_kills.values()) >= 3:
        names = ", ".join(f"{c} ({n})" for c, n in effect_kills.most_common(3))
        victims = [b["card"] for b in your_deaths if b["cause"] in effect_kills]
        low = sorted({v for v in victims if ((cards.get(v) or {}).get("willpower") or 9) <= 2})
        tips.append(
            f"**Played into their damage removal.** {sum(effect_kills.values())} of your characters died to "
            f"damage actions: {names}."
            + (f" Low-willpower bodies ({', '.join(low[:4])}) were the targets." if low else "")
            + " Against this deck, lead with higher-willpower characters and don't put two "
              "small ones down the turn before they have ink for a sweeper."
        )
    collapse = [t for t in opp_turns
                if sum(1 for b in s.banish_log if b["turn"] == t.number and b["owner"] == YOU
                       and b["kind"] == "challenge") >= 3]
    if collapse:
        t = collapse[0]
        tips.append(
            f"**Board collapsed to challenges on turn {t.number}.** The opponent challenged and banished "
            f"{len(t.banished_theirs)} of your characters in one turn. Their ready attackers outnumbered "
            "your questers' willpower. Keep a Bodyguard up, or exert fewer characters the turn before."
        )

    # 2. Quested, then challenged and banished on the very next opponent turn.
    quest_then_lost = []
    for i, t in enumerate(s.turns):
        if t.side != YOU:
            continue
        nxt = s.turns[i + 1] if i + 1 < len(s.turns) else None
        if not nxt or nxt.side != OPP:
            continue
        killed_by_challenge = {ch["defender"]: ch["attacker"] for ch in nxt.challenges
                               if ch["side"] == OPP and ch["defender_died"]}
        for card, gain in t.quests:
            if card in killed_by_challenge:
                quest_then_lost.append((t.number, card, gain, killed_by_challenge[card]))
    if quest_then_lost:
        ex = "; ".join(f"T{n} {c} (+{g} lore → killed by {k})" for n, c, g, k in quest_then_lost[:4])
        tips.append(
            f"**Quested into a challenge {len(quest_then_lost)}×.** {ex}. Questing exerts the "
            "character, and exerted characters can be challenged. That's fine when the lore is "
            "worth the card, but count the opponent's ready attackers first, or keep a Bodyguard up."
        )

    # 3. Opponent questers: never removed, or removed late.
    opp_q = s.quest_lore_by_card[OPP]
    if opp_q:
        first_removed = {}
        for b in s.banish_log:
            if b["owner"] == OPP and b["card"] not in first_removed:
                first_removed[b["card"]] = b["turn"]
        top = opp_q.most_common(3)
        desc = []
        for c, n in top:
            rt = first_removed.get(c)
            desc.append(f"{c} ({n} lore, " + (f"first removed turn {rt})" if rt else "never removed)"))
        moments.append("Opponent's top questers: " + "; ".join(desc) + ".")
        for c, n in top:
            rt = first_removed.get(c)
            before = sum(g for tn, sd, cc, g in s.quest_log if sd == OPP and cc == c and (rt is None or tn < rt))
            if before >= 4:
                if rt:
                    tips.append(f"**{c} quested for {before} lore before you removed it (turn {rt}).** "
                                "Answer the opponent's best repeat quester the first turn you can, even "
                                "at the cost of a weaker play of your own.")
                else:
                    tips.append(f"**{c} quested for {before} lore and was never removed.** Point removal "
                                "or your best challenge at it before trading with smaller bodies.")
                break

    # 4/5. Ink: missed drops and unspent ink.
    missed = []
    floated = []
    last_turn = s.turns[-1].number if s.turns else 0
    for t in you_turns:
        hand = t.hand_after or Counter()
        if not t.inked:
            inkables = [n for n in hand if inkable(n)]
            needs_more = [n for n in hand if isinstance(cost(n), int) and cost(n) > t.ink_after]
            if inkables and (t.ink_after < 5 or needs_more):
                missed.append((t.number, t.ink_after, inkables))
        spent = sum(p for _, p in t.played)
        unspent = t.ink_after - spent
        if unspent >= 2 and t.number != last_turn:
            fits = sorted({n for n in hand if ctype(n) in ("Character", "Item", "Location")
                           and isinstance(cost(n), int) and cost(n) <= unspent}, key=lambda n: -cost(n))
            if fits:
                floated.append((t.number, unspent, t.ink_after, fits[:3]))
    if missed:
        ex = "; ".join(f"T{n} (stuck on {ink}, could ink {', '.join(sorted(c)[:2])})" for n, ink, c in missed[:4])
        tips.append(f"**Missed ink drops {len(missed)}×.** {ex}. On each of those turns you were under 5 ink or still held a card you "
                    "couldn't afford yet. Ink a duplicate or a card that's dead in this matchup.")
    if floated:
        ex = "; ".join(f"T{n}: {u} of {a} ink unused, holding {', '.join(f'{c} ({cost(c)})' for c in fits)}"
                       for n, u, a, fits in floated[:4])
        tips.append(f"**Unspent ink {len(floated)}×.** {ex}. Ink that isn't spent is gone at the end "
                    "of the turn; check whether one of those cards could have come down. (This counts "
                    "card costs only; activated abilities and ink drops aren't itemised in the log.)")

    # 6. Inked a lone copy while holding a duplicate inkable card.
    bad_ink = []
    for t in you_turns:
        if t.hand_after is None:
            continue
        for card in t.inked:
            # Still holding 2+ copies of another inkable card after the turn,
            # and the inked card was the last copy.
            dupes = [n for n, k in t.hand_after.items() if k >= 2 and n != card and inkable(n)]
            if t.hand_after[card] == 0 and dupes:
                bad_ink.append((t.number, card, dupes[0]))
    if bad_ink:
        ex = "; ".join(f"T{n} inked {c} while holding 2+ {d}" for n, c, d in bad_ink[:3])
        tips.append(f"**Ink choice.** {ex}. Inking a duplicate keeps more different options in hand.")

    # 7. Your challenges.
    your_ch = [c for t in s.turns for c in t.challenges if c["side"] == YOU]
    opp_ch = [c for t in s.turns for c in t.challenges if c["side"] == OPP]
    bad = [c for c in your_ch if c["attacker_died"] and not c["defender_died"]]
    if bad:
        tips.append("**Losing challenges:** " + "; ".join(
            f"{c['attacker']} died attacking {c['defender']} without banishing it" for c in bad[:3]) +
            ". Only challenge when you banish the target or the trade is clearly up for you.")

    # 8. Lore tempo.
    q_you = sum(len(t.quests) for t in you_turns)
    q_opp = sum(len(t.quests) for t in opp_turns)

    # 9. Curve: first character / first play.
    first_play = next((i + 1 for i, t in enumerate(you_turns) if t.played), None)
    if first_play and first_play >= 3:
        tips.append(f"**Slow start.** Your first card came down on your turn {first_play}. "
                    "If this keeps happening, mulligan harder for 1–2 drops.")

    # 10. Deck comparison.
    deck_notes: list[str] = []
    if deck_text.strip():
        deck = _deck_counts(deck_text)
        not_in = sorted(n for n in s.seen_you if n not in deck and n in cards)
        if not_in:
            deck_notes.append("Cards from the log that aren't in the given deck list (is it the right list?): "
                              + ", ".join(not_in[:8]))
        never = sorted(n for n, k in deck.items() if k >= 3 and s.seen_you[n] == 0)
        if never:
            deck_notes.append("3–4-ofs you never saw this game: " + ", ".join(never[:8]) + ".")
        inked_key = [(t.number, c) for t in you_turns for c in t.inked
                     if deck.get(c, 0) <= 2 and deck.get(c, 0) > 0 and ctype(c) == "Character"
                     and (cost(c) or 0) >= 4]
        if inked_key:
            tips.append("**Inked low-count payoffs:** " + "; ".join(
                f"T{n} {c} (only {deck[c]} in the deck)" for n, c in inked_key[:3]) +
                ". With 1–2 copies, every inked copy is a big share of that plan.")

    opp_colors = Counter()
    for n, k in s.revealed_opp.items():
        for col in _colors(cards.get(n)):
            opp_colors[col] += k
    you_colors = Counter()
    for n, k in s.seen_you.items():
        for col in _colors(cards.get(n)):
            you_colors[col] += 1

    return {
        "state": s,
        "turns": s.turns,
        "tips": tips,
        "moments": moments,
        "deck_notes": deck_notes,
        "deck_given": bool(deck_text.strip()),
        "quests": (q_you, q_opp),
        "challenges": (your_ch, opp_ch),
        "opp_colors": [c for c, _ in opp_colors.most_common(3)],
        "you_colors": [c for c, _ in you_colors.most_common(2)],
        "opp_guess": _guess_opponent_deck(s.revealed_opp, [c for c, _ in opp_colors.most_common(2)]),
        "lines": len(lines),
    }


def _fmt_list(items: list[str]) -> str:
    return ", ".join(items) if items else "—"


def format_game_review(r: dict) -> str:
    if "error" in r:
        return r["error"]
    s: State = r["state"]
    you_l, opp_l = s.lore[YOU], s.lore[OPP]
    if s.winner == YOU:
        result = f"**Win {you_l}–{opp_l}**"
    elif s.winner == OPP:
        result = f"**Loss {you_l}–{opp_l}**"
    else:
        result = f"Unfinished / conceded at {you_l}–{opp_l}"
    play = {YOU: "on the play", OPP: "on the draw"}.get(s.first_player or "", "")
    out = [f"# Game review — {result}",
           f"{len(s.turns)} turns ({sum(1 for t in s.turns if t.side == YOU)} yours), {play}. "
           f"Your inks: {_fmt_list(r['you_colors'])}. Opponent's inks: {_fmt_list(r['opp_colors'])}."]
    if s.mulligan.get(YOU):
        m = s.mulligan[YOU]
        out.append(f"Mulligan: you put back {m['count']} ({_fmt_list(m['out'])}), drew {_fmt_list(m['in'])}. "
                   f"Opponent put back {s.mulligan.get(OPP, {}).get('count', 0)}.")
    if s.undo_count:
        out.append(f"_{s.undo_count} undo(s) in the log were rolled back before analysis._")

    out += ["", "## Your turns", "| Turn | Inked | Played (ink paid) | Sang | Quested | Lore you–opp |", "|---|---|---|---|---|---|"]
    for t in s.turns:
        if t.side != YOU:
            continue
        played = ", ".join(f"{c} ({p})" for c, p in t.played) or "—"
        sang = ", ".join(f"{a} ← {b}" for a, b in t.sang) or "—"
        q = ", ".join(f"{c} +{g}" for c, g in t.quests) or "—"
        spent = sum(p for _, p in t.played)
        out.append(f"| {t.number} | {_fmt_list(t.inked)} | {played} [{spent}/{t.ink_after}] | {sang} | {q} | "
                   f"{t.lore_after.get(YOU, 0)}–{t.lore_after.get(OPP, 0)} |")

    out += ["", "## Opponent"]
    g = r["opp_guess"]
    if not g and r["opp_colors"]:
        out.append(f"No known tournament list in {'/'.join(r['opp_colors'][:2])} shares 3+ cards with what they showed.")
    if g:
        out.append(f"Closest known list: **{g[0]}** ({g[2]} of their {g[3]} revealed cards appear in "
                   f"{g[1]}). Use `get_meta(event=...)` to see the whole list.")
    rev = sorted(s.revealed_opp.items(), key=lambda kv: (-kv[1], kv[0]))
    out.append("Cards seen (×N = times played, inked or discarded): "
               + (", ".join(f"{n} ×{k}" if k > 1 else n for n, k in rev) or "none"))
    qy, qo = r["quests"]
    yc, oc = r["challenges"]
    out.append(f"Quests: you {qy}, opponent {qo}. Challenges: you {len(yc)} "
               f"({sum(c['defender_died'] for c in yc)} kills), opponent {len(oc)} "
               f"({sum(c['defender_died'] for c in oc)} kills). Cards drawn: you {s.drawn[YOU]}, "
               f"opponent {s.drawn[OPP]}.")

    if r["moments"]:
        out += ["", "## Key moments"] + [f"- {m}" for m in r["moments"]]

    out += ["", "## Tips"]
    out += [f"{i}. {t}" for i, t in enumerate(r["tips"], 1)] or ["No obvious misplays found in what the log shows."]
    if r["deck_notes"]:
        out += ["", "## Against your deck list"] + [f"- {n}" for n in r["deck_notes"]]
    if not r["deck_given"]:
        out += ["", "_No deck list given, so these tips only use what's in the log. Ask the player "
                "which deck they played (a pasted list or a deck file path) and run this again for "
                "deck-specific tips, such as low-count payoffs that got inked and key cards that never showed up._"]
    out += ["", "_Limits: the opponent's hand is hidden, so only revealed cards count. Ink math uses card "
            "costs paid; activated ability costs and ink drops aren't itemised in the duels.ink log._"]
    return "\n".join(out)
