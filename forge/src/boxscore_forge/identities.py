"""The accounting identities a boxscore must satisfy.

Two jobs, and they are the same equations in both:

1. Layer 1 of the correctness guarantee — a boxscore that violates any identity never enters the
   pool. A failing boxscore is discarded, never repaired, so validation reports every violation it
   finds rather than stopping at the first.
2. The constraint system the solver reasons over.

Only identities the board can express are here. The design lists others — hits at least doubles
plus triples plus home runs — that reference columns the width budget excluded. An identity over a
quantity the player cannot see is not a deduction they can make.

Identities group into four families, and which families a solution path had to use is one of the
two axes that describe a puzzle's difficulty. The families, not the individual identities, are what
make one Saturday feel different from the next.
"""

import dataclasses
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from boxscore_forge.boxscore import (
    BatterFootnotes,
    BattingLine,
    Direction,
    LineScore,
    PitchingLine,
    TeamFootnotes,
)


def _integer_fields(model: type) -> tuple[str, ...]:
    """Read the columns off the model rather than restating them.

    A hand-written list is a second source of truth that drifts the first time a column is added,
    and it drifts silently: the new column simply goes unchecked.
    """
    return tuple(field.name for field in dataclasses.fields(model) if field.type in (int, "int"))


BATTING_COLUMNS: Final[tuple[str, ...]] = _integer_fields(BattingLine)
PITCHING_COLUMNS: Final[tuple[str, ...]] = _integer_fields(PitchingLine)
FOOTNOTE_COLUMNS: Final[tuple[str, ...]] = _integer_fields(BatterFootnotes)
TEAM_FOOTNOTE_FIELDS: Final[tuple[str, ...]] = _integer_fields(TeamFootnotes)
LINE_SCORE_FIELDS: Final[tuple[str, ...]] = _integer_fields(LineScore)

# The one list that stays written out, because it is a choice rather than a reflection of the model:
# the offense's hits, runs, walks and strikeouts are the same events the opposing pitchers are
# charged with, while at-bats and plate appearances have no pitching counterpart on the board.
CROSS_TEAM_COLUMNS: Final[tuple[str, ...]] = ("hits", "runs", "walks", "strikeouts")


class Family(StrEnum):
    """The five kinds of reasoning the board offers, which is the second axis of difficulty.

    ⚠️⚠️ **This was four, and the player was already being taught five.** The reference sheet and the
    tutorial both present the batting order as a relation family — it is the one family that cannot be
    read off a boxscore, which is exactly why §8 has to teach it — while `FAMILY_OF` mapped no identity
    to it, so `families_used` silently excluded every lineup step and package metadata could not say a
    board needed one.

    **Not adding it did not avoid the mismatch; it hid it.** And it had a practical cost: with no
    family for it there was no way to ask how many published boards depend on the batting order, or to
    exclude them if that ever became necessary.

    ⚠️ **Every figure taken before 2026-08-21 was measured against four families.** They are not wrong
    — they were counting a smaller set — and they are marked rather than re-run, the same treatment the
    zero-fill correction received. A figure that names the four-family axis stays comparable with
    itself; one that mixes the two axes is not comparable with anything.
    """

    COLUMN_SUM = "column_sum"
    ROW_IDENTITY = "row_identity"
    CROSS_TEAM = "cross_team"
    GLOBAL_IDENTITY = "global_identity"
    BATTING_ORDER = "batting_order"


class Identity(StrEnum):
    """Every identity that can reject a boxscore, named so a rejection says which one broke."""

    BATTING_COLUMN_SUM = "batting_column_sum"
    FOOTNOTE_COLUMN_SUM = "footnote_column_sum"
    PITCHING_COLUMN_SUM = "pitching_column_sum"
    CROSS_TEAM_TOTAL = "cross_team_total"
    ROW_PLATE_APPEARANCES = "row_plate_appearances"
    GLOBAL_PLATE_APPEARANCES = "global_plate_appearances"
    LINE_SCORE_RUNS = "line_score_runs"
    LINE_SCORE_HITS = "line_score_hits"
    HITS_WITHIN_AT_BATS = "hits_within_at_bats"
    PLATE_APPEARANCES_COVER_AT_BATS_AND_WALKS = "plate_appearances_cover_at_bats_and_walks"
    EARNED_RUNS_WITHIN_RUNS = "earned_runs_within_runs"
    BATTING_ORDER = "batting_order"
    """The lineup is cyclic and cannot be skipped, so a slot never bats fewer times than the one after it.

    ⚠️ **Per SLOT, never per player.** A slot is every man who occupied it; measured per row the claim is
    false at once, since a substitute bats fewer times than the man he replaced.

    ⚠️ **True of 99.9950% of the production pool** — 5 directions in 100,226 break it, which is why it
    arrives with a pool rule rather than as a weaker relation. A constraint true almost always is a trap:
    the solver deduces a value that is wrong on the exceptional board and every total still balances.
    """

    NON_NEGATIVE = "non_negative"


