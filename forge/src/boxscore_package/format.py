"""The puzzle package: the artefact that crosses between the generator and everything else.

⚠️ **This package belongs to neither side.** §22 requires the verifier to share no code with the
generator, so anything they genuinely both need — and a file format is exactly that — lives here
instead of in either of them. Nothing in this module reasons about a puzzle. It reads, writes, and
says what the fields are called. If logic ever appears here, the separation has been quietly undone.

**The board is stored as arrays, not as named cells.** A naming grammar would be a shared vocabulary
that one side invented and the other inherited, and inheriting a mistake is precisely what §22 is
guarding against. Arrays fix the column order and nothing else; each side names cells however it
likes internally.

**Two halves, and both of them travel.** `puzzle` is what a player receives — erased cells are null.
`solution` is the completed board, which §22's fourth layer solves the published half against, and which
the client needs to validate an entry with the backend down (§23).

⚠️ **This paragraph said the opposite, in the same file as the code that reversed it.** It described a
field called `source` being *stripped before serving*, while `published()` twenty pages down carries a
warning explaining why it no longer removes the solution. Two places, one file, contradicting each other
— and the field had also been renamed. What `published()` actually removes is the metadata that would
give the game away.

Innings pitched are stored as **outs**, not as the `x.y` the board displays. Every value in the
format is an integer, and one of §3's cross-team identities is stated in outs: the outs made by the
offense equal the outs recorded by the opposing pitchers.
"""

import json
import re
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Final, Self

from boxscore_domain import MAX_INNINGS

SCHEMA_VERSION: Final = 5
"""What this code writes.

⚠️ **Version 5 exists because the reveal became a boxscore instead of a legend.** Version 4's
`reveal` carried the names of the rows the board drew and nothing else, so the finished screen could
only redraw the board the player had just filled in with names attached. A printed boxscore is a
different object: it has both clubs, it has runs batted in, and it names the teams rather than
abbreviating them.

**The board is unchanged and this is deliberate.** §6 is a screen budget for the *playing* board and
nothing here touches it — `puzzle`, `solution`, `labels` and `slot_references` are byte-identical to
what version 4 wrote. The new block is display-only, feeds no deduction, and is read by nothing the
four validation layers depend on.

⚠⚠ **And it is a version rather than a tightening, by the test one paragraph down.** Every schema-4
file in the repository would be *rejected* by this reader, because `reveal.boxscore` is required
whenever a reveal is present. A document that used to be valid and now is not is exactly the case that
must not reuse a number.

⚠⚠ **It carries a rule the calendar has to keep, and the package cannot.** The reveal now prints
both clubs, and the other club's half **is the other puzzle of that game** — §5 makes a game up to two
boards, one per direction. Publishing both directions of one game hands the second one away in the
first one's reveal. The decision taken with this version is **one game, one puzzle**: the pool is
400,000+ directions, so spending a whole game on each board costs nothing measurable. `write` cannot
enforce it — it sees one package and the rule is about a set — so it is enforced where sets are
assembled and asserted in `write_reference_puzzles.py`. **When the calendar is built it inherits the
obligation**, and there is a note in CLAUDE.md saying so.

⚠️ **Version 4 was tightened once, in place, and here is the test that allowed it.** As first cut it
left `solution` optional and `left_on_base` nullable on this side while the browser required both, and
it parsed the answer board with the puzzle's nullable rule — so a null answer under a visible blank was
accepted by both readers, and the cell then read blank *and* counted as correct while entering any
number was wrong.

Tightening a version in place is what this docstring argues against one paragraph down, so the reason
has to be re-derived rather than carried across. **The test used: does the change alter the status of
any artifact that exists?** Every schema-4 file in the repository — both generations, twelve packages —
is accepted before and after. No document changes meaning, so `schema: 4` does not come to mean two
things, which is the whole hazard the version rule exists to prevent. Had one file flipped, this would
have been schema 5.

⚠️ **Version 4 exists because version 3 could describe a board nobody can finish.** It allowed a
per-batter footnote cell to be null, which was right while those cells were erasable. They are given
now — the pool run found coverage identical either way, because 96% of the pool's footnote terms are
zero — and the renderer draws the line as read-only text with no editable element in it.

That left three layers disagreeing: the reader accepted the null, `createGame` counted it as a blank the
player owes, and the UI offered nothing to fill it with. **Reproduced rather than reasoned about**: the
retained generation's first package is accepted, holds 33 blanks of which 14 are footnotes, and its
footnote line renders 0 editable elements. Every visible blank can be filled and the board never
completes.

A nullable field becoming non-nullable is a change in what the document *means*, not a field going
missing, so it is a new version rather than a tightening of the old one. Tightening 3 in place would
make `schema: 3` mean one thing in a file written last week and another in a file written today — which
is this project's named failure shape wearing the version number as a disguise.

⚠️ **Version 3 exists because the package could not say which club batted last.** The line score has an
offensive half and a defensive half, and nothing in the file said which of the two was at home — so a
client rendering `Away` over the offensive row was **stating a fact it had never been told**, and on the
reference set it was wrong. *A label sits outside the arithmetic*, which is exactly why every total
still balanced while the board said something false.

The ragged line score determines it where the halves differ — the home side leading after the top of the
ninth never bats again — but four of the six reference packages are nine and nine. A client inferring it
*where it could* would be right sometimes and silently wrong the rest of the time, which is worse than
not knowing. So the forge, which has the fact, writes it down.
"""

READABLE: Final = (SCHEMA_VERSION,)
"""⚠️ **A version is not amended, it is replaced.** Slot references were not an addition to version 1 —
without them a client cannot resolve `SH: 9b` to a row, so the package meant something *different*
rather than something *more*. `offense_is_home` is the same kind of change against version 2: a board
that cannot name its sides is not a board with one field missing, it is a board that renders a false
statement. And a board carrying a blank no interface can reach is not a version-3 board with stricter
data — it is a board that cannot be played, which is why version 4 replaces 3 rather than narrowing it.

Cutting it now is the point. Nothing is published, `serve` does not exist, and there is nothing to
migrate — **a version scheme first exercised under pressure is one that gets skipped.**

⚠️ **Version 1 was listed here and the promise was false.** A v1 signature is 64 hex of HMAC and this
parser accepts only the 128 of Ed25519, so an authentic v1 file was rejected at the boundary while
three places claimed it would parse — and no test caught it, because the schema tests build objects
and read `as_json()` without going through `from_json`. The fix is to drop the promise rather than
write a legacy verifier nobody will run: **no consumer of version 1 exists**, and keeping it would be a
mechanism preserved past its problem.
"""

