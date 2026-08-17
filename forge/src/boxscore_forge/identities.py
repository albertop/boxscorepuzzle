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
    """The four kinds of reasoning the board offers, which is the second axis of difficulty."""

    COLUMN_SUM = "column_sum"
    ROW_IDENTITY = "row_identity"
    CROSS_TEAM = "cross_team"
    GLOBAL_IDENTITY = "global_identity"


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
}


@dataclass(frozen=True, slots=True)
class Violation:
    """One broken identity. `detail` is for the operator's logs, never for a player."""

    identity: Identity
    detail: str


def find_violations(direction: Direction) -> tuple[Violation, ...]:
    """Return every identity the direction breaks. An empty result means the boxscore balances."""
    return (
        *_check_column_sums(direction),
        *_check_cross_team_totals(direction),
        *_check_row_identities(direction),
        *_check_global_identity(direction),
        *_check_line_score(direction),
        *_check_bounds(direction),
        *_check_non_negative(direction),
    )


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
            + footnotes.reached_on_interference
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
