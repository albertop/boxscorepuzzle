"""Pack A: sixteen boards to solve by hand, as a printable pack — and an experiment inside it.

⚠⚠ **Sixteen at stall rungs 5, 8, 11 and 12.** This said *fifty* and *chain* until 2026-08-23, four
days after `ba49413` re-axed the code, so the file described the retired design while behaving as the
current one. **The behaviour was right and the text was the artefact** — and this text is not only a
comment: the same words reached `key.csv`'s header and the run summary, which are the record of the
experiment rather than a description of it.

§22 promotes the hand-solve from sanity check to launch gate, because it is the only real
verification of human derivability that exists and the only check the same-author risk does not
touch. This builds the pack.

**It is also an experiment with a hypothesis.** Layer 3 certifies that a propagator holding every
relation at once needs no guess; layer 3b asks the same of a solver reading one relation at a time,
and **29% of Saturday boards fail it**. A player sits between the two and nothing automated says
where. So a third of these sixteen come from the uncertified 29%, interleaved at random and unlabelled:

  * solved with no more difficulty than the rest → 3b is too conservative and stays reported
  * stuck systematically on them → 3b becomes a gate

**Which board is which is in `key.csv`, which must not be opened until the solving is finished.**
Nothing on a puzzle page identifies the game, the date, the teams, the stall target, the difficulty
or the certification status. The board reference is a sequential number and encodes nothing.

Read-only against DGL. Run from `forge/`.
"""

import csv
import json
import random
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "verifier"))

from collections.abc import Sequence  # noqa: E402

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

from boxscore_domain import ZERO_DENSITY_GATE  # noqa: E402
from boxscore_forge.calendar import read as read_calendar  # noqa: E402
from boxscore_forge.publication_key import PINNED_PUBLIC_KEY  # noqa: E402
from boxscore_forge.publish import slot_references  # noqa: E402
from boxscore_package.format import (  # noqa: E402
    FOOTNOTE_COLUMNS,
    Board,
    read,
)
from boxscore_package.format import Package as PuzzlePackage  # noqa: E402
from boxscore_package.innings import to_display  # noqa: E402
from boxscore_package.signing import verify as verify_signature  # noqa: E402
from boxscore_package.signing import verifying_key  # noqa: E402
from boxscore_verify.verify import derivable_in_view  # noqa: E402

TARGETS = (5, 8, 11, 12)
QUOTAS = {5: 4, 8: 4, 11: 4, 12: 4}
"""**Pack A: stall rungs, four boards each** — decided 2026-08-21, built 2026-08-22.

⚠️⚠️ **These were chain targets `(5, 7, 9, 11)` with quotas summing to fifty**, and the file's own
docstring said so: *"the target variable is now stalls… this pack must not be printed until `erase` can
take a stall target."* It can, and has since the generator moved. **The pack was the last chain-targeted
thing in the tree**, and correcting the documents while leaving it would have been the visible half of a
fix with the working half untouched.

⚠️ **On the pack's own axis 8 is already the 87th percentile and 12 is near the reachable maximum**, so
the rungs are not the ceiling measurement's range: the ceiling takes the best of nine seeds per board
and the pack is what one ordinary attempt produces. Reading one as the other compares two different
questions.

⚠️ **Only about 20% of boards reach 12.** If that rung does not fill, **that is the finding** — reported,
never quietly substituted with a lower target
it exists to correct.

Explicit quotas rather than weighted sampling. A first version drew by weight and produced no chain-5
boards at all — with one board per game, the hard targets took every game before the easy ones were
reached, and a pack missing a rung cannot say anything about that rung.
"""

WANTED = 16

# ⚠️⚠️ **`UNCERTIFIED_SHARE = 1/3` stood here and is removed, 2026-08-23. The reason it existed is
# also the reason it had to go.**
#
# It capped how many layer-3b-uncertified boards a pack could hold, and the danger it named is real:
# if the uncertified boards all live at the hard end, filling the hard rung with them makes
# **uncertified and hard the same variable**, and any difference the solver feels is difficulty
# wearing certification's clothes.
#
# It was sized against *3b certifies 100% of the easiest boards and 91% of the hardest* — measured on
# the **chain** axis, which the generator abandoned. Measured over the shipping inventory at stall
# rungs: **5 certified of 75**, and **4 of those 5 sit at rung 8.**
#
# **So against this population the quota creates the confound it was written to prevent.** At 1/3 the
# pack came out rung 8 = 3 certified, rung 11 = 1, rung 12 = 0 — *rung 8 is the certified rung and the
# others are not*, which is precisely the variable being confounded, relocated. Unfiltered, 15 of 16
# boards are uncertified: certification stops varying, and there is nothing left to confound.
#
# ⚠️ **The count is reported, never assumed.** `report()` prints how many certified came out, so a
# future reader knows the mix was *observed* rather than chosen. Removing a filter silently is how a
# later reader concludes a property was designed.

PRE_1950_ALLOWANCE = 2
"""§5's pre-1950 preference, applied so the pack looks like what will actually ship."""

GATE = ZERO_DENSITY_GATE
"""⚠️⚠️ **The shipping gate, not `HAND_SOLVE_ZERO_DENSITY_GATE`.** The pack drew at 0.25 while the
inventory ships at 0.30, which made it grade a cleaner population than the player meets. See
`shipping_games()` — the pack takes the calendar's boards now, so the draw's gate is whatever produced
them, and this constant only survives for the candidate filter."""