BATTING_COLUMNS: Final = ("plate_appearances", "at_bats", "runs", "hits", "walks", "strikeouts")
"""PA, AB, R, H, BB, SO — the six the board shows (§6). Order is part of the format."""

FOOTNOTE_COLUMNS: Final = ("hit_by_pitch", "sacrifice_flies", "sacrifice_hits", "catcher_interference")
"""HBP, SF, SH, CI — the footnote line, **given in full: no cell here is erasable** (§6).

⚠️ **This docstring has now been wrong in both directions, which is the point of the warning.** It
said the cells were given while §6 had opened them; it was corrected to say they were erasable; and the
pool run then closed them again, leaving it wrong a second time until someone read it. The decision
itself: the cells were opened on a measurement counting the solver deducing zeros — 96% of the pool's
footnote terms are zero — and the pool run found coverage identical with them erasable and with them
given, at every target. Everything built for the open case was deleted rather than disabled.

The authority is `erasure.erasable()`, which returns no footnote cell, and the test asserting no
reference package carries a footnote blank. A docstring is not a check.
"""

PITCHING_COLUMNS: Final = ("outs", "hits", "runs", "earned_runs", "walks", "strikeouts")
"""IP, H, R, ER, BB, SO, with innings held as outs."""

SLOT_REFERENCE = re.compile(r"^[1-9][a-z]?$")
"""`9` where a lineup slot holds one row, `9a`/`9b` where it is shared — the string the board draws and
the footnote line prints, **produced once on the forge and never derived by a client**.

Deriving it there would be a second copy of a baseball rule, and a wrong one attaches a footnote term
to the wrong row: the row identity then fails while every column total still balances.
"""

PUZZLE_ID = re.compile(r"^[0-9a-f]{16}$")
"""Opaque, sixteen hex characters, as the format document states.

Checked because the identifier reaches filenames and will reach URLs. An id that is not what the
contract says is not a smaller problem than a malformed board — it is the same problem somewhere the
board's own validation never looks.
"""

SIGNATURE = re.compile(r"^[0-9a-f]{128}$")
"""Ed25519, hex — 64 bytes, so 128 characters. It was 64 for HMAC-SHA256, and the length changing is
part of why this is schema 2 rather than an amendment to schema 1. A signature of the wrong
*type* used to reach the comparison, which raises
rather than refusing — a malformed file crashing the verifier instead of being rejected by it."""


class PackageError(Exception):
    """The file is not a puzzle package, or is a version this code does not know."""


def _cells(raw: object, width: int, where: str) -> tuple[int | None, ...]:
    """One row of the grid, checked at the boundary rather than three layers later.

    A package that is valid JSON and malformed as a board must produce a controlled `PackageError`
    here, not a `TypeError` inside the arithmetic. The distinction matters because the second one
    reads as a crash and the first one reads as a rejection.
    """
    if not isinstance(raw, list):
        message = f"{where} is {type(raw).__name__}, expected a list of {width} values"
        raise PackageError(message)
    if len(raw) != width:
        message = f"{where} holds {len(raw)} values, expected {width}"
        raise PackageError(message)
    for index, value in enumerate(raw):
        # bool is an int in Python and never a cell value, so it is excluded explicitly.
        if value is None:
            pass
        elif not isinstance(value, int) or isinstance(value, bool):
            message = f"{where}[{index}] is {value!r}, expected a whole number or null"
            raise PackageError(message)
    return tuple(raw)


def check_profile(board: object, where: str, *, complete: bool) -> None:
    """Which cells of a board may be blank. **One rule, used by construction and by parsing.**

    | profile | may be blank |
    |---|---|
    | puzzle (`complete=False`) | the batting and pitching grids, and their totals rows |
    | answer (`complete=True`) | nothing, anywhere |

    The footnote line and `left_on_base` are given in both: §6 never erases them, and the row identity
    does not close without the footnote totals.

    ⚠️ **This lives outside `from_json` because the null policy applied only at the parse boundary let
    the type write what it could not read.** A directly constructed `Package` carrying an answer board
    with one null cell was accepted, `as_json()` emitted the null, and `from_json()` refused the
    document its own writer had just produced. **A format that cannot read back its own output is not a
    format**, and the asymmetry is invisible to anyone who only ever round-trips valid data.

    Same shape and same fix as `_check_slot_references` below, which was hoisted for exactly this after
    `__post_init__` and `from_json` were found applying different subsets of one rule.

    ⚠️ **The parameter is `object`, not `Board`, and that is the point.** Annotated `Board`, mypy calls
    the `isinstance` below unreachable — correctly, for code it can see. But a frozen dataclass does not
    check its own field types at runtime, so a directly built `Package` can carry a `str` where a board
    belongs, and it did: the value travelled to `as_json()` and died there with an `AttributeError`
    instead of being refused at the boundary that created it. **A type is a promise; this is the check.**
    """
    if not isinstance(board, Board):
        message = f"{where} is {type(board).__name__}, expected a board"
        raise PackageError(message)
    # Widened deliberately, same reason: the annotation says `int` and nothing enforces it.
    left_on_base: object = board.left_on_base
    if not isinstance(left_on_base, int) or isinstance(left_on_base, bool):
        message = f"{where}.left_on_base is {left_on_base!r}; §6 never erases it"
        raise PackageError(message)

    always: list[tuple[str, tuple[tuple[int | None, ...], ...]]] = [("footnotes", board.footnotes)]
    grids: list[tuple[str, tuple[tuple[int | None, ...], ...]]] = [
        ("batting", board.batting),
        ("pitching", board.pitching),
    ]
    for name, rows in always + (grids if complete else []):
        for index, row in enumerate(rows):
            if any(cell is None for cell in row):
                message = f"{where}.{name}[{index}] has a blank and must be given"
                raise PackageError(message)

    totals: list[tuple[str, tuple[int | None, ...]]] = [("footnote_totals", board.footnote_totals)]
    if complete:
        totals += [("batting_totals", board.batting_totals), ("pitching_totals", board.pitching_totals)]
    for name, row in totals:
        if any(cell is None for cell in row):
            message = f"{where}.{name} has a blank and must be given"
            raise PackageError(message)


def _rows(raw: object, width: int, where: str) -> tuple[tuple[int | None, ...], ...]:
    """The rows of a grid: shape and cell type only.

    ⚠️ **Which cells may be blank is not decided here.** That is `check_profile`, and it is one
    function because it has to answer for a board built in memory as well as one parsed from a
    document — `as_json()` could emit an answer board with a hole that `from_json()` then refused,
    which is a format that cannot read back what it writes.
    """
    if not isinstance(raw, list):
        message = f"{where} is {type(raw).__name__}, expected a list of rows"
        raise PackageError(message)
    return tuple(_cells(row, width, f"{where}[{index}]") for index, row in enumerate(raw))


