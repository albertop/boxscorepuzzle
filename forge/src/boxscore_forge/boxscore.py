"""The board's data model: one direction of a real boxscore.

A direction is one team's offense against the opposing team's pitching. A game yields up to two,
and may qualify as a puzzle in one direction and not the other.

Every quantity is an integer. Innings pitched are stored as outs rather than the printed `x.y`
form: thirds of an inning are not decimals, and floating point in an arithmetic identity produces
puzzles that fail validation for no visible reason.

Containers are frozen because they travel through a validation pipeline, where a mutable value is
action at a distance waiting to happen.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BattingLine:
    """One batter's row, or the batting totals row. Six columns, which is the board's width limit."""

    at_bats: int
    runs: int
    hits: int
    runs_batted_in: int
    walks: int
    strikeouts: int


@dataclass(frozen=True, slots=True)
class PitchingLine:
    """One pitcher's row, or the pitching totals row.

    `outs` is what the board prints as IP. Three outs to an inning; the conversion belongs at the
    presentation edge, not here.
    """

    outs: int
    hits: int
    runs: int
    earned_runs: int
    walks: int
    strikeouts: int


@dataclass(frozen=True, slots=True)
class Footnotes:
    """Given values the board prints below the grid rather than as columns, for the offensive team.

    The width budget allows six data columns and no seventh, but a printed boxscore publishes these
    same quantities as footnotes, which cost no column width and need no touch target because they
    are never erased.

    Without `left_on_base` the plate appearance identity cannot be expressed at all, and without the
    remaining counts it does not close.

    `reached_on_interference` is the category that is easy to forget, because it almost never
    happens and a boxscore missing it still looks right. Checked against every team-game Retrosheet
    has: counting it, the plate appearance total balances in all 407,816; leaving it out, 1,933 of
    them silently fail to.
    """

    left_on_base: int
    hit_by_pitch: int
    sacrifice_flies: int
    sacrifice_hits: int
    reached_on_interference: int


@dataclass(frozen=True, slots=True)
class LineScore:
    """Runs per inning for both teams plus the R/H/E summary. Given complete and never erased.

    The per-inning tuples can differ in length: a home team leading after the top of the ninth does
    not bat, and extra innings lengthen both. Nothing here assumes nine.

    Errors are carried because a line score has an E column, but no identity uses them — Retrosheet
    proofs defensive statistics far less closely, and the board deduces nothing from them.
    """

    offense_by_inning: tuple[int, ...]
    defense_by_inning: tuple[int, ...]
    offense_runs: int
    offense_hits: int
    offense_errors: int
    defense_runs: int
    defense_hits: int
    defense_errors: int


@dataclass(frozen=True, slots=True)
class Direction:
    """One team's offense against the opposing team's pitching: everything the board shows."""

    batting: tuple[BattingLine, ...]
    batting_totals: BattingLine
    pitching: tuple[PitchingLine, ...]
    pitching_totals: PitchingLine
    footnotes: Footnotes
    line_score: LineScore