CALENDAR = Path(__file__).resolve().parents[2] / "forge" / "calendar.json"
INVENTORY = Path(__file__).resolve().parents[2] / "forge" / "inventory"
"""Tighter than `ZERO_DENSITY_GATE`, deliberately and only for the hand-solve packs.

This pack puts boards in front of a person to judge, so it draws from the cleaner end — a board
rejected for zero density is not the board being asked about, and the corrected pool is abundant enough
to afford it. **The reason and the number now live together in `boxscore_domain`**, because a deviation
with its reason attached is not the defect a bare literal is.
"""

PICK_SEED = 50
"""Only the *choice* among equally eligible boards. ⚠⚠ **It was `SEED`, and it seeded an erasure.**

The pack re-derived each board with this seed and one attempt, so a board entered the pool only if that
attempt reproduced it — 2 boards at rung 11 where the inventory holds 23. **There is no erasure here any
more**, so the seed decides which of several eligible boards is printed and nothing about difficulty."""
SAMPLE_PER_DECADE = 8

BATTING_HEADS = ("PA", "AB", "R", "H", "BB", "SO")
PITCHING_HEADS = ("IP", "H", "R", "ER", "BB", "SO")
FOOTNOTE_LABELS = (
    ("hit_by_pitch", "HBP"),
    ("sacrifice_flies", "SF"),
    ("sacrifice_hits", "SH"),
    ("catcher_interference", "CI"),
)


@dataclass(frozen=True, slots=True)
class Candidate:
    """One shipped board, read from its signed package. **Nothing here is re-derived.**"""

    game_id: str
    puzzle_id: str
    generation: str
    season: int
    target: int
    package: PuzzlePackage
    certified: bool
    has_substitution: bool
    has_live_footnote: bool

    @property
    def slots(self) -> tuple[int, ...]:
        """The lineup slot of each batting row, recovered from the package's own references.

        ⚠️ **From `slot_references`, not from a second source.** `9`, `9a` and `9b` are all slot nine;
        stripping the letter is exact and it keeps one definition of which row sits where.
        """
        references = self.package.slot_references or ()
        return tuple(int("".join(ch for ch in reference if ch.isdigit())) for reference in references)


def footnote_line(board: Board, slots: "Sequence[int]") -> str:
    """`SH: 1 #2, 1 #9b   LOB: 9` — read from the **puzzle**, never from the source direction.

    Each carrier is `<count> #<slot>`, carriers joined by `, `, terms in `FOOTNOTE_COLUMNS` order, LOB
    last, all joined by three spaces.

    ⚠️ **The count is what makes the board solvable, and it used to be absent.** The old form printed
    `SH: 2`, which is a *slot reference* and reads as a count — the two could not be told apart, and a
    row carrying two of one term could not be expressed at all. Measured over the admissible pool:
    **4,019 of 100,226 directions carry at least one such row — 4.01%**, and 8.31% in the 1920s where
    the pool is thinnest. Those boards cannot be solved: `PA = AB + BB + HBP + SF + SH + CI` has no
    other route to the value, and **every total still balances**, which is why nothing in the four
    layers saw it.

    ⚠️ **The count prints even when it is one.** A format showing it only sometimes is ambiguous again —
    the same trap as the slot letter that appears only when a slot is shared, which is what made the old
    form unambiguous by accident rather than by design.

    ⚠️ **`serve/tests/footnote-line-vectors.json` holds the canonical strings and the browser renderer
    runs against the same file.** §33 forbids the two sharing a function, so they share the data. They
    had drifted in three ways at once — no count, no `#`, and LOB at opposite ends of the line — while a
    reading of the PDF alone suggested they agreed.

    ⚠️ **This took its values from `Loaded.direction` and the grid beside it drew the erased board.**
    The printed board was then easier than the puzzle whose stalls and layer-3b status its key recorded.
    That is `Board → the artifact a human reads`, one boundary further out than the `Direction → Board`
    defect fixed before it, and the same shape.

    *The `?` placeholder for an erased attribution is gone with the cells it stood for: the footnote line
    is given in full from schema 4, so no value here is ever unknown.*
    """
    references = slot_references(slots)
    parts = []
    for field, short in FOOTNOTE_LABELS:
        column = FOOTNOTE_COLUMNS.index(field)
        carriers = [f"{row[column]} #{references[index]}" for index, row in enumerate(board.footnotes) if row[column]]
        if carriers:
            parts.append(f"{short}: {', '.join(carriers)}")
    parts.append(f"LOB: {board.left_on_base}")
    return "   ".join(parts)