def _required(raw: dict[str, Any], field: str) -> object:
    """The field, or a refusal naming it. Absent and null are one answer here: both mean *not given*."""
    value = raw.get(field)
    if value is None:
        message = f"the package has no {field}"
        raise PackageError(message)
    return value


def _whole_number(raw: object, where: str) -> int:
    if not isinstance(raw, int) or isinstance(raw, bool):
        message = f"{where} is {raw!r}, expected a whole number"
        raise PackageError(message)
    return raw


def _innings(raw: object, where: str) -> tuple[int, ...]:
    if not isinstance(raw, list):
        message = f"{where} is {type(raw).__name__}, expected a list of innings"
        raise PackageError(message)
    # ⚠⚠ **The inning cap enforced where it cannot be bypassed.** `MAX_INNINGS` was decided from a
    # width measurement and recorded, and for a while that was all: nothing rejected a longer board, so
    # the generator could still build one and the cap was a note rather than a gate. **An incomplete
    # gate looks like a gate and is not one.**
    #
    # Checked at the package boundary rather than in the sampler, because this is the seam every board
    # crosses on its way out — §22's rule that validation happens at the boundary and fails closed. A
    # filter in `load()` would bound what the *generator draws from*; it would not stop a board reaching
    # a player, and the pool query cannot count innings anyway (Retrosheet writes a ten-run inning as
    # `(10)`, so the string length is not the count).
    if len(raw) > MAX_INNINGS:
        message = f"{where} has {len(raw)} innings, more than the {MAX_INNINGS} the board can draw (§6)"
        raise PackageError(message)
    return tuple(_whole_number(value, f"{where}[{index}]") for index, value in enumerate(raw))


@dataclass(frozen=True, slots=True)
class LineScore:
    """The board's anchor: always shown complete, never erased (§6)."""

    offense_by_inning: tuple[int, ...]
    defense_by_inning: tuple[int, ...]
    offense_runs: int
    offense_hits: int
    offense_errors: int
    defense_runs: int
    defense_hits: int
    defense_errors: int

    def as_json(self) -> dict[str, Any]:
        return {
            "offense_by_inning": list(self.offense_by_inning),
            "defense_by_inning": list(self.defense_by_inning),
            "offense_runs": self.offense_runs,
            "offense_hits": self.offense_hits,
            "offense_errors": self.offense_errors,
            "defense_runs": self.defense_runs,
            "defense_hits": self.defense_hits,
            "defense_errors": self.defense_errors,
        }

    @classmethod
    def from_json(cls, raw: object) -> Self:
        """The line score is the board's anchor and is always complete (§6), so every field is required."""
        if not isinstance(raw, dict):
            message = f"the line score is {type(raw).__name__}, expected an object"
            raise PackageError(message)
        missing = [
            field
            for field in (
                "offense_by_inning",
                "defense_by_inning",
                "offense_runs",
                "offense_hits",
                "offense_errors",
                "defense_runs",
                "defense_hits",
                "defense_errors",
            )
            if field not in raw
        ]
        if missing:
            message = f"the line score is missing {', '.join(missing)}"
            raise PackageError(message)
        return cls(
            offense_by_inning=_innings(raw["offense_by_inning"], "line_score.offense_by_inning"),
            defense_by_inning=_innings(raw["defense_by_inning"], "line_score.defense_by_inning"),
            offense_runs=_whole_number(raw["offense_runs"], "line_score.offense_runs"),
            offense_hits=_whole_number(raw["offense_hits"], "line_score.offense_hits"),
            offense_errors=_whole_number(raw["offense_errors"], "line_score.offense_errors"),
            defense_runs=_whole_number(raw["defense_runs"], "line_score.defense_runs"),
            defense_hits=_whole_number(raw["defense_hits"], "line_score.defense_hits"),
            defense_errors=_whole_number(raw["defense_errors"], "line_score.defense_errors"),
        )


@dataclass(frozen=True, slots=True)
class Board:
    """A board, whole or partly erased.

    `None` in a grid cell means the player has to work it out. **Nothing in the footnote line is ever
    `None`** — not the totals row, not the team footnote, not the per-batter cells — and neither is the
    line score.

    ⚠️ **This sentence has now been wrong in both directions, which is why it is worth a warning.** It
    said the per-batter cells were given while §6 had opened them; it was corrected to say they were
    erasable; the pool run then closed them again and it went on saying the opposite until a review
    read it. From schema 4 the reader enforces it, so the two cannot disagree again — but a docstring is
    still not a check, and `erasure.erasable()` is the authority on what may be removed.

    The format does not enforce the rest, because a verifier that trusts the format to reject malformed
    input is a verifier that checks nothing.
    """

    batting: tuple[tuple[int | None, ...], ...]
    batting_totals: tuple[int | None, ...]
    footnotes: tuple[tuple[int | None, ...], ...]
    footnote_totals: tuple[int | None, ...]
    left_on_base: int
    """Never erased: without it the board cannot express the global identity at all (§6).

    ⚠️ **This was `int | None` while the browser reader required a whole number**, so the forge could
    build and sign a board the client refused at boot — the producer/consumer split schema 4 was cut to
    remove, inside schema 4.
    """
    pitching: tuple[tuple[int | None, ...], ...]
    pitching_totals: tuple[int | None, ...]
    line_score: LineScore

    def as_json(self) -> dict[str, Any]:
        return {
            "batting": [list(row) for row in self.batting],
            "batting_totals": list(self.batting_totals),
            "footnotes": [list(row) for row in self.footnotes],
            "footnote_totals": list(self.footnote_totals),
            "left_on_base": self.left_on_base,
            "pitching": [list(row) for row in self.pitching],
            "pitching_totals": list(self.pitching_totals),
            "line_score": self.line_score.as_json(),
        }

    @classmethod
    def from_json(cls, raw: object, *, complete: bool = False) -> Self:
        """A board. **`complete` is the answer board, where no cell may be missing.**

        ⚠️ **Two profiles, because one nullable rule for both was wrong in a way the player meets.**
        A puzzle carries blanks in the batting and pitching grids and their totals; an answer board
        carries none anywhere. Parsed with one rule, a null answer under a visible blank was accepted
        by both readers — and then `isCorrect` returned true for a cell still drawn empty, while
        entering any number was necessarily wrong. **Reproduced before this was written**: the cell
        read blank, counted as correct, and rejected `0`.

        Both readers now refuse it, which is the point: a rule enforced on one side is a rule the two
        sides disagree about.
        """
        if not isinstance(raw, dict):
            message = f"a board is {type(raw).__name__}, expected an object"
            raise PackageError(message)
        batting = _rows(raw.get("batting"), len(BATTING_COLUMNS), "batting")
        footnotes = _rows(raw.get("footnotes"), len(FOOTNOTE_COLUMNS), "footnotes")
        if len(footnotes) != len(batting):
            message = f"{len(footnotes)} footnote rows against {len(batting)} batting rows"
            raise PackageError(message)
        board = cls(
            batting=batting,
            batting_totals=_cells(raw.get("batting_totals"), len(BATTING_COLUMNS), "batting_totals"),
            footnotes=footnotes,
            # The footnote TOTALS row is never erased — the row identity does not close without it —
            # so a null in it is
            # malformed rather than difficult.
            footnote_totals=_cells(raw.get("footnote_totals"), len(FOOTNOTE_COLUMNS), "footnote_totals"),
            left_on_base=_whole_number(raw.get("left_on_base"), "left_on_base"),
            pitching=_rows(raw.get("pitching"), len(PITCHING_COLUMNS), "pitching"),
            pitching_totals=_cells(raw.get("pitching_totals"), len(PITCHING_COLUMNS), "pitching_totals"),
            line_score=LineScore.from_json(raw.get("line_score", {})),
        )
        # The policy, after the shape. One function, so parsing and construction cannot diverge.
        check_profile(board, "board", complete=complete)
        return board


