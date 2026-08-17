"""The accounting identities a boxscore must satisfy.

Two jobs, and they are the same equations in both:

1. Layer 1 of the correctness guarantee — a boxscore that violates any identity never enters the
   pool. A failing boxscore is discarded, never repaired, so validation reports every violation it
   finds rather than stopping at the first.
2. The constraint system the T1-T5 solver reasons over.

Only identities the board can express are here. The design lists others — hits at least doubles
plus triples plus home runs, runs batted in at least home runs per player — that reference columns
the width budget excluded. An identity over a quantity the player cannot see is not a deduction
they can make.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from boxscore_forge.boxscore import BattingLine, Direction, PitchingLine

BATTING_COLUMNS: Final[tuple[str, ...]] = ("at_bats", "runs", "hits", "runs_batted_in", "walks", "strikeouts")
PITCHING_COLUMNS: Final[tuple[str, ...]] = ("outs", "hits", "runs", "earned_runs", "walks", "strikeouts")

# The offense's hits, runs, walks and strikeouts are the same events the opposing pitchers are
# charged with. At-bats and runs batted in have no pitching counterpart on the board.
CROSS_TEAM_COLUMNS: Final[tuple[str, ...]] = ("hits", "runs", "walks", "strikeouts")

FOOTNOTE_FIELDS: Final[tuple[str, ...]] = ("left_on_base", "hit_by_pitch", "sacrifice_flies", "sacrifice_hits")
LINE_SCORE_FIELDS: Final[tuple[str, ...]] = (
    "offense_runs",
    "offense_hits",
    "offense_errors",
    "defense_runs",
    "defense_hits",
    "defense_errors",
)


class Identity(StrEnum):
    """Every identity that can reject a boxscore, named so a rejection says which one broke."""

    BATTING_COLUMN_SUM = "batting_column_sum"
    PITCHING_COLUMN_SUM = "pitching_column_sum"
    CROSS_TEAM_TOTAL = "cross_team_total"
    PLATE_APPEARANCES = "plate_appearances"
    LINE_SCORE_RUNS = "line_score_runs"
    LINE_SCORE_HITS = "line_score_hits"
    HITS_WITHIN_AT_BATS = "hits_within_at_bats"
    EARNED_RUNS_WITHIN_RUNS = "earned_runs_within_runs"
    RUNS_BATTED_IN_WITHIN_RUNS = "runs_batted_in_within_runs"
    NON_NEGATIVE = "non_negative"


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
        *_check_plate_appearances(direction),
        *_check_line_score(direction),
        *_check_bounds(direction),
        *_check_non_negative(direction),
    )


def _value(container: object, field: str) -> int:
    value: int = getattr(container, field)
    return value


def _check_column_sums(direction: Direction) -> Iterator[Violation]:
    """Every column of individual rows must add up to the totals row the board pins on screen."""
    for column in BATTING_COLUMNS:
        rows = sum(_value(line, column) for line in direction.batting)
        total = _value(direction.batting_totals, column)
        if rows != total:
            yield Violation(Identity.BATTING_COLUMN_SUM, f"{column}: rows sum to {rows}, total says {total}")

    for column in PITCHING_COLUMNS:
        rows = sum(_value(line, column) for line in direction.pitching)
        total = _value(direction.pitching_totals, column)
        if rows != total:
            yield Violation(Identity.PITCHING_COLUMN_SUM, f"{column}: rows sum to {rows}, total says {total}")


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


def _check_plate_appearances(direction: Direction) -> Iterator[Violation]:
    """Every batter who came to the plate made an out, scored, or was left on base.

    On this board the batter line and the global team identity close as one equation, because plate
    appearances are not a column: counting them forward from at-bats has to agree with counting them
    backward from outs, runs and runners left on.

    The backward count assumes every runner arrived by way of a plate appearance. That has been true
    of every team-game before 2020 bar eleven, which are source errors. It is not true since: extra
    innings begin with a runner already on second who never batted, so those games break this
    identity on the board as surely as they break it here, and rejecting them is correct rather than
    a false negative.
    """
    footnotes = direction.footnotes
    from_batting = (
        direction.batting_totals.at_bats
        + direction.batting_totals.walks
        + footnotes.hit_by_pitch
        + footnotes.sacrifice_flies
        + footnotes.sacrifice_hits
        + footnotes.reached_on_interference
    )
    from_outs = direction.pitching_totals.outs + direction.batting_totals.runs + footnotes.left_on_base
    if from_batting != from_outs:
        yield Violation(
            Identity.PLATE_APPEARANCES,
            f"at-bats plus walks and sacrifices give {from_batting}, outs plus runs plus left on base give {from_outs}",
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

    for label, pitching_line in _labelled_pitching(direction):
        if pitching_line.earned_runs > pitching_line.runs:
            yield Violation(
                Identity.EARNED_RUNS_WITHIN_RUNS,
                f"{label}: {pitching_line.earned_runs} earned of {pitching_line.runs} runs",
            )

    totals = direction.batting_totals
    if totals.runs_batted_in > totals.runs:
        yield Violation(
            Identity.RUNS_BATTED_IN_WITHIN_RUNS,
            f"team: {totals.runs_batted_in} runs batted in against {totals.runs} runs",
        )


def _check_non_negative(direction: Direction) -> Iterator[Violation]:
    for label, value in _every_value(direction):
        if value < 0:
            yield Violation(Identity.NON_NEGATIVE, f"{label} is {value}")


def _labelled_batting(direction: Direction) -> Iterator[tuple[str, BattingLine]]:
    for index, line in enumerate(direction.batting):
        yield f"batting[{index}]", line
    yield "batting_totals", direction.batting_totals


def _labelled_pitching(direction: Direction) -> Iterator[tuple[str, PitchingLine]]:
    for index, line in enumerate(direction.pitching):
        yield f"pitching[{index}]", line
    yield "pitching_totals", direction.pitching_totals


def _every_value(direction: Direction) -> Iterator[tuple[str, int]]:
    for label, batting_line in _labelled_batting(direction):
        for column in BATTING_COLUMNS:
            yield f"{label}.{column}", _value(batting_line, column)
    for label, pitching_line in _labelled_pitching(direction):
        for column in PITCHING_COLUMNS:
            yield f"{label}.{column}", _value(pitching_line, column)
    for field in FOOTNOTE_FIELDS:
        yield f"footnotes.{field}", _value(direction.footnotes, field)
    for field in LINE_SCORE_FIELDS:
        yield f"line_score.{field}", _value(direction.line_score, field)
    for label, innings in (
        ("offense", direction.line_score.offense_by_inning),
        ("defense", direction.line_score.defense_by_inning),
    ):
        for inning, runs in enumerate(innings, start=1):
            yield f"line_score.{label}_by_inning[{inning}]", runs