def shipped(assigned: dict[str, str], generations: set[str]) -> list[Candidate]:
    """The boards that will actually be served, read from their signed packages.

    ⚠️⚠️ **It re-derived them until 2026-08-23, and that was the whole of the 3% finding.** The pack
    called `erase_with_lineup_fallback(..., seed=SEED)` once per target and kept whatever came back, so
    a board only entered the pool if **one ordinary attempt at one fixed seed** reproduced it. The
    shipped board came from `_hardest_target()` working down from the ceiling. The pool it built held
    **2 boards at rung 11 and 3 at rung 12**; the inventory on disk holds **23 and 31**.

    ⚠️⚠️ **And the axis argument survived while the instrument stopped being valid, which is the shape
    worth naming.** *The ceiling is the best of nine seeds; the pack is what an ordinary attempt
    produces* is true, was deliberate, and is written down. **What nobody checked is whether an ordinary
    attempt recovers a board the producer found working down from the ceiling.** It does not — and the
    justification stayed true the whole time, so nothing about it read as wrong.

    **B's gate asks whether what ships is derivable by a person.** A re-derived board shares the game id
    and nothing else, so the question it answers is a near neighbour of the one being asked. That is not
    an acceptable substitution at a launch gate.

    ⚠️ **No database, no seed, no erasure.** Everything comes from the package and the calendar.
    """
    found: list[Candidate] = []
    verifying = verifying_key(PINNED_PUBLIC_KEY.read_text(encoding="utf-8").strip())
    for game_id, wanted_id in sorted(assigned.items()):
        path = next(
            (INVENTORY / generation / f"{wanted_id}.json" for generation in sorted(generations)
             if (INVENTORY / generation / f"{wanted_id}.json").is_file()),
            None,
        )
        if path is None:
            message = f"{wanted_id} is in the calendar and in no generation under {INVENTORY}"
            raise SystemExit(message)
        package = read(path)

        # ⚠️⚠️ **The signature is checked, and a failure is a refusal rather than a warning.** The pack
        # prints boards straight from files on disk; `serve` refuses an unsigned or altered package, so
        # printing one without checking would put a board in front of the operator that the product
        # itself would reject — and the gate would be measuring something that will never be served.
        # `format.read()` parses and does not verify; that is why this is here rather than assumed.
        verify_signature(package, verifying)

        target = package.metadata.get("target_stalls")
        if not isinstance(target, int) or target not in TARGETS:
            continue
        found.append(
            Candidate(
                game_id=game_id,
                puzzle_id=package.puzzle_id,
                generation=path.parent.name,
                # ⚠️ From the game id's characters, exactly as `build_inventory._is_early` reads it. The
                # package strips season, date and teams (§7), so this is where it lives.
                season=int(game_id[3:7]),
                target=target,
                package=package,
                certified=derivable_in_view(package),
                # ⚠️ A substitution is two rows sharing a lineup slot. `slot_references` puts a letter on
                # a reference **only** where the slot is shared, so a letter anywhere is the signal —
                # never a hyphen in a label, which is what this read before the suffix was removed.
                has_substitution=any(not reference.isdigit() for reference in package.slot_references or ()),
                has_live_footnote=any(any(row) for row in package.solution.footnotes),
            )
        )
    return found


def choose(pool: list[Candidate], rng: random.Random) -> list[Candidate]:
    """Sixteen boards: a third uncertified, every stall rung present, era quota respected.

    One board per game, so no solver sees the same lineup twice and recognises it.
    """
    chosen: list[Candidate] = []
    used_games: set[str] = set()
    pre_1950 = [0]

    def take(candidate: Candidate) -> bool:
        if candidate.game_id in used_games:
            return False
        if candidate.season < 1950 and pre_1950[0] >= PRE_1950_ALLOWANCE:
            return False
        used_games.add(candidate.game_id)
        pre_1950[0] += candidate.season < 1950
        chosen.append(candidate)
        return True

    def shuffled(items: list[Candidate]) -> list[Candidate]:
        ordered = sorted(items, key=lambda item: item.game_id)
        rng.shuffle(ordered)
        return ordered

    # ⚠️⚠️ **Each rung is filled to quota and certification is not consulted.** Decided 2026-08-23; the
    # constant that stood at the top of this file carries the argument.
    #
    # ⚠️⚠️ **And there were TWO caps, which is the part nobody could see without measuring.** The
    # overall `UNCERTIFIED_SHARE` was blamed for the pack coming out at nine of sixteen. It was not the
    # binding one: a per-rung `ceiling_here = wanted // 2` stood right here and allowed **two**
    # uncertified boards per rung whatever the share said. Raising the share alone stalls at **eleven**
    # — measured at 0.50, 0.67, 0.75, 0.90 and 1.00, all eleven, the same rungs every time — because
    # from 0.50 upward the per-rung ceiling is what holds.
    #
    # ⚠️⚠️ **A false explanation that the outcome appears to validate.** The first account of the nine
    # was *five uncertified allowed plus four certified available equals nine*. The pool holds **five**
    # certified, not four, so the arithmetic was wrong — and it produced the right number, which is why
    # it was believed. `CLAUDE.md` records instruments that measure their own output and metrics
    # pointed at the wrong thing; this is a third relative: **a wrong cause whose prediction happens to
    # match, which no amount of re-reading the result can detect.** Only enumerating the mechanisms —
    # both caps, and the actual certified count — separated them. *A number that comes out right is not
    # evidence that the reason is right.*
    for target in sorted(TARGETS, reverse=True):
        wanted = QUOTAS[target]
        at_target = len([item for item in chosen if item.target == target])
        for candidate in shuffled([item for item in pool if item.target == target]):
            if at_target >= wanted:
                break
            if take(candidate):
                at_target += 1

    # The two cases the tutorial has to teach must appear somewhere in the pack. If one is missing a
    # board is *swapped* rather than appended: the replacement takes the place of one at the same
    # stall target, the same certification and the same side of 1950, so every quota survives the
    # substitution. An earlier version appended and then dropped `chosen[-2]`, which removed an
    # arbitrary board and could silently empty a rung.
    for trait_name, trait in (
        ("substitution", lambda c: c.has_substitution),
        ("live footnote", lambda c: c.has_live_footnote),
    ):
        if any(trait(item) for item in chosen):
            continue
        for candidate in shuffled([item for item in pool if trait(item)]):  # pragma: no cover - rare
            if candidate.game_id in used_games:
                continue
            victims = [
                item
                for item in chosen
                if item.target == candidate.target
                and item.certified == candidate.certified
                and not trait(item)
                and (item.season < 1950) == (candidate.season < 1950)
            ]
            if not victims:
                continue
            chosen.remove(victims[0])
            used_games.discard(victims[0].game_id)
            pre_1950[0] -= victims[0].season < 1950
            take(candidate)
            break
        else:  # pragma: no cover - only if the pool cannot supply the trait at all
            message = f"no board in the pool carries a {trait_name} at a target the pack can spare"
            raise SystemExit(message)

    rng.shuffle(chosen)
    # ⚠️⚠️ **The audit was here and it defeated the fix that moved it.** `main()` calls `report()` and
    # *then* `audit()`, with a comment explaining that a refusal which does not say what it drew from is
    # half a check — and this line raised one level down, before `report()` was ever reached. **The
    # repair was made in the caller while the thing being repaired sat in the callee**, so the terminal
    # showed a bare refusal on 2026-08-23 exactly as it had before.
    #
    # ⚠️ It cost a diagnosis by hand: *nine boards, wanted sixteen* with no pool distribution beside it
    # cannot distinguish a pack that filtered badly from an inventory with nothing to give.
    return chosen