LEAKING_METADATA: Final = frozenset({"game_id", "retrosheet_id", "season", "date", "teams"})
"""Metadata keys that would hand over the mystery, removed by `published()`.

⚠️ Found while writing the schema down. The opaque puzzle id exists so that nothing in the URL names
the teams or the date (§7), and `metadata` is deliberately loose so seam C3 can carry anything — which
means the loose half is the hole. An id that reveals nothing beside a metadata block holding
`game_id` protects nothing.
"""


@dataclass(frozen=True, slots=True)
class PrintedBatter:
    """One batting line as a newspaper set it: **AB R H RBI**, plus the two the player deduced.

    ⚠️ **`RBI` is here and not on the board, and that is the point.** §6 gives the board six columns
    and `PA` takes one of them because `PA` is what breaks the constraint forest. `RBI` earns none of
    that — it has no cross-team counterpart and no place in the row identity — which is exactly why it
    is worth printing at the end: it is the one number on the finished sheet the puzzle never asked
    for, so the reveal tells the player something instead of repeating what they worked out.

    ⚠️ **`PA` is not here.** It is a column of the board, not of a boxscore; no newspaper printed it.
    """

    name: str
    position: str
    at_bats: int
    runs: int
    hits: int
    runs_batted_in: int
    walks: int
    strikeouts: int

    def as_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "position": self.position,
            "ab": self.at_bats,
            "r": self.runs,
            "h": self.hits,
            "rbi": self.runs_batted_in,
            "bb": self.walks,
            "so": self.strikeouts,
        }

    @classmethod
    def from_json(cls, raw: object, where: str) -> Self:
        row = _object(raw, where)
        return cls(
            name=_text(_required(row, "name"), f"{where}.name"),
            position=_text(_required(row, "position"), f"{where}.position"),
            at_bats=_whole_number(_required(row, "ab"), f"{where}.ab"),
            runs=_whole_number(_required(row, "r"), f"{where}.r"),
            hits=_whole_number(_required(row, "h"), f"{where}.h"),
            runs_batted_in=_whole_number(_required(row, "rbi"), f"{where}.rbi"),
            walks=_whole_number(_required(row, "bb"), f"{where}.bb"),
            strikeouts=_whole_number(_required(row, "so"), f"{where}.so"),
        )


@dataclass(frozen=True, slots=True)
class PrintedPitcher:
    """One pitching line, in the order the men appeared. `outs`, not innings — see `_innings`."""

    name: str
    role: str
    outs: int
    hits: int
    runs: int
    earned_runs: int
    walks: int
    strikeouts: int

    def as_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "outs": self.outs,
            "h": self.hits,
            "r": self.runs,
            "er": self.earned_runs,
            "bb": self.walks,
            "so": self.strikeouts,
        }

    @classmethod
    def from_json(cls, raw: object, where: str) -> Self:
        row = _object(raw, where)
        return cls(
            name=_text(_required(row, "name"), f"{where}.name"),
            role=_text(_required(row, "role"), f"{where}.role"),
            outs=_whole_number(_required(row, "outs"), f"{where}.outs"),
            hits=_whole_number(_required(row, "h"), f"{where}.h"),
            runs=_whole_number(_required(row, "r"), f"{where}.r"),
            earned_runs=_whole_number(_required(row, "er"), f"{where}.er"),
            walks=_whole_number(_required(row, "bb"), f"{where}.bb"),
            strikeouts=_whole_number(_required(row, "so"), f"{where}.so"),
        )


@dataclass(frozen=True, slots=True)
class PrintedSide:
    """One club's half of the printed sheet: who it is, who batted, who pitched.

    ⚠️ **`city` and `nickname` are separate and both are required.** A boxscore is headed *St. Louis
    Browns*, not *SLA*; the three-letter code is Retrosheet's key, and a player who has just earned the
    answer should not be handed an abbreviation. They are two fields rather than one string because the
    narrow places on a phone print the city alone — a line score has ten numeric columns at 375px and no
    room for a nickname — and a renderer that had to split a joined string would be guessing where the
    city ends.

    Both non-empty, and there is no ambiguous case to arbitrate: **`retroTeams` resolves 2,892 of 2,901
    team-seasons in the pool to exactly one row, and the nine that fail resolve to *zero* rather than to
    two** — all Negro League and exhibition clubs whose season windows do not cover the game. So the
    only failure is an absent name, and the loader drops that direction rather than shipping a board
    whose reveal cannot name the club.

    `code` is kept: it is what the puzzle id derives from, and it is what a curious player looks the
    game up with.
    """

    code: str
    city: str
    nickname: str
    batting: tuple[PrintedBatter, ...]
    pitching: tuple[PrintedPitcher, ...]

    def as_json(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "city": self.city,
            "nickname": self.nickname,
            "batting": [row.as_json() for row in self.batting],
            "pitching": [row.as_json() for row in self.pitching],
        }

    @classmethod
    def from_json(cls, raw: object, where: str) -> Self:
        side = _object(raw, where)
        code = _text(_required(side, "code"), f"{where}.code")
        city = _text(_required(side, "city"), f"{where}.city")
        nickname = _text(_required(side, "nickname"), f"{where}.nickname")
        # ⚠️ Fail closed on a blank rather than fall back to the code. A reveal headed `SLA` is the
        # thing this version exists to remove, and a renderer that silently substituted the
        # abbreviation would make the absence invisible — the absence of a name reading as the
        # presence of a poor one.
        for value, name in ((code, "code"), (city, "city"), (nickname, "nickname")):
            if not value.strip():
                message = f"{where}.{name} is blank; a printed boxscore has to name the club"
                raise PackageError(message)
        return cls(
            code=code,
            city=city,
            nickname=nickname,
            batting=tuple(
                PrintedBatter.from_json(row, f"{where}.batting[{index}]")
                for index, row in enumerate(_list(_required(side, "batting"), f"{where}.batting"))
            ),
            pitching=tuple(
                PrintedPitcher.from_json(row, f"{where}.pitching[{index}]")
                for index, row in enumerate(_list(_required(side, "pitching"), f"{where}.pitching"))
            ),
        )