FAMILY_OF: Final[dict[Identity, Family]] = {
    Identity.BATTING_COLUMN_SUM: Family.COLUMN_SUM,
    Identity.FOOTNOTE_COLUMN_SUM: Family.COLUMN_SUM,
    Identity.PITCHING_COLUMN_SUM: Family.COLUMN_SUM,
    # The line score is an anchor rather than a family of its own: what it states about runs and
    # hits is the same kind of reasoning as reading a column total off the bottom of the grid.
    Identity.LINE_SCORE_RUNS: Family.COLUMN_SUM,
    Identity.LINE_SCORE_HITS: Family.COLUMN_SUM,
    Identity.ROW_PLATE_APPEARANCES: Family.ROW_IDENTITY,
    Identity.CROSS_TEAM_TOTAL: Family.CROSS_TEAM,
    Identity.GLOBAL_PLATE_APPEARANCES: Family.GLOBAL_IDENTITY,
    # ⚠️ Added 2026-08-21. Its absence is why `families_used` could not report a board that leaned on
    # the lineup, and why the package recorded `"lineup": "plain" | "fallback"` as a workaround.
    Identity.BATTING_ORDER: Family.BATTING_ORDER,
}


UNMAPPED: Final[frozenset[Identity]] = frozenset(
    {
        Identity.HITS_WITHIN_AT_BATS,
        Identity.PLATE_APPEARANCES_COVER_AT_BATS_AND_WALKS,
        Identity.EARNED_RUNS_WITHIN_RUNS,
        Identity.NON_NEGATIVE,
    }
)
"""Identities deliberately outside the family axis, and the reason they are outside it.

**Every member here is an inequality, not an equality.** `AB >= H`, `PA >= AB + BB`, `ER <= R` and
`nothing below zero` bound a cell; they do not *close* a relation the way a column total or a row
identity does. The family axis describes **which kind of reasoning produced a deduction**, and a bound
narrowing a range is the bounding technique rather than one of the equation families — §4's two axes
are technique and family, and these belong to the first.

⚠️⚠️ **This set exists so that "deliberately unmapped" and "forgotten" stop looking the same.**
(v36-P3-38) The membership rule was three hand-written lists — one here, one in `test_identities.py`,
one in `test_constraints.py` — tied together only by `<= FAMILY_OF.keys()` subset assertions. A subset
assertion fires when an identity is *removed* from `FAMILY_OF` while still on a hand list; **the
realistic drift is the opposite**, a new equality identity added to `find_violations` and forgotten in
`FAMILY_OF`, and the hand lists would not contain the newcomer either, so nothing would notice.

`Identity.BATTING_ORDER` was the live demonstration: absent from all three, and no way to tell whether
that was a decision or an oversight. It was an oversight, and it took a review to find out.

With this, `set(Identity) - UNMAPPED == FAMILY_OF.keys()` is assertable, so **a newcomer must be
classified somewhere or the suite goes red**.
"""


@dataclass(frozen=True, slots=True)
class Violation:
    """One broken identity. `detail` is for the operator's logs, never for a player."""

    identity: Identity
    detail: str


def find_violations(direction: Direction, slots: tuple[int, ...] = ()) -> tuple[Violation, ...]:
    """Return every identity the direction breaks. An empty result means the boxscore balances.

    `slots` is the batting order. **Empty means the order is not checked**, never checked against a
    guess: one row per slot is wrong on every board carrying a substitution, and wrong silently,
    because the board balances either way.
    """
    return (
        *_check_column_sums(direction),
        *_check_cross_team_totals(direction),
        *_check_row_identities(direction),
        *_check_global_identity(direction),
        *_check_line_score(direction),
        *_check_bounds(direction),
        *_check_non_negative(direction),
        *_check_batting_order(direction, slots),
    )


LINEUP_SLOTS: Final = 9
"""A batting order is nine places. The shape of the game, not a parameter."""