FORMULAS = (
    "PA = AB + BB + HBP + SF + SH + CI &nbsp;&nbsp;|&nbsp;&nbsp; "
    "Column totals = sum of the rows &nbsp;&nbsp;|&nbsp;&nbsp; "
    "PA = Outs + Runs + LOB<br/>"
    "Team H = hits allowed by the opposing pitchers (same for BB, SO, R) &nbsp;&nbsp;|&nbsp;&nbsp; "
    "Outs = 3 x innings pitched &nbsp;&nbsp;|&nbsp;&nbsp; "
    "AB &ge; H &nbsp;&nbsp;|&nbsp;&nbsp; ER &le; R &nbsp;&nbsp;|&nbsp;&nbsp; nothing below zero"
)
"""On every page, not only on a cover sheet — somebody solving across several days should not have
to go and find it.

It doubles as the first real test of §8's permanent reference sheet. If this works on paper across
sixteen boards the reference sheet is about right, and if it does not, that is worth knowing now.
"""


def survey_box() -> Table:
    """The three categories stay separate, and the 1-6 scale is what validates the rung.

    ⚠️ **The scale is the only thing that can test whether the stall count measures difficulty at all.**
    A stall count is a solver measurement; that it corresponds to what a person experiences is an
    assumption nobody has checked. If the marked 1-6 tracks the rung, the scale is validated. If it does
    not, the count is measuring something else and the generator's control variable is wrong — which is
    worth knowing before a calendar is built on it.

    It is deliberately not tied to the day of the week. A 5 marked on a board the system calls Monday
    says that board is misclassified, and that is exactly the signal wanted.

    Two conditions or it measures nothing, both enforced elsewhere: **the stall target never appears
    on the page**, since seeing "8 stalls" anchors the rating to the number, and **the pages are not
    ordered by target**, since the early boards become the reference for everything after them.

    Only **had to guess** bears on layer 3b. **Tedious** and **boring** bear on the difficulty curve
    and the quality filter, and merging them loses both answers.

    The free-text line matters more than it looks: every serious defect in this project came from
    somebody noticing that something looked wrong, never from a statistic.
    """
    lines = [
        ["Time taken: ________ min", "Finished?    Y  /  N"],
        ["How many times did you have to stop and think?  ______", ""],
        ["How hard was it?     1     2     3     4     5     6", "(1 = very easy, 6 = very hard)"],
        ["If not finished, where did you get stuck?  _________________________________________", ""],
        ["How did it feel?   (tick any)", ""],
        ["   [   ] Had to guess — no next step by reasoning", "   [   ] Tedious — too much adding, or hunting"],
        ["   [   ] Boring — easy, nothing to think about", "   [   ] Good"],
        ["Anything odd?  ____________________________________________________________________", ""],
    ]
    table = Table(lines, colWidths=[80 * mm, 72 * mm], rowHeights=4.9 * mm)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#666666")),
                # The four feelings sit two by two rather than one per line: it is a shorter box and
                # a tick grid reads faster than a list when the same four choices repeat on every page.
                ("SPAN", (0, 1), (1, 1)),
                ("SPAN", (0, 3), (1, 3)),
                ("SPAN", (0, 4), (1, 4)),
                ("SPAN", (0, 7), (1, 7)),
                ("LINEBELOW", (0, 0), (-1, 0), 0.3, colors.HexColor("#bbbbbb")),
                ("LINEBELOW", (0, 2), (-1, 2), 0.3, colors.HexColor("#bbbbbb")),
                ("LINEBELOW", (0, 6), (-1, 6), 0.3, colors.HexColor("#bbbbbb")),
            ]
        )
    )
    return table