@dataclass(frozen=True, slots=True)
class PrintedBoxscore:
    """Both clubs, complete — the object the player reconstructed half of.

    ⚠️⚠️ **`offense` and `defense` name the *puzzle's* sides, not the game's.** The offence is the club
    whose batting the board carried; the defence is the club whose pitching it carried. Each side here
    holds **both** its batting and its pitching, so `offense.pitching` and `defense.batting` are the
    half the board never showed. Named after the puzzle rather than after home and away so that one
    vocabulary runs through the package — `offense_is_home` already means this.
    """

    offense: PrintedSide
    defense: PrintedSide

    def as_json(self) -> dict[str, Any]:
        return {"offense": self.offense.as_json(), "defense": self.defense.as_json()}

    @classmethod
    def from_json(cls, raw: object, where: str = "reveal.boxscore") -> Self:
        block = _object(raw, where)
        return cls(
            offense=PrintedSide.from_json(_required(block, "offense"), f"{where}.offense"),
            defense=PrintedSide.from_json(_required(block, "defense"), f"{where}.defense"),
        )


@dataclass(frozen=True, slots=True)
class Reveal:
    """What the player earns: the names, the teams, the date, and the card (§7, §29).

    ⚠️ **This is the answer to the mystery and it ships inside the package.** §23 requires the game to
    work with the backend down, so the client cannot fetch the reveal when a row is completed — it has
    to be holding it already. §9 accepts that a determined player can read it in devtools, and that is
    a deliberate trade rather than an oversight: the alternative is a network dependency in the play
    path, which is the one thing §23 forbids.

    Nothing here may reach the board's labels, and nothing here may be encoded in the puzzle id.
    """

    batter_names: tuple[str, ...]
    pitcher_names: tuple[str, ...]
    offense_team: str
    defense_team: str
    played_on: str
    boxscore: PrintedBoxscore
    """The complete printed sheet, both clubs. **Required from schema 5.**

    ⚠️ **It repeats the board's numbers, and the repetition is checked rather than trusted.** The
    offence's `AB R H BB SO` and the defence's whole pitching line are already in `solution`, so this
    is two places holding one set of facts — the shape every serious defect in this project has had.
    The alternative was a block carrying only the *new* half, leaving the renderer to stitch a printed
    sheet from two sources with different row orders, which trades a checkable duplication for an
    unchecked join. So it is duplicated on purpose and `check_reveal_agrees` asserts the two agree
    cell by cell on every column they share, at the boundary, for every package written or read.
    """

    card: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "batter_names": list(self.batter_names),
            "pitcher_names": list(self.pitcher_names),
            "offense_team": self.offense_team,
            "defense_team": self.defense_team,
            "played_on": self.played_on,
            "boxscore": self.boxscore.as_json(),
            "card": self.card,
        }

    @classmethod
    def from_json(cls, raw: object) -> Self:
        if not isinstance(raw, dict):
            message = f"reveal is {type(raw).__name__}, expected an object"
            raise PackageError(message)
        return cls(
            batter_names=tuple(_strings(raw.get("batter_names"), "reveal.batter_names")),
            pitcher_names=tuple(_strings(raw.get("pitcher_names"), "reveal.pitcher_names")),
            offense_team=_text(raw.get("offense_team"), "reveal.offense_team"),
            defense_team=_text(raw.get("defense_team"), "reveal.defense_team"),
            played_on=_text(raw.get("played_on"), "reveal.played_on"),
            boxscore=PrintedBoxscore.from_json(_required(raw, "boxscore")),
            card=_text(raw.get("card", ""), "reveal.card"),
        )


def _text(raw: object, where: str) -> str:
    if not isinstance(raw, str):
        message = f"{where} is {type(raw).__name__}, expected a string"
        raise PackageError(message)
    return raw


def _object(raw: object, where: str) -> dict[str, Any]:
    """A JSON object, refused at the boundary rather than three layers later as a `TypeError`."""
    if not isinstance(raw, dict):
        message = f"{where} is {type(raw).__name__}, expected an object"
        raise PackageError(message)
    return raw


def _list(raw: object, where: str) -> list[Any]:
    if not isinstance(raw, list):
        message = f"{where} is {type(raw).__name__}, expected a list"
        raise PackageError(message)
    return raw


def _strings(raw: object, where: str) -> list[str]:
    if not isinstance(raw, list):
        message = f"{where} is {type(raw).__name__}, expected a list of strings"
        raise PackageError(message)
    return [_text(value, f"{where}[{index}]") for index, value in enumerate(raw)]


_PRINTED_BATTING: Final = tuple(
    column for column in BATTING_COLUMNS if column in {entry.name for entry in fields(PrintedBatter)}
)
_PRINTED_PITCHING: Final = tuple(
    column for column in PITCHING_COLUMNS if column in {entry.name for entry in fields(PrintedPitcher)}
)
"""The columns the board and the printed sheet both carry, **derived rather than listed.**

Spelling them would be a third copy of the column order, and the order is a decision §6 already took
once. `plate_appearances` drops out of the first by itself, because `PrintedBatter` has no such field —
a boxscore does not print it — and every pitching column survives the second, because the two lines
happen to agree. A future column changes one dataclass and this follows.
"""