def _check_batting_order(direction: Direction, slots: tuple[int, ...]) -> tuple[Violation, ...]:
    """The per-slot appearances must be what the team total predicts, or the direction is out of the pool.

    ⚠⚠ **The pool rule, and it is a rule about the data rather than about the game.** The order is a
    cycle and never skips, so `T` plate appearances are dealt round the nine places: `T // 9` each,
    plus one more for the first `T % 9`. **35 directions in 371,802 do not match that.**

    ⚠️ **They read as transcription noise, not as baseball, and here is why.** The exceptions are flat
    across every decade from the 1910s to the 2010s; they appear under both source types; they are not
    concentrated in extra-inning games, nor in games where one side batted last. **A real rule of the
    game would cluster somewhere** — a scoring convention has an era, a source, or a situation. Noise
    spread evenly across all four dimensions is the signature of a transcription error.

    ⚠️ **And the caveat stays, because it is not resolved.** 35 is few enough for a person to read, and
    nobody has. A genuine batting-out-of-order call cannot be told from a scoring error *by a
    distribution* — both produce exactly this shape. The rule is applied because a constraint true
    99.99% of the time is a trap rather than a weaker rule: the generator would erase cells the player
    cannot deduce on the one board in ten thousand that breaks it.

    Excluding them is cheap and reversible; shipping an underivable board is neither.
    """
    if not slots:
        return ()
    if len(slots) != len(direction.batting):
        return (
            Violation(
                Identity.BATTING_ORDER,
                f"{len(slots)} slots against {len(direction.batting)} batting rows",
            ),
        )
    if sorted(set(slots)) != list(range(1, LINEUP_SLOTS + 1)):
        return (Violation(Identity.BATTING_ORDER, f"slots {sorted(set(slots))} are not the nine places"),)

    per_slot: dict[int, int] = {}
    for row, slot in zip(direction.batting, slots, strict=True):
        per_slot[slot] = per_slot.get(slot, 0) + row.plate_appearances
    total = sum(per_slot.values())
    complete, over = divmod(total, LINEUP_SLOTS)

    broken = [
        f"slot {slot} has {per_slot[slot]}, the cycle gives {complete + (1 if slot <= over else 0)}"
        for slot in sorted(per_slot)
        if per_slot[slot] != complete + (1 if slot <= over else 0)
    ]
    if broken:
        return (Violation(Identity.BATTING_ORDER, f"{total} plate appearances: " + "; ".join(broken)),)
    return ()


def _value(container: object, field: str) -> int:
    value: int = getattr(container, field)
    return value


def _check_column_sums(direction: Direction) -> Iterator[Violation]:
    """Every column of individual rows must add up to the totals row the board pins on screen."""
    for columns, rows, totals, identity in (
        (BATTING_COLUMNS, direction.batting, direction.batting_totals, Identity.BATTING_COLUMN_SUM),
        (FOOTNOTE_COLUMNS, direction.batter_footnotes, direction.footnote_totals, Identity.FOOTNOTE_COLUMN_SUM),
        (PITCHING_COLUMNS, direction.pitching, direction.pitching_totals, Identity.PITCHING_COLUMN_SUM),
    ):
        for column in columns:
            summed = sum(_value(row, column) for row in rows)
            stated = _value(totals, column)
            if summed != stated:
                yield Violation(identity, f"{column}: rows sum to {summed}, total says {stated}")


def _check_cross_team_totals(direction: Direction) -> Iterator[Violation]:
    """The link between the two halves of the board, and what makes this a puzzle rather than
    unrelated rows of arithmetic."""
    for column in CROSS_TEAM_COLUMNS:
        offense = _value(direction.batting_totals, column)
        charged_to_pitchers = _value(direction.pitching_totals, column)
        if offense != charged_to_pitchers:
            yield Violation(
                Identity.CROSS_TEAM_TOTAL,
                f"{column}: offense has {offense}, opposing pitchers are charged with {charged_to_pitchers}",
            )


def _check_row_identities(direction: Direction) -> Iterator[Violation]:
    """Every plate appearance is an at-bat, a walk, or one of the footnoted ways of reaching.

    Applied to the totals row as well, which is where it doubles as the team-level batter line.
    """
    rows = [*zip(direction.batting, direction.batter_footnotes, strict=True)]
    rows.append((direction.batting_totals, direction.footnote_totals))
    for index, (line, footnotes) in enumerate(rows):
        label = "totals" if index == len(rows) - 1 else f"batting[{index}]"
        accounted = (
            line.at_bats
            + line.walks
            + footnotes.hit_by_pitch
            + footnotes.sacrifice_flies
            + footnotes.sacrifice_hits
            + footnotes.catcher_interference
        )
        if accounted != line.plate_appearances:
            yield Violation(
                Identity.ROW_PLATE_APPEARANCES,
                f"{label}: {line.plate_appearances} plate appearances against {accounted} accounted for",
            )