def audit(chosen: list[Candidate]) -> None:
    """Assert the pack is what it claims. A launch gate is checked by code, never believed from print.

    The pack decides whether layer 3b becomes a gate, so a pack that reports quotas it does not meet
    invalidates that experiment silently. It has happened once already: weighted sampling produced
    zero boards at the easiest rung and only the printed summary showed it.
    """
    problems: list[str] = []
    if len(chosen) != WANTED:
        problems.append(f"{len(chosen)} boards, wanted {WANTED}")
    for target, quota in QUOTAS.items():
        at_target = sum(1 for item in chosen if item.target == target)
        if at_target != quota:
            problems.append(f"stall rung {target} has {at_target} boards against a quota of {quota}")
    pre_1950 = sum(1 for item in chosen if item.season < 1950)
    if pre_1950 > PRE_1950_ALLOWANCE:
        problems.append(f"{pre_1950} pre-1950 boards against an allowance of {PRE_1950_ALLOWANCE}")
    games = [item.game_id for item in chosen]
    if len(set(games)) != len(games):
        problems.append("the same game appears twice")
    if not any(item.has_substitution for item in chosen):
        problems.append("no board carries a suffixed label, and the tutorial has to teach one")
    if not any(item.has_live_footnote for item in chosen):
        problems.append("no board carries a live footnote, and the tutorial has to teach one")
    # ⚠️⚠️ **The two certification assertions are gone with the quota that made them meaningful, and
    # this paragraph is why rather than a blank space.**
    #
    # One required the pack to hold roughly a third uncertified boards; the other refused a rung that
    # was *entirely* uncertified, because that makes "uncertified" and "hard" one variable. Both were
    # correct about a population where certification varied. It does not vary any more: **5 of 75
    # shipped boards are certified**, so a pack drawn without filtering is ~15 of 16 uncertified and
    # every rung is uncertified — which the second assertion would refuse, and which is now the honest
    # description of what ships rather than a defect.
    #
    # ⚠️ **What replaces them is not another assertion but a printed count.** `report()` states how
    # many certified came out. There is no target to assert against, and asserting a number nobody
    # chose would be a check that only says the pool has not changed — dressed as a property of the
    # pack.

    # ⚠️ Folded in from a second `audit()` that had been defined below this one. Python kept the
    # later definition, so the strict uncertified share this function enforces was not running and a
    # pack could pass with anywhere from 10% to 50% uncertified boards. One audit, not two.
    order = [candidate.target for candidate in chosen]
    rising = sum(1 for a, b in zip(order, order[1:], strict=False) if b > a)
    falling = sum(1 for a, b in zip(order, order[1:], strict=False) if b < a)
    if rising == 0 or falling == 0 or min(rising, falling) < len(order) // 5:
        problems.append(f"the page order is monotonic in difficulty: {rising} rises, {falling} falls")

    if problems:
        raise SystemExit("the pack does not satisfy its own constraints: " + "; ".join(problems))


def indented(label: str, *, substitute: bool) -> str:
    """A row that shares its slot with an earlier one is indented, the way a printed boxscore sets it.

    ⚠️ **This used to decide by `"-" in label`, and that was the same defect this project spent a day
    closing, asleep.** Indentation is a property of the *lineup slot* — this man came into somebody
    else's place — and it was being derived from a formatting detail of the label. The two agreed by
    coincidence, and the moment the suffix was removed the cue vanished and every substitute drew as a
    starter. Deriving it from the slot removes the coincidence.
    """
    return f"  {label}" if substitute else label


def substitutes(slots: "Sequence[int]") -> list[bool]:
    """Which rows share a slot with a row above them. One source for the indent and the rule."""
    seen: set[int] = set()
    flags: list[bool] = []
    for slot in slots:
        flags.append(slot in seen)
        seen.add(slot)
    return flags