def check_reveal_agrees(reveal: "Reveal", solution: Board, labels: tuple[str, ...], roles: tuple[str, ...]) -> None:
    """The printed sheet and the board must say the same thing about the half they share.

    ⚠️⚠️ **This is the guard that makes the duplication safe, and without it schema 5 is a defect.**
    `reveal.boxscore.offense.batting` restates every batting column the board carries except `PA`, and
    `reveal.boxscore.defense.pitching` restates the whole pitching line. Two places holding one set of
    facts, with nothing checking they agree, is the shape of every serious defect this project has
    found. So they are checked — cell by cell, on every column they share, at the one boundary every
    package crosses in both directions.

    **It also checks the names and the labels**, which are duplicated the same way: `batter_names`
    and the printed rows both carry who batted, `labels` and the printed rows both carry where he
    played. A reveal whose two halves disagree about a row is exactly how a footnote ends up attributed
    to the wrong man while every total still balances.

    ⚠⚠ **What it does not check is the other half, and this docstring used to delegate that to a check
    that did not exist.** It said the unshared half "belongs to `certify_for_publication`, against the
    game log". `Evidence` carried no rows, no certification looked at them, and **the gate certified a
    package whose `defense.batting` and `offense.pitching` were whatever the producer put there** —
    the test fixture named those rows `Not A Real Player` and the gate accepted it. v30-P1-02. A
    forward reference to somebody else's check is the absence of a check reading as the presence of a
    passing one, and it was written the same day as the rule about it.

    `boxscore_verify.certify.check_printed_boxscore_corresponds` exists now and is registered. It
    compares the unshared grids with the line score, which comes from a different table: the defence's
    batters scored the defence's runs, the offence's staff allowed the same events from the other
    side, and its outs are bounded by the innings the defence batted.

    ⚠️ **It still cannot corroborate a row.** There is no independent source at row granularity, so
    which batter had the hits and what he was called is checked by nothing. That residual is stated in
    that function rather than forwarded again.
    """
    printed = reveal.boxscore
    if printed.offense.code != reveal.offense_team or printed.defense.code != reveal.defense_team:
        message = (
            f"reveal names {reveal.offense_team} against {reveal.defense_team} and its boxscore names "
            f"{printed.offense.code} against {printed.defense.code}"
        )
        raise PackageError(message)

    _check_rows(
        printed.offense.batting,
        solution.batting,
        BATTING_COLUMNS,
        _PRINTED_BATTING,
        names=reveal.batter_names,
        labels=labels,
        label_field="position",
        where="reveal.boxscore.offense.batting",
    )
    _check_rows(
        printed.defense.pitching,
        solution.pitching,
        PITCHING_COLUMNS,
        _PRINTED_PITCHING,
        names=reveal.pitcher_names,
        labels=roles,
        label_field="role",
        where="reveal.boxscore.defense.pitching",
    )


def _check_rows(  # noqa: PLR0913
    printed: tuple[Any, ...],
    board: tuple[tuple[int | None, ...], ...],
    columns: tuple[str, ...],
    shared: tuple[str, ...],
    *,
    names: tuple[str, ...],
    labels: tuple[str, ...],
    label_field: str,
    where: str,
) -> None:
    """One grid of the printed sheet against the board's own, row for row."""
    if len(printed) != len(board):
        message = f"{where} has {len(printed)} rows and the board has {len(board)}"
        raise PackageError(message)
    for index, (row, board_row) in enumerate(zip(printed, board, strict=True)):
        for column in shared:
            mine = getattr(row, column)
            theirs = board_row[columns.index(column)]
            if mine != theirs:
                message = f"{where}[{index}].{column} is {mine} and the board says {theirs}"
                raise PackageError(message)
        if index < len(names) and row.name != names[index]:
            message = f"{where}[{index}].name is {row.name!r} and the reveal names {names[index]!r}"
            raise PackageError(message)
        if index < len(labels) and getattr(row, label_field) != labels[index]:
            message = (
                f"{where}[{index}].{label_field} is {getattr(row, label_field)!r} "
                f"and the board's label is {labels[index]!r}"
            )
            raise PackageError(message)