def _check_global_identity(direction: Direction) -> Iterator[Violation]:
    """Every batter who came to the plate made an out, scored, or was left on base.

    The count assumes every runner arrived by way of a plate appearance. That was true of every
    team-game before 2020 bar eleven, which are source errors. Extra innings now begin with a runner
    already on second who never batted, so those games break this identity on the board as surely as
    they break it here, and rejecting them is correct rather than a false negative.
    """
    reached_the_plate = direction.batting_totals.plate_appearances
    accounted = direction.pitching_totals.outs + direction.batting_totals.runs + direction.team_footnotes.left_on_base
    if reached_the_plate != accounted:
        yield Violation(
            Identity.GLOBAL_PLATE_APPEARANCES,
            f"{reached_the_plate} plate appearances against {accounted} outs, runs and runners left on",
        )


def _check_line_score(direction: Direction) -> Iterator[Violation]:
    """The line score is the anchor: it is never erased, so everything it states must hold."""
    line_score = direction.line_score
    for label, innings, total in (
        ("offense", line_score.offense_by_inning, line_score.offense_runs),
        ("defense", line_score.defense_by_inning, line_score.defense_runs),
    ):
        by_inning = sum(innings)
        if by_inning != total:
            yield Violation(Identity.LINE_SCORE_RUNS, f"{label}: innings sum to {by_inning}, run total says {total}")

    if line_score.offense_runs != direction.batting_totals.runs:
        yield Violation(
            Identity.LINE_SCORE_RUNS,
            f"line score gives the offense {line_score.offense_runs} runs, batting total says "
            f"{direction.batting_totals.runs}",
        )
    if line_score.offense_hits != direction.batting_totals.hits:
        yield Violation(
            Identity.LINE_SCORE_HITS,
            f"line score gives the offense {line_score.offense_hits} hits, batting total says "
            f"{direction.batting_totals.hits}",
        )


def _check_bounds(direction: Direction) -> Iterator[Violation]:
    """Inequalities. They rarely reject a real boxscore, but they are what lets the solver eliminate
    candidates rather than only compute them."""
    for label, line in _labelled_batting(direction):
        if line.hits > line.at_bats:
            yield Violation(Identity.HITS_WITHIN_AT_BATS, f"{label}: {line.hits} hits in {line.at_bats} at-bats")
        if line.at_bats + line.walks > line.plate_appearances:
            yield Violation(
                Identity.PLATE_APPEARANCES_COVER_AT_BATS_AND_WALKS,
                f"{label}: {line.at_bats} at-bats and {line.walks} walks in {line.plate_appearances} plate appearances",
            )

    for label, pitching_line in _labelled_pitching(direction):
        if pitching_line.earned_runs > pitching_line.runs:
            yield Violation(
                Identity.EARNED_RUNS_WITHIN_RUNS,
                f"{label}: {pitching_line.earned_runs} earned of {pitching_line.runs} runs",
            )


def _check_non_negative(direction: Direction) -> Iterator[Violation]:
    for label, value in _every_value(direction):
        if value < 0:
            yield Violation(Identity.NON_NEGATIVE, f"{label} is {value}")


def _labelled_batting(direction: Direction) -> Iterator[tuple[str, BattingLine]]:
    for index, line in enumerate(direction.batting):
        yield f"batting[{index}]", line
    yield "batting_totals", direction.batting_totals


def _labelled_footnotes(direction: Direction) -> Iterator[tuple[str, BatterFootnotes]]:
    for index, footnotes in enumerate(direction.batter_footnotes):
        yield f"footnotes[{index}]", footnotes
    yield "footnote_totals", direction.footnote_totals


def _labelled_pitching(direction: Direction) -> Iterator[tuple[str, PitchingLine]]:
    for index, line in enumerate(direction.pitching):
        yield f"pitching[{index}]", line
    yield "pitching_totals", direction.pitching_totals


def _every_value(direction: Direction) -> Iterator[tuple[str, int]]:
    for label, batting_line in _labelled_batting(direction):
        for column in BATTING_COLUMNS:
            yield f"{label}.{column}", _value(batting_line, column)
    for label, footnotes in _labelled_footnotes(direction):
        for column in FOOTNOTE_COLUMNS:
            yield f"{label}.{column}", _value(footnotes, column)
    for label, pitching_line in _labelled_pitching(direction):
        for column in PITCHING_COLUMNS:
            yield f"{label}.{column}", _value(pitching_line, column)
    for field in TEAM_FOOTNOTE_FIELDS:
        yield f"team_footnotes.{field}", _value(direction.team_footnotes, field)
    for field in LINE_SCORE_FIELDS:
        yield f"line_score.{field}", _value(direction.line_score, field)
    for label, innings in (
        ("offense", direction.line_score.offense_by_inning),
        ("defense", direction.line_score.defense_by_inning),
    ):
        for inning, runs in enumerate(innings, start=1):
            yield f"line_score.{label}_by_inning[{inning}]", runs