def board_table(board: Board, candidate: "Candidate", *, solved: bool) -> Table:
    # ⚠️ Eight columns, not seven. The first carries the lineup slot, and it is the cell a footnote
    # reference points at: `SH: 9b` is useless if nothing on the board says `9b`. Its header is left
    # blank on purpose — no boxscore has a slot column, so any symbol there is our invention asking to
    # be interpreted, while `1, 2, 3...` in order explains itself.
    rows: list[list[str]] = [["", "", *BATTING_HEADS]]
    spans: list[tuple[str, tuple[int, int], tuple[int, int], object]] = []
    batting_team = "HOME" if candidate.package.offense_is_home else "AWAY"
    pitching_team = "AWAY" if candidate.package.offense_is_home else "HOME"

    rows.append([f"{batting_team} BATTING", *([""] * 7)])
    section_rows = [len(rows) - 1]
    sub = substitutes(candidate.slots)
    references = candidate.package.slot_references or ()
    first_batting_row = len(rows)
    for index, line in enumerate(board.batting):
        rows.append(
            [
                references[index],
                indented(candidate.package.labels[index], substitute=sub[index]),
                *("" if value is None else str(value) for value in line),
            ]
        )
    # The rule between slots goes above the first row of each new slot, which is where a block starts.
    slot_rules = [first_batting_row + index for index, shared in enumerate(sub) if not shared and index]
    rows.append(["", "TOTALS", *("" if value is None else str(value) for value in board.batting_totals)])
    totals_rows = [len(rows) - 1]

    rows.append([f"{pitching_team} PITCHING", *([""] * 7)])
    section_rows.append(len(rows) - 1)
    rows.append(["", "", *PITCHING_HEADS])
    head_rows = [0, len(rows) - 1]
    for index, line in enumerate(board.pitching):
        label = (
            candidate.package.pitcher_labels[index]
            if index < len(candidate.package.pitcher_labels)
            else f"P{index + 1}"
        )
        cells = ["" if value is None else str(value) for value in line]
        if line[0] is not None:
            cells[0] = to_display(line[0])
        # The slot column is empty in the pitching section: those are the *opposing* team's pitchers
        # and they have no place in this batting order. Left blank deliberately rather than by
        # omission, since a stray number here would name a row that does not exist.
        rows.append(["", label, *cells])
    totals = ["" if value is None else str(value) for value in board.pitching_totals]
    if board.pitching_totals[0] is not None:
        totals[0] = to_display(board.pitching_totals[0])
    rows.append(["", "TOTALS", *totals])
    totals_rows.append(len(rows) - 1)

    del solved
    # Shorter rows on a tall board. Eight millimetres is still far more than a digit needs, and
    # the page has to carry the formula strip and the survey box as well as the grid.
    height = 7.4 * mm if len(rows) > 20 else 8.6 * mm
    # The slot column is taken out of the label column rather than added to the board: the label no
    # longer carries a suffix, so it needs less than it did, and the six data columns keep their width.
    table = Table(rows, colWidths=[8 * mm, 18 * mm, *([21 * mm] * 6)], rowHeights=height)
    style: list[tuple[object, ...]] = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (1, -1), 3),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        (
            "BACKGROUND",
            (0, first_batting_row),
            (0, first_batting_row + len(board.batting) - 1),
            colors.HexColor("#eeeeee"),
        ),
    ]
    for row in head_rows:
        style += [
            ("BACKGROUND", (0, row), (-1, row), colors.HexColor("#dddddd")),
            ("FONTNAME", (0, row), (-1, row), "Helvetica-Bold"),
        ]
    for row in section_rows:
        style += [
            ("BACKGROUND", (0, row), (-1, row), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0, row), (-1, row), colors.white),
            ("FONTNAME", (0, row), (-1, row), "Helvetica-Bold"),
            ("FONTSIZE", (0, row), (-1, row), 8),
            ("ALIGN", (0, row), (-1, row), "LEFT"),
            ("SPAN", (0, row), (-1, row)),
        ]
    for row in totals_rows:
        style += [
            ("BACKGROUND", (0, row), (-1, row), colors.HexColor("#eeeeee")),
            ("FONTNAME", (0, row), (-1, row), "Helvetica-Bold"),
        ]
    style += [("LINEABOVE", (0, row), (-1, row), 1.1, colors.HexColor("#666666")) for row in slot_rules]
    table.setStyle(TableStyle(style + [tuple(span) for span in spans]))  # type: ignore[arg-type]
    return table


def line_score_table(board: Board, *, offense_is_home: bool) -> Table:
    score = board.line_score
    innings = max(len(score.offense_by_inning), len(score.defense_by_inning))
    away, home = (
        (score.defense_by_inning, score.offense_by_inning)
        if offense_is_home
        else (score.offense_by_inning, score.defense_by_inning)
    )
    away_rhe, home_rhe = (
        (
            (score.defense_runs, score.defense_hits, score.defense_errors),
            (score.offense_runs, score.offense_hits, score.offense_errors),
        )
        if offense_is_home
        else (
            (score.offense_runs, score.offense_hits, score.offense_errors),
            (score.defense_runs, score.defense_hits, score.defense_errors),
        )
    )
    header = ["", *(str(index + 1) for index in range(innings)), "R", "H", "E"]
    rows = [header]
    for side, by_inning, rhe in (("AWAY", away, away_rhe), ("HOME", home, home_rhe)):
        cells = [str(by_inning[index]) if index < len(by_inning) else "x" for index in range(innings)]
        rows.append([side, *cells, *(str(value) for value in rhe)])
    table = Table(rows, colWidths=[14 * mm, *([9 * mm] * innings), 10 * mm, 10 * mm, 10 * mm], rowHeights=6 * mm)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bbbbbb")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("LINEBEFORE", (innings + 1, 0), (innings + 1, -1), 1.0, colors.HexColor("#666666")),
            ]
        )
    )
    return table


def build_pdf(path: Path, chosen: list[Candidate], *, answers: bool) -> None:
    document = SimpleDocTemplate(
        str(path), pagesize=A4, topMargin=14 * mm, bottomMargin=12 * mm, leftMargin=16 * mm, rightMargin=16 * mm
    )
    reference = ParagraphStyle("reference", fontName="Helvetica-Bold", fontSize=11)
    footnotes = ParagraphStyle("footnotes", fontName="Helvetica", fontSize=8.5, spaceBefore=3)
    formulas = ParagraphStyle(
        "formulas",
        fontName="Helvetica",
        fontSize=7.0,
        leading=9,
        spaceBefore=2,
        textColor=colors.HexColor("#333333"),
    )
    story: list[object] = []
    for index, candidate in enumerate(chosen, start=1):
        # Nothing here names the game, the date, the teams, the target or the certification. All of
        # that is the key file, and a spoiler on the page would void the experiment.
        story.append(Paragraph(f"Board {index:02d}{' — solution' if answers else ''}", reference))
        story.append(Paragraph(FORMULAS, formulas))
        story.append(Spacer(1, 2 * mm))
        story.append(line_score_table(candidate.package.puzzle, offense_is_home=candidate.package.offense_is_home))
        story.append(
            Paragraph(
                footnote_line(candidate.package.solution if answers else candidate.package.puzzle, candidate.slots),
                footnotes,
            )
        )
        story.append(Spacer(1, 2 * mm))
        story.append(
            board_table(
                candidate.package.solution if answers else candidate.package.puzzle, candidate, solved=answers
            )
        )
        if not answers:
            story.append(Spacer(1, 3 * mm))
            story.append(survey_box())
        if index < len(chosen):
            story.append(PageBreak())
    document.build(story)