@dataclass(frozen=True, slots=True)
class Package:
    """What the forge produces for one puzzle.

    `metadata` is deliberately loose: seam C3 requires rich metadata on every puzzle even when
    nothing reads it, and a format that had to be revised every time a new field was wanted would
    make that expensive. It is opaque to this module and to the verifier.
    """

    puzzle_id: str
    puzzle: Board
    solution: Board
    """The completed board. Ships with the puzzle — see `Reveal` for why, and §9 for the trade.

    ⚠️ **Required, and it defaulted to `None`.** The client cannot validate an entry without it, which
    §23 makes non-negotiable: with the backend down the board still has to be playable. So a package
    without one is not a package with a field missing — it is a puzzle nobody can play. The browser
    reader always said so; this side did not, and the gap let the forge build, sign and publish a
    document the browser refused at boot.
    """

    labels: tuple[str, ...] = ()
    """One per batting row: the **bare** position the man entered at — `CF`, `SS`, `P`.

    ⚠️ **Never suffixed, and this said the opposite.** The suffix was removed when it turned out three
    separate decisions were reading it as a lineup-slot marker; `slot_references` carries that now, and
    two rows may both read `CF`.
    """

    pitcher_labels: tuple[str, ...] = ()
    """`SP`, then `RP-1` onwards in order of appearance. Never a bare `P` (§5)."""

    reveal: Reveal | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    slot_references: tuple[str, ...] | None = None
    """Required. Typed optional only so the field can carry a default position in the dataclass; a
    package without it raises at construction."""
    """One per batting row, in row order. Required from schema 2; absent in version 1 packages.

    **Pitching rows carry none, deliberately.** Those are the *opposing* team's pitchers and have no
    place in this batting order, so a slot there would name a row that does not exist.
    """

    offense_is_home: bool | None = None
    """Which half of the line score batted last. **Required from schema 3.**

    Top-level rather than inside `Board`, because a board is stored twice — once as the puzzle and once
    as the solution — and one fact stored in two places is this project's named failure shape. `None`
    is the absence the constructor refuses, not a third state.
    """

    schema: int | None = None
    """The version this package *is*, checked against the payload rather than trusted.

    ⚠️ **A version is a statement about the payload, not a stamp applied to it.** A package carrying
    slot references is a version 2 package and one without them is a version 1 package, so the two
    cannot disagree: `written_as` derives it. Set it explicitly only to assert what a parsed document
    claimed.
    """

    def __post_init__(self) -> None:
        """⚠️ **This returned early when `schema` was `None`, which is the normal path.**

        So the ordinary constructor produced a package with no references, `written_as` labelled it
        schema 2, `as_json()` omitted the field, and `from_json()` refused the result. The type could
        build a document its own reader rejects — an asymmetric contract every producer would have to
        rediscover.

        Frozen dataclasses need `object.__setattr__` for defaulting; the alternative was a factory
        nobody is obliged to use.
        """
        if self.slot_references is None:
            message = "a package needs one slot reference per batting row; schema 1 is gone"
            raise PackageError(message)
        # The guard refuses anything but a tuple, so there is nothing left to canonicalise here. The
        # version that accepted a list and converted it made the annotation and the constructor
        # disagree; refusing is the shorter way to have one contract, and it keeps a mutable container
        # out of a frozen object whose point is that a signed package cannot change afterwards.
        # ⚠️ `is not True and is not False`, never truthiness. `offense_is_home=0` is a caller saying
        # *the visitors are batting* in a language the field does not speak, and truthiness would read
        # it as the absence this branch exists to catch.
        if self.offense_is_home is not True and self.offense_is_home is not False:
            message = f"offense_is_home is {self.offense_is_home!r}; a package must say which side batted last"
            raise PackageError(message)
        _check_slot_references(self.slot_references, len(self.puzzle.batting))
        # ⚠️ **The labels were defaulted and never counted.** A package could be built, signed and
        # certified on the forge with no labels at all, and the browser then refused it for exactly that
        # — two readers of one schema disagreeing about what the schema requires, which is the failure
        # shape this project is named for. The document says one label per row; so does this now.
        # ⚠️ **The same rule the parser applies, and for the reason `check_profile` records.** A policy
        # living only at the parse boundary let this type emit a document its own reader refused.
        check_profile(self.puzzle, "puzzle", complete=False)
        check_profile(self.solution, "solution", complete=True)
        _check_labels(self.labels, len(self.puzzle.batting), "labels")
        _check_labels(self.pitcher_labels, len(self.puzzle.pitching), "pitcher_labels")
        if self.schema is not None:
            _check_schema(self.schema, "a package cannot be schema")
        # ⚠️ Here rather than in `from_json`, because `from_json` calls this constructor and a check
        # placed only on the parse path would let the forge build and sign a package its own reader
        # refuses. That asymmetry is what schema 4's own docstring records going wrong once already.
        if self.reveal is not None:
            check_reveal_agrees(self.reveal, self.solution, self.labels, self.pitcher_labels)

    @property
    def written_as(self) -> int:
        """⚠️ **One version, so nothing derives it any more.**

        This returned 1 for a package without slot references, which was right while both versions
        existed: a version is a statement about the payload. Version 1 is gone — its signatures are
        HMAC and this parser only accepts Ed25519, so the compatibility promise was false and no
        consumer needed it — and with one version left, deriving would only manufacture a document
        this code cannot read back.
        """
        # `is not None`, never truthiness: an empty tuple is a real value and used to read as absent.
        return self.schema if self.schema is not None else SCHEMA_VERSION

    signature: str | None = None

    def published(self) -> Self:
        """The shape that travels.

        ⚠️ **It no longer removes the solution**, and that reversal is worth stating. The earlier
        version stripped it as an answer key, which contradicts §23: with the backend down the client
        cannot fetch a name when a row is completed, so the reveal and the solution have to be in the
        file. What travels instead loses the metadata keys that would give the game away, because a
        deliberately opaque id beside a `game_id` in the metadata protects nothing.
        """
        # ⚠️ **`replace`, for the reason the signer now uses it too.** A hand-written field list is a
        # copy of the dataclass that nobody updates: `offense_is_home` was added and both rebuilders
        # dropped it without a word. Naming only what changes is the only version of this that cannot
        # go stale.
        return replace(
            self,
            metadata={key: value for key, value in self.metadata.items() if key not in LEAKING_METADATA},
        )

    def as_json(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema": self.written_as,
            "puzzle_id": self.puzzle_id,
            "puzzle": self.puzzle.as_json(),
            "metadata": self.metadata,
        }
        document["labels"] = list(self.labels)
        document["pitcher_labels"] = list(self.pitcher_labels)
        if self.slot_references is not None:
            document["slot_references"] = list(self.slot_references)
        # Unconditional: `__post_init__` refuses a package without it, so a document missing the field
        # is one this code did not write.
        document["offense_is_home"] = self.offense_is_home
        document["solution"] = self.solution.as_json()
        if self.reveal is not None:
            document["reveal"] = self.reveal.as_json()
        if self.signature is not None:
            document["signature"] = self.signature
        return document

    @classmethod
    def from_json(cls, raw: object) -> Self:
        """The envelope, checked here rather than by whoever happens to call this.

        ⚠️ **`read()` guarded the root object and this did not**, so a list or a string reaching this
        method raised `AttributeError` from `raw.get` instead of `PackageError`. A public boundary that
        is only safe when entered through one particular door is not a boundary.

        And `schema` was compared with `!=`, which accepts `true`: Python makes `True == 1`. A JSON
        document declaring `"schema": true` was read as a version 1 package.
        """
        if not isinstance(raw, dict):
            message = f"puzzle package is {type(raw).__name__}, expected an object"
            raise PackageError(message)
        _check_schema(raw.get("schema"), "puzzle package schema")
        try:
            # Hoisted so the slot references can be checked against the board they belong to: one per
            # batting row is the property, and it cannot be stated without the rows.
            puzzle = Board.from_json(raw["puzzle"])
            return cls(
                puzzle_id=_matching(raw.get("puzzle_id"), PUZZLE_ID, "puzzle_id"),
                puzzle=puzzle,
                # ⚠️ `complete=True`: an answer board with a hole is worse than a missing one, because
                # both readers accepted it and the cell then read blank *and* counted as correct.
                solution=Board.from_json(_required(raw, "solution"), complete=True),
                # Required, not defaulted: a document without them is not a v3 document.
                labels=tuple(_strings(raw.get("labels"), "labels")),
                pitcher_labels=tuple(_strings(raw.get("pitcher_labels"), "pitcher_labels")),
                reveal=Reveal.from_json(raw["reveal"]) if raw.get("reveal") is not None else None,
                slot_references=_slot_references(raw.get("slot_references"), len(puzzle.batting)),
                offense_is_home=_side(raw.get("offense_is_home")),
                # ⚠️ Required, not defaulted to `{}`. The document says the key is present; defaulting
                # meant a package with no metadata parsed here and was refused by the client, which is
                # the divergence the shared vectors exist to catch — and did, on their first run.
                metadata=_metadata(raw.get("metadata")),
                # Not stored. `written_as` derives the version from the payload, and a document
                # whose declared version disagreed with its content was rejected above — so keeping
                # the parsed number would only let a round trip differ from its original.
                schema=None,
                signature=_matching(raw.get("signature"), SIGNATURE, "signature", optional=True),
            )
        except (KeyError, TypeError) as error:
            message = f"puzzle package is missing or malformed: {error}"
            raise PackageError(message) from error