def write_provenance(path: Path, chosen: list[Candidate], assigned: dict[str, str], generations: set[str]) -> None:
    """Which data these boards were drawn against. **`docs/reloading-retrosheet.md` §8.**

    ⚠⚠ **The pack takes `game_id`s from the calendar and reloads them from the database**, so a reload
    between the generation and the pack changes the board underneath the id. `main()` notices the game
    that stops qualifying; it cannot notice **the one that changed and still qualifies** — and a wrong
    key does not fail loudly, it produces a wrong measurement of the one thing no test can check.

    ⚠⚠ **Beside the key, never inside it, and that is the point.** The key must not be opened until the
    solving is finished; provenance that lived in it could only be checked by spoiling the experiment.
    **A future reader can compare this file against the calendar without opening an answer.**

    ⚠️ **It records rather than verifies**, which is the honest scope. Regenerating each `game_id` and
    comparing the produced solution against the shipping package would *detect* a reload rather than
    merely make it detectable; that is a stronger check and it is not built here.
    """
    document = {
        "built": datetime.now(tz=UTC).isoformat(),
        "calendar": str(CALENDAR),
        "generations": sorted(generations),
        "boards": [
            {
                "board": f"{index:02d}",
                "game_id": candidate.game_id,
                # The id the calendar assigned to this game. Puzzle ids derive from the game and never
                # from the date (§21), so regenerating it and getting a different id is a changed dataset.
                "calendar_puzzle_id": assigned.get(candidate.game_id, ""),
            }
            for index, candidate in enumerate(chosen, start=1)
        ],
    }
    path.write_text(json.dumps(document, indent=1, sort_keys=True) + chr(10), encoding="utf-8")


def write_key(path: Path, chosen: list[Candidate]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "board",
                "game_id",
                "season",
                # ⚠⚠ **`stall_target`, and it read `chain_target` until 2026-08-23.** The column always
                # held a stall target after `ba49413`; the header named the retired axis. **A key is the
                # record of what the experiment measured**, so a mislabelled column there is not a stale
                # comment — it is the measurement described wrongly, permanently, in the one file that
                # outlives the run.
                "stall_target",
                "certified_by_3b",
                "substitution",
                "live_footnote",
            ]
        )
        for index, candidate in enumerate(chosen, start=1):
            writer.writerow(
                [
                    f"{index:02d}",
                    candidate.game_id,
                    candidate.season,
                    candidate.target,
                    "yes" if candidate.certified else "NO",
                    "yes" if candidate.has_substitution else "",
                    "yes" if candidate.has_live_footnote else "",
                ]
            )


def write_sheet(path: Path, count: int) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["board", "solved", "minutes", "got_stuck_where", "underivable", "tedious", "boring", "notes"])
        for index in range(1, count + 1):
            writer.writerow([f"{index:02d}", "", "", "", "", "", "", ""])


def shipping_games() -> tuple[dict[str, str], set[str]]:
    """The games behind the boards that will actually ship, from the calendar.

    ⚠️⚠️ **The pack drew its own sample until 2026-08-22, and at a different gate.** It called
    `load(SAMPLE_PER_DECADE, gated=True, gate=HAND_SOLVE_ZERO_DENSITY_GATE)` — a fresh draw at **0.25**
    against the shipping **0.30** — so it graded a population that is not the inventory, on two counts.

    ⚠️ **The deviation was reasoned, and the reason stopped applying.** It said the sample is *"chosen to
    answer whether this is derivable by a human rather than to be representative"*. Under that framing
    it is defensible. **The gate's job is not derivability in general — it is to confirm that no
    publishable board is impossible**, and for that question being representative is not a nicety, it is
    the entire claim. *A justification is scoped and does not travel.*

    **So the pack draws from the calendar**, through `load(also=...)` — which exists for exactly this:
    naming the boards to be examined rather than hoping a draw contains them.
    """
    calendar = read_calendar(CALENDAR)
    generations = {entry.assigned for entry in calendar}
    # ⚠️ **The puzzle id is kept, not discarded.** This built the same map and returned only its keys,
    # so the one fact that ties a board to the data it came from was read off disk and thrown away.
    # `write_provenance` needs it (`docs/reloading-retrosheet.md` §8).
    assigned: dict[str, str] = {}
    for entry in calendar:
        for generation in generations:
            package = INVENTORY / generation / f"{entry.puzzle_id}.json"
            if package.exists():
                assigned[entry.game_id] = entry.puzzle_id
                break
    if not assigned:
        message = f"no packages found for {len(calendar)} calendar entries under {INVENTORY}"
        raise SystemExit(message)
    return assigned, generations


def main() -> None:
    """⚠️⚠️ **RETIRED 2026-08-26. Pack A is deleted and no pack may be built from this file.**

    The operator solved sixteen boards by hand, none was guessed, and **the gate closed on that**
    (`docs/beta-0.md`, Deliverable B). Pack A's own question -- does the difficulty ordering match felt
    difficulty -- was answered *no*, and the calibration that would have followed was withdrawn rather
    than resized: he now has complete command of the identities, so **he is no longer an instrument that
    discriminates.** The sixteen ratings and their game ids are transcribed in `docs/reviews/todo.md`;
    the boards, the PDFs, the recording sheets and the answer keys are gone.

    ⚠️⚠️ **The MODULE stays, and that is deliberate rather than an incomplete delete.** `CLAUDE.md`:
    *retirement is a refusal in `main()`, not a deletion and not a move -- the file stays where its tests
    and its history are.* **Five test files use its renderer as an independent second implementation** --
    the footnote line, the slot references, the innings notation, the row labels, and the erased-board
    parity -- which is §22's no-shared-code principle in miniature. Deleting the file took twenty guards
    with it and none of them was about the pack.

    ⚠️ **What it is NOT any more: a tool.** Building a pack would need the answer keys back on disk, and
    a key committed once is disclosed permanently.
    """
    message = (
        "build_pack is retired: Pack A was deleted on 2026-08-26 and its result is in "
        "docs/reviews/todo.md. The renderer stays because five test files use it; the pack does not. "
        "See docs/beta-0.md Deliverable B for what closed the hand-solve gate."
    )
    raise SystemExit(message)


def _unreachable_main() -> None:
    rng = random.Random(PICK_SEED)
    assigned, generations = shipping_games()
    # ⚠⚠ **No `load()`, and therefore no database.** The boards are read from the signed packages the
    # calendar names. The pack used to reload every game and erase it again, which is the whole of the
    # 3% finding — see `shipped()`. What is left needs the inventory directory and nothing else.
    pool = shipped(assigned, generations)
    chosen = choose(pool, rng)

    # ⚠⚠ **Before the audit, and it was after it.** A refusal reported the unmet quota and **not the
    # population it drew from** — which is the one datum needed to tell a pack that filtered badly from
    # an inventory that has no hard boards. It cost a second run to learn what the first already knew.
    #
    # ⚠️ **A check that refuses without saying what it saw is half a check.** The audit still raises;
    # what changed is that everything it looked at is on the terminal before it does.
    report(pool, len(assigned), chosen)
    audit(chosen)

    out = Path(__file__).resolve().parent
    build_pdf(out / "boards.pdf", chosen, answers=False)
    build_pdf(out / "solutions.pdf", chosen, answers=True)
    write_key(out / "key.csv", chosen)
    # ⚠️ Written beside the key rather than inside it, so provenance can be checked without opening
    # an answer. See `write_provenance`.
    write_provenance(out / "provenance.json", chosen, assigned, generations)
    write_sheet(out / "recording-sheet.csv", len(chosen))

    print(f"wrote {out / 'boards.pdf'}, solutions.pdf, key.csv, recording-sheet.csv, provenance.json")


def report(pool: list[Candidate], calendar_size: int, chosen: list[Candidate]) -> None:
    """What the run saw, printed **before** the audit decides.

    ⚠️ **Includes the pool's own rung distribution, not only the chosen one.** *Rung 12 has 3 boards
    against a quota of 4* does not say whether the pool held four; the two lines together do, and that
    is the difference between *the pack filtered badly* and *the inventory has no hard boards*.
    """
    certified = sum(1 for candidate in chosen if candidate.certified)
    uncertified = len(chosen) - certified
    available: dict[int, int] = {}
    for candidate in pool:
        available[candidate.target] = available.get(candidate.target, 0) + 1
    by_target: dict[int, int] = {}
    for candidate in chosen:
        by_target[candidate.target] = by_target.get(candidate.target, 0) + 1
    print(f"pool: {len(pool)} shipped boards at a target rung, from {calendar_size} calendar entries")
    print(f"pool by stall rung: {dict(sorted(available.items()))}")
    # ⚠️⚠️ **Both halves, and the pool's share beside them.** The certification quota was removed on
    # 2026-08-23, so this number is **observed rather than chosen** — and a reader who meets a pack that
    # is 15/16 uncertified must be able to tell that from a pack that was *built* that way. The pool
    # line says whether the pack's mix is the inventory's mix.
    in_pool = sum(1 for candidate in pool if candidate.certified)
    print(
        f"chosen: {len(chosen)} boards, {certified} certified and {uncertified} uncertified by layer 3b "
        f"(pool: {in_pool} of {len(pool)} certified) -- not filtered on, reported"
    )
    print(f"chosen by stall rung: {dict(sorted(by_target.items()))}")
    print(f"pre-1950: {sum(1 for c in chosen if c.season < 1950)} (allowance {PRE_1950_ALLOWANCE})")
    print(f"with a substitution: {sum(1 for c in chosen if c.has_substitution)}")
    print(f"with a live footnote: {sum(1 for c in chosen if c.has_live_footnote)}")


if __name__ == "__main__":
    main()