def _check_labels(values: object, rows: int, where: str) -> None:
    """One label per row, and a tuple of strings — the same rule the client applies."""
    if isinstance(values, str) or not isinstance(values, (tuple, list)):
        message = f"{where} is {type(values).__name__}, expected a tuple of strings"
        raise PackageError(message)
    if len(values) != rows:
        message = f"{len(values)} {where} for {rows} rows"
        raise PackageError(message)
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value:
            message = f"{where}[{index}] is {value!r}, expected a non-empty string"
            raise PackageError(message)


def _check_schema(value: object, where: str) -> None:
    """The version rule, in one place, used by construction **and** by parsing.

    ⚠️ **They applied different subsets, and the constructor's was the weaker one.** `__post_init__`
    asked only `not in READABLE`, and Python makes `2.0 == 2`, so `schema=2.0` passed, `written_as`
    returned the float, and `as_json()` emitted `"schema": 2.0` — a document `from_json` correctly
    refuses. **The type could once again build output outside the language its own parser accepts**,
    which is the sentence already written above this class about slot references, arriving one field
    over because the rule had two copies instead of one home.

    `bool` is excluded explicitly: `True == 1`, and a JSON document declaring `"schema": true` was once
    read as a version 1 package.
    """
    if not isinstance(value, int) or isinstance(value, bool) or value not in READABLE:
        message = f"{where} {value!r}; this code reads {list(READABLE)}"
        raise PackageError(message)


def _check_slot_references(values: object, rows: int) -> None:
    """The complete rule, in one place, used by construction **and** by parsing.

    ⚠️ **These applied different subsets.** `__post_init__` checked the count and `from_json` checked
    the count, the syntax and the duplicates — so a producer could build a package with a malformed or
    repeated reference, serialise it happily, and hand `serve` a document the shared reader refuses.
    The reference writer's read-back caught that for one caller; the shared type has to be unable to
    produce output outside the language its own parser accepts, or every producer rediscovers the
    guard independently.
    """
    # ⚠️ **The container is checked before its contents.** Widening this to `Sequence[object]` kept
    # the element guard reachable and left the outer shape unchecked — and a `str` **is** a Sequence,
    # so a nine-row package given `"123456789"` passed the length, the per-character grammar and the
    # uniqueness test.
    #
    # ⚠️ **A tuple, and only a tuple.** The first repair accepted a list and canonicalised it, which
    # left the field's annotation saying `tuple[str, ...]` while the constructor took something else:
    # a typed producer could not use the supported path without an error, and a mutable container was
    # admitted into a frozen object whose whole purpose is that a signed package cannot change
    # afterwards. Two contracts for one field is this project's named failure shape, and the cheap way
    # to have one is to refuse — no caller passes a list, and `from_json` converts at the parse
    # boundary, which is where a conversion belongs.
    if not isinstance(values, tuple):
        message = f"slot_references is {type(values).__name__}, expected a tuple of strings"
        raise PackageError(message)
    if len(values) != rows:
        message = f"{len(values)} slot references for {rows} batting rows"
        raise PackageError(message)
    for index, value in enumerate(values):
        # ⚠️ **The parameter is `Sequence[object]` on purpose.** Typing it `tuple[str, ...]` made
        # mypy call this branch unreachable — correct about the annotation and wrong about the world,
        # because `__post_init__` receives whatever a caller passed. An annotation that promises more
        # than the boundary can check turns a real guard into dead code.
        #
        # The type check lived in the parser only, so a direct `Package(...)` carrying `1` or
        # `None` reached the regex and raised a bare `TypeError`: the same malformed field with a
        # different error contract depending on which supported path built it, and neither path is
        # the exception.
        if not isinstance(value, str):
            message = f"slot reference {index} is {value!r}, expected a string"
            raise PackageError(message)
        if not SLOT_REFERENCE.fullmatch(value):
            message = f"slot reference {value!r} is not a slot with an optional letter"
            raise PackageError(message)
    if len(set(values)) != len(values):
        # A duplicate makes a footnote unresolvable, which is the one thing the field exists to do.
        message = f"slot_references repeats a value: {list(values)}"
        raise PackageError(message)


def _side(raw: object) -> bool:
    """Which half batted last, as a boolean and nothing else.

    ⚠️ **`isinstance(raw, bool)`, not truthiness.** JSON's `0` and `1` are the shape a producer in
    another language reaches for, and accepting them would let a document say *the visitors batted*
    while meaning nothing of the kind. The constructor applies the same rule; this is the parse side of
    one predicate, not a second one.
    """
    if not isinstance(raw, bool):
        message = f"offense_is_home is {raw!r}, expected true or false"
        raise PackageError(message)
    return raw


def _slot_references(raw: object, rows: int) -> tuple[str, ...]:
    """One reference per batting row. Required: schema 1 is gone and there is no version without it."""
    if not isinstance(raw, list):
        message = f"slot_references is {raw!r}, expected {rows} strings, one per batting row"
        raise PackageError(message)
    _check_slot_references(tuple(raw), rows)
    return tuple(raw)


def _matching(raw: object, pattern: re.Pattern[str], where: str, *, optional: bool = False) -> Any:  # noqa: ANN401
    """A string of the shape the contract states, or a refusal naming the field.

    `optional` allows absence, never a wrong shape: a package may be unsigned, and a package whose
    signature is a number or an empty string is malformed rather than unsigned.
    """
    if raw is None and optional:
        return None
    if not isinstance(raw, str) or not pattern.fullmatch(raw):
        message = f"{where} is {raw!r}, expected {pattern.pattern}"
        raise PackageError(message)
    return raw


def _metadata(raw: object) -> dict[str, Any]:
    """Loose by design (seam C3), but it has to be an object — a list here breaks every reader."""
    if not isinstance(raw, dict):
        message = f"metadata is {type(raw).__name__}, expected an object"
        raise PackageError(message)
    return raw


def read(path: Path) -> Package:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        message = f"{path} is not valid JSON: {error}"
        raise PackageError(message) from error
    # The root check lives in `from_json` now, where every caller gets it. Kept here only to name
    # the file in the message, which a caller reading a path wants and the method cannot know.
    if not isinstance(raw, dict):
        message = f"{path} does not hold a puzzle package"
        raise PackageError(message)
    return Package.from_json(raw)


def write(path: Path, package: Package) -> None:
    path.write_text(json.dumps(package.as_json(), indent=1, sort_keys=True), encoding="utf-8")
